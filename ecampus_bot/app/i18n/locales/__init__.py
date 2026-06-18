"""Реестр всех поддерживаемых языков. ru — источник истины, остальные переводятся с него."""
from . import ru, en, zh, ar, es, fr, tr, kk, az, hy, uz, tg, hi, vi

DEFAULT_LANG = "ru"

LOCALES: dict[str, dict[str, str]] = {
    "ru": ru.MESSAGES,
    "en": en.MESSAGES,
    "zh": zh.MESSAGES,
    "ar": ar.MESSAGES,
    "es": es.MESSAGES,
    "fr": fr.MESSAGES,
    "tr": tr.MESSAGES,
    "kk": kk.MESSAGES,
    "az": az.MESSAGES,
    "hy": hy.MESSAGES,
    "uz": uz.MESSAGES,
    "tg": tg.MESSAGES,
    "hi": hi.MESSAGES,
    "vi": vi.MESSAGES,
}

# Имя языка на самом этом языке — для клавиатуры /language
LANGUAGE_NAMES: dict[str, str] = {
    "ru": "Русский",
    "en": "English",
    "zh": "中文",
    "ar": "العربية",
    "es": "Español",
    "fr": "Français",
    "tr": "Türkçe",
    "kk": "Қазақша",
    "az": "Azərbaycan",
    "hy": "Հայերեն",
    "uz": "O'zbek",
    "tg": "Тоҷикӣ",
    "hi": "हिन्दी",
    "vi": "Tiếng Việt",
}

SUPPORTED_LANGUAGES: list[str] = list(LOCALES.keys())
