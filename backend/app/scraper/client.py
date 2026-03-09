import asyncio
import random
import re
import json
from datetime import date, timedelta
from typing import Any, Optional
import httpx
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type, before_sleep_log, RetryError,
)
import logging
from loguru import logger
from app.core.config import settings


def get_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


RETRYABLE = (
    httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout,
    httpx.PoolTimeout, httpx.ConnectError, httpx.RemoteProtocolError,
    httpx.ReadError,
)

TIMEOUTS = httpx.Timeout(connect=6.0, read=10.0, write=6.0, pool=6.0)


def _retry_fast():
    return retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        retry=retry_if_exception_type(RETRYABLE),
        before_sleep=before_sleep_log(
            logging.getLogger("tenacity"), logging.DEBUG,
        ),
        reraise=True,
    )


def _retry_html():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=2, max=10, jitter=2),
        retry=retry_if_exception_type(RETRYABLE),
        before_sleep=before_sleep_log(
            logging.getLogger("tenacity"), logging.DEBUG,
        ),
        reraise=True,
    )


class NCFUClient:
    TARGET_GROUP = 2

    BASE_HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": f"{settings.base_url}/schedule",
    }

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._delay = settings.scraper_request_delay

    async def __aenter__(self) -> "NCFUClient":
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            headers=self.BASE_HEADERS,
            timeout=TIMEOUTS,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=30,
            ),
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    @_retry_fast()
    async def _post_json(self, path: str, body: dict) -> Any:
        assert self._client is not None
        await asyncio.sleep(self._delay + random.uniform(0, 0.15))
        r = await self._client.post(path, json=body)
        if r.status_code in (429, 502, 503, 504):
            logger.warning(f"HTTP {r.status_code} on {path}")
            if r.status_code == 429:
                await asyncio.sleep(
                    int(r.headers.get("Retry-After", 10))
                )
            r.raise_for_status()
        r.raise_for_status()
        return r.json()

    @_retry_html()
    async def _get_html(self, path: str) -> str:
        assert self._client is not None
        await asyncio.sleep(self._delay + random.uniform(0, 0.15))
        r = await self._client.get(path)
        r.raise_for_status()
        return r.text

    # ── Institute discovery ────────────────────────────────────────────────
    async def get_institutes(self) -> list[dict]:
        html = await self._get_html("/schedule")
        m = re.search(
            r"var viewModel\s*=\s*(\{.*?\});", html, re.DOTALL,
        )
        if not m:
            raise ValueError("viewModel not found in schedule page")
        return json.loads(m.group(1)).get("Institutes", [])

    async def get_institutes_for_branch(
        self, branch_id: int,
    ) -> list[dict]:
        try:
            html = await self._get_html(
                f"/schedule?branch={branch_id}"
            )
            m = re.search(
                r"var viewModel\s*=\s*(\{.*?\});", html, re.DOTALL,
            )
            if not m:
                return []
            data = json.loads(m.group(1))
            insts = data.get("Institutes", [])
            for inst in insts:
                if not inst.get("BranchId"):
                    inst["BranchId"] = branch_id
            return insts
        except Exception as exc:
            logger.warning(f"branch {branch_id} fetch failed: {exc}")
            return []

    # ── Specialty discovery  (THE MISSING LAYER) ───────────────────────────
    #
    # The eCampus cascade is:  Institute → Specialties → Groups
    #
    # On the website, when you select an institute in the dropdown, the JS
    # fires an XHR to /schedule/GetSpecialities  (yes, their spelling)
    # with {"instituteId": ..., "branchId": ...}.
    # The server returns a flat JSON list of specialty NAME strings:
    #     ["История", "Математика", "Физика", ...]
    #
    # Then when you pick a specialty, GetAcademicGroups is called with
    # that specialty name in the "specialty" field.

    async def get_specialties(
        self, is_synthetic: bool, institute_id: int, branch_id: int,
    ) -> list[str]:
        """
        Fetch the list of specialty names for an institute.

        Returns a list of specialty name strings, e.g.
        ["История", "Математика и компьютерные науки", ...].

        The eCampus endpoint is /schedule/GetSpecialities.
        It returns a JSON list of OBJECTS, not plain strings:
            [{"Id": 0, "Name": "История"}, {"Id": 0, "Name": "Физика"}, ...]

        We extract the "Name" field from each object.
        """

        params = {
            "branchId": branch_id,
            "instituteId": institute_id if not is_synthetic else None
        }

        try:
            result = await self._post_json(
                "/schedule/GetSpecialities",
                params
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"get_specialties: HTTP {exc.response.status_code} "
                    f"for institute_id={institute_id} branch={branch_id} "
                    f"body={exc.response.text[:200]}"
            )
            return []
        except Exception as exc:
            logger.error(
                f"get_specialties: {type(exc).__name__} "
                    f"for institute_id={institute_id} branch={branch_id}: "
                    f"{exc}"
            )
            return []

        # Unwrap: if the response is a dict with a known wrapper key,
        # pull out the inner list first.
        items: list = []
        if isinstance(result, list):
            items = result
        elif isinstance(result, dict):
            for key in ("Specialities", "Specialties", "Items", "Data"):
                if key in result and isinstance(result[key], list):
                    items = result[key]
                    break

        if not items:
            logger.warning(
                f"get_specialties: empty or unexpected response "
                    f"for institute_id={institute_id}: "
                    f"{type(result).__name__} {str(result)[:200]}"
            )
            return []

        # The API returns objects like {"Id": 0, "Name": "История"}.
        # Extract the "Name" string from each.  Also handle the
        # (unlikely) case where items are already plain strings.
        names: list[str] = []
        for item in items:
            if isinstance(item, dict):
                name = item.get("Name") or item.get("name") or ""
                name = str(name).strip()
                if name:
                    names.append(name)
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
            else:
                logger.debug(
                    f"get_specialties: skipping unexpected item "
                        f"type {type(item).__name__}: {str(item)[:100]}"
                )
        return names

    # ── Group discovery ────────────────────────────────────────────────────
    async def get_groups(
        self,
        institute_id: int,
        branch_id: int,
        is_synthetic: bool,
        specialty: str,
    ) -> list[dict]:
        """
        Fetch groups for a given institute + specialty name.

        The 'specialty' parameter MUST be a non-empty specialty name
        string (e.g. "История").  Passing "" returns an empty list from
        the eCampus API.
        """
        return await self._post_json(
            "/schedule/GetAcademicGroups",
            {
                "instituteId": institute_id if not is_synthetic else None,
                "branchId":    branch_id,
                "specialty":   specialty,
            },
        )

    # ── Schedule fetching ──────────────────────────────────────────────────
    async def get_week_schedule(
        self, group_id: int, monday: date,
    ) -> Any:
        monday = get_monday(monday)
        iso = monday.strftime("%Y-%m-%dT00:00:00.000Z")
        try:
            return await self._post_json(
                "/schedule/GetSchedule",
                {
                    "Id":         group_id,
                    "date":       iso,
                    "targetType": self.TARGET_GROUP,
                },
            )
        except RetryError:
            return None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
