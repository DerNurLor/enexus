"""
app/ecampus/captcha_solver.py
Решение математических капч eCampus через 2captcha API.
Капча вида "5 + 8 = " — нужно вернуть ответ.
"""
from __future__ import annotations
import asyncio
import base64
import httpx
from loguru import logger

TWOCAPTCHA_SUBMIT_URL = "https://2captcha.com/in.php"
TWOCAPTCHA_RESULT_URL = "https://2captcha.com/res.php"

POLL_INTERVAL = 3      # секунды между проверками
POLL_TIMEOUT  = 120    # максимальное время ожидания


async def solve_math_captcha(image_bytes: bytes, api_key: str) -> str | None:
    """
    Отправляет изображение капчи в 2captcha и возвращает ответ (число).
    Возвращает None при ошибке.
    """
    if not api_key:
        logger.warning("2captcha API key not configured")
        return None

    b64 = base64.b64encode(image_bytes).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Отправляем капчу
        try:
            resp = await client.post(TWOCAPTCHA_SUBMIT_URL, data={
                "key":    api_key,
                "method": "base64",
                "body":   b64,
                "json":   1,
                # Подсказка — математическое выражение
                "textinstructions": "Решите математическое выражение и введите только цифровой ответ",
                "numeric": 1,         # ожидаем только цифры
                "min_len": 1,
                "max_len": 3,
            })
            data = resp.json()
        except Exception as e:
            logger.error(f"2captcha submit error: {e}")
            return None

        if data.get("status") != 1:
            logger.error(f"2captcha submit failed: {data}")
            return None

        captcha_id = data.get("request")
        if not captcha_id:
            return None

        logger.info(f"2captcha task submitted: {captcha_id}")

        # 2. Опрашиваем результат
        elapsed = 0
        await asyncio.sleep(5)  # минимальное ожидание перед первым запросом

        while elapsed < POLL_TIMEOUT:
            try:
                res = await client.get(TWOCAPTCHA_RESULT_URL, params={
                    "key":    api_key,
                    "action": "get",
                    "id":     captcha_id,
                    "json":   1,
                })
                result = res.json()
            except Exception as e:
                logger.error(f"2captcha poll error: {e}")
                return None

            if result.get("status") == 1:
                answer = str(result.get("request", "")).strip()
                logger.info(f"2captcha solved: {captcha_id} → {answer}")
                return answer

            if result.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                logger.warning("2captcha: captcha unsolvable")
                return None

            # CAPCHA_NOT_READY — ждём ещё
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        logger.warning(f"2captcha timeout after {POLL_TIMEOUT}s")
        return None


async def report_incorrect(captcha_id: str, api_key: str) -> None:
    """Сообщаем 2captcha что ответ был неверным (для повышения точности)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(TWOCAPTCHA_RESULT_URL, params={
                "key":    api_key,
                "action": "reportbad",
                "id":     captcha_id,
            })
    except Exception:
        pass
