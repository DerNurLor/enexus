#!/usr/bin/env python3
"""Добавляет twocaptcha_api_key в config.py бэкенда."""

CONFIG_PATH = "/opt/ncfu/backend/app/core/config.py"

with open(CONFIG_PATH, "r") as f:
    content = f.read()

if "twocaptcha_api_key" not in content:
    for search in ["ecampus_encryption_key", "jwt_secret", "telegram_bot_token"]:
        idx = content.find(search)
        if idx > 0:
            end = content.find("\n", idx)
            content = content[:end+1] + '    twocaptcha_api_key: str = ""\n' + content[end+1:]
            print(f"Added twocaptcha_api_key after {search}")
            break
    with open(CONFIG_PATH, "w") as f:
        f.write(content)
    print("config.py updated OK")
else:
    print("Already exists")
