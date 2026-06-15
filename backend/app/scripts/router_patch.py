#!/usr/bin/env python3
"""
Добавляет эндпоинт /ecampus/captcha/solve в router.py
и обновляет /ecampus/connect для автокапчи.
"""
import sys

ROUTER_PATH = "/opt/ncfu/backend/app/ecampus/router.py"

with open(ROUTER_PATH, "r") as f:
    content = f.read()

if "captcha_solver" not in content:
    content = content.replace(
        "from app.auth.dependencies import get_current_user",
        "from app.auth.dependencies import get_current_user\nfrom app.ecampus.captcha_solver import solve_math_captcha"
    )

SOLVE_ENDPOINT = '''

@router.get("/captcha/solve")
async def solve_captcha_auto(current_user: AuthUser = Depends(get_current_user)):
    """
    Получает картинку капчи с eCampus и решает её через 2captcha.
    Возвращает { answer, captcha_cookie } для использования при connect.
    """
    from app.core.config import settings
    import httpx, base64

    api_key = getattr(settings, "twocaptcha_api_key", "") or ""
    if not api_key:
        raise HTTPException(status_code=503, detail="2captcha API key не настроен.")

    ecampus_base = "https://ecampus.ncfu.ru"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        login_page = await client.get(f"{ecampus_base}/account/login")
        csrf_token = ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_el = soup.find("input", {"name": "__RequestVerificationToken"})
        if csrf_el:
            csrf_token = csrf_el.get("value", "")

        captcha_resp = await client.get(f"{ecampus_base}/Captcha/Captcha")
        if not captcha_resp.is_success:
            raise HTTPException(status_code=502, detail="Не удалось получить капчу с eCampus.")

        image_bytes = captcha_resp.content
        captcha_cookie = dict(client.cookies).get("captcha", "")

    # Решаем через 2captcha
    answer = await solve_math_captcha(image_bytes, api_key)
    if not answer:
        raise HTTPException(status_code=502, detail="Не удалось решить капчу. Попробуйте вручную.")

    return {
        "answer":         answer,
        "captcha_cookie": captcha_cookie,
        "csrf_token":     csrf_token,
    }
'''

if "/captcha/solve" not in content:
    insert_after = "@router.get(\"/captcha\")"
    idx = content.find(insert_after)
    if idx > 0:
        next_router = content.find("\n@router.", idx + len(insert_after))
        if next_router > 0:
            content = content[:next_router] + SOLVE_ENDPOINT + content[next_router:]
            print("Added /captcha/solve endpoint")
        else:
            content += SOLVE_ENDPOINT
            print("Added /captcha/solve endpoint at end")
    else:
        print("ERROR: Could not find get_captcha endpoint")
        sys.exit(1)
else:
    print("Endpoint already exists")

with open(ROUTER_PATH, "w") as f:
    f.write(content)

print("router.py updated OK")
