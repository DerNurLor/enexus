"""
ecampus/client.py

Клиент для работы с порталом eCampus СКФУ.

Возможности:
  - Авторизация с решением капчи через 2captcha
  - Получение списка предметов и курсов
  - Получение оценок и успеваемости
  - Получение файлов и ссылок на материалы

Безопасность:
  - Логин/пароль хранятся зашифрованными (AES-256-GCM)
  - Сессия (cookie) хранится в Redis с TTL 3 часа
  - Капча решается через 2captcha API
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger

ECAMPUS_BASE    = "https://ecampus.ncfu.ru"
CAPTCHA_URL     = f"{ECAMPUS_BASE}/Captcha/Captcha"
LOGIN_URL       = f"{ECAMPUS_BASE}/account/login?returnUrl=%2Faccount"
STUDIES_URL     = f"{ECAMPUS_BASE}/studies"
GET_COURSES_URL = f"{ECAMPUS_BASE}/studies/GetCourses"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class ECampusAuthError(Exception):
    """Ошибка авторизации на eCampus."""
    pass


class ECampusCaptchaError(Exception):
    """Не удалось решить капчу."""
    pass


class ECampusClient:
    """
    Асинхронный клиент для eCampus СКФУ.

    Использование:
        client = ECampusClient(login="user@ncfu.ru", password="secret", captcha_api_key="2captcha_key")
        async with client:
            await client.login()
            courses = await client.get_courses()
    """

    def __init__(
        self,
        login: str,
        password: str,
        captcha_api_key: str,
        session_cookies: dict | None = None,
    ):
        self.login_str     = login
        self.password      = password
        self.captcha_key   = captcha_api_key
        self._client: httpx.AsyncClient | None = None
        self._cookies      = session_cookies or {}
        self._csrf_token   = ""

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=60,
        )
        # Восстанавливаем сохранённые cookies
        for k, v in self._cookies.items():
            self._client.cookies.set(k, v)
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    # ── Авторизация ──────────────────────────────────────────────────────────

    async def authenticate(self) -> dict:
        """
        Полный цикл авторизации:
        1. Получить страницу входа → CSRF токен
        2. Получить капчу → решить через 2captcha
        3. Отправить форму входа
        4. Вернуть cookies для сохранения

        Returns: dict с cookies сессии
        """
        assert self._client is not None

        # Шаг 1: получаем страницу входа и CSRF токен
        resp = await self._client.get(LOGIN_URL)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        token_el = soup.find("input", {"name": "__RequestVerificationToken"})
        if not token_el:
            raise ECampusAuthError("Не найден __RequestVerificationToken на странице входа")

        self._csrf_token = token_el.get("value", "")
        logger.debug(f"CSRF token obtained: {self._csrf_token[:20]}...")

        # Шаг 2: получаем и решаем капчу
        captcha_text = await self._solve_captcha()
        logger.debug(f"Captcha solved: {captcha_text}")

        # Шаг 3: отправляем форму входа
        form_data = {
            "Login":                       self.login_str,
            "Password":                    self.password,
            "CaptchaCode":                 captcha_text,
            "__RequestVerificationToken":  self._csrf_token,
        }

        resp = await self._client.post(
            LOGIN_URL,
            data=form_data,
            headers={
                "Content-Type":    "application/x-www-form-urlencoded",
                "Referer":         LOGIN_URL,
                "Origin":          ECAMPUS_BASE,
                "Upgrade-Insecure-Requests": "1",
            },
        )

        # Проверяем успешность входа
        if "account/login" in str(resp.url) or "validation-summary-errors" in resp.text:
            soup = BeautifulSoup(resp.text, "html.parser")
            err_el = soup.select_one(".validation-summary-errors ul li")
            err_msg = err_el.text.strip() if err_el else "Неверный логин или пароль"
            raise ECampusAuthError(f"Ошибка входа: {err_msg}")

        # Сохраняем cookies
        cookies = dict(self._client.cookies)
        self._cookies = cookies
        logger.info(f"eCampus auth success for {self.login_str}")
        return cookies

    async def _solve_captcha(self) -> str:
        """
        Получает изображение капчи и решает его через 2captcha API.
        """
        assert self._client is not None

        # Получаем изображение капчи
        resp = await self._client.get(
            CAPTCHA_URL,
            headers={"Referer": LOGIN_URL},
        )
        resp.raise_for_status()

        # Сохраняем captcha cookie
        captcha_cookie = self._client.cookies.get("captcha", "")

        # Кодируем изображение в base64
        img_base64 = base64.b64encode(resp.content).decode()

        # Отправляем в 2captcha
        return await self._submit_to_2captcha(img_base64)

    async def _submit_to_2captcha(self, img_base64: str) -> str:
        """
        Отправляет изображение капчи в 2captcha и ждёт результата.
        """
        assert self._client is not None

        # Отправляем задание
        submit_resp = await self._client.post(
            "https://2captcha.com/in.php",
            data={
                "key":    self.captcha_key,
                "method": "base64",
                "body":   img_base64,
                "json":   "1",
            },
        )
        result = submit_resp.json()
        if result.get("status") != 1:
            raise ECampusCaptchaError(f"2captcha reject: {result}")

        captcha_id = result["request"]
        logger.debug(f"2captcha task ID: {captcha_id}")

        # Ждём решения (polling каждые 5 секунд, максимум 2 минуты)
        for attempt in range(24):
            await asyncio.sleep(5)
            poll_resp = await self._client.get(
                "https://2captcha.com/res.php",
                params={"key": self.captcha_key, "action": "get", "id": captcha_id, "json": "1"},
            )
            poll = poll_resp.json()

            if poll.get("status") == 1:
                return poll["request"]

            if poll.get("request") not in ("CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"):
                raise ECampusCaptchaError(f"2captcha error: {poll}")

        raise ECampusCaptchaError("2captcha timeout: капча не решена за 2 минуты")

    # ── Данные eCampus ───────────────────────────────────────────────────────

    async def get_studies_viewmodel(self) -> dict:
        """
        Получает viewModel со страницы /studies.
        Содержит список семестров и другую мета-информацию.
        """
        assert self._client is not None
        resp = await self._client.get(STUDIES_URL)
        resp.raise_for_status()

        # Ищем viewModel в JS на странице
        match = re.search(r'viewModel\s*=\s*(\{.+?\});', resp.text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Альтернатива — парсим через BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        return {"raw_html": resp.text[:5000]}

    async def get_courses(self, student_id: int, term_id: int) -> list[dict]:
        """
        Получает список предметов студента за семестр.
        """
        assert self._client is not None
        resp = await self._client.post(
            GET_COURSES_URL,
            json={"studentId": student_id, "termId": term_id},
            headers={
                "Content-Type":     "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Referer":          STUDIES_URL,
                "Origin":           ECAMPUS_BASE,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("courses", [])

    async def get_grades(self, course_url: str) -> dict:
        """
        Получает оценки по конкретному курсу.
        """
        assert self._client is not None
        url = course_url if course_url.startswith("http") else f"{ECAMPUS_BASE}{course_url}"
        resp = await self._client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        grades = []

        # Парсим таблицу оценок
        for row in soup.select("table.grades-table tr, table tr"):
            cells = [td.text.strip() for td in row.select("td")]
            if cells:
                grades.append(cells)

        # Ищем ссылки на файлы и ресурсы
        files = []
        links = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.text.strip()
            if any(ext in href.lower() for ext in [".pdf", ".doc", ".docx", ".xlsx", ".ppt", ".zip", ".rar"]):
                files.append({"name": text, "url": href if href.startswith("http") else f"{ECAMPUS_BASE}{href}"})
            elif href.startswith("http") and "ecampus.ncfu.ru" not in href:
                links.append({"name": text, "url": href})

        return {
            "grades": grades,
            "files":  files,
            "links":  links,
        }

    def get_cookies(self) -> dict:
        """Возвращает текущие cookies для сохранения в Redis/БД."""
        return self._cookies

    async def get_lessons(self, lesson_type_id: int, student_id: int) -> list[dict]:
        """Получает занятия и оценки для конкретного типа занятий."""
        assert self._client is not None
        resp = await self._client.post(
            f"{ECAMPUS_BASE}/studies/GetLessons",
            json={"lessonTypeId": lesson_type_id, "studentId": student_id},
            headers={
                "Content-Type":     "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Referer":          STUDIES_URL,
                "Origin":           ECAMPUS_BASE,
            },
        )
        if not resp.is_success:
            return []
        data = resp.json()
        if not isinstance(data, list):
            return []
        # Очищаем "None" строки
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if v == 'None' or v == 'null':
                        item[k] = None
        return data
