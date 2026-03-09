"""
search/service.py
=================
Нормализация запросов и построение MongoDB-фильтров.

normalize_group_name() — ключевая функция для сопоставления названий групп.
Покрывает сценарии:
  • замена пробелов ↔ дефисов:  "ИСС б о 22 3" → "ИСС-б-о-22-3"
  • регистр:                    "исс-Б-О-22-3" → нижний для поиска
  • лишние/пропущенные символы: "ИСС--б-о--22-3", "ИСС б  о22 3"
  • транслитерация латиницы:    "ISS-b-o-22-3" → кириллица
  • опечатки и перестановки:    fuzzy matching
  • сокращения:                 "аис25" → "аис-б-о-25"
"""

import re
from rapidfuzz import process as fz_process, fuzz

try:
    from transliterate import translit
    _TRANSLIT = True
except ImportError:
    _TRANSLIT = False


ABBREVIATIONS: dict[str, str] = {
    "СКФУ": "Северо-Кавказский федеральный университет",
}


def normalize_query(q: str) -> str:
    q = q.strip()
    for abbr, full in ABBREVIATIONS.items():
        q = q.replace(abbr, full)
    if _TRANSLIT and re.search(r"[a-zA-Z]", q):
        try:
            from transliterate import translit
            q = translit(q, "ru")
        except Exception:
            pass
    return q.strip()


_FORM_ALIASES: dict[str, str] = {
    "бак": "б", "бакалавр": "б", "bak": "б",
    "маг": "м", "магистр": "м",
    "асп": "а", "аспирант": "а",
    "спец": "с", "специалист": "с",
    "b": "б", "m": "м",
}

_BASE_ALIASES: dict[str, str] = {
    "очная": "о", "очн": "о",
    "заочная": "з", "заоч": "з",
    "очно-заочная": "оз",
}

# Простая таблица транслитерации для одиночных букв
_LAT_TO_CYR = {
    'a': 'а', 'b': 'б', 'c': 'с', 'd': 'd', 'e': 'е',
    'g': 'г', 'h': 'х', 'i': 'и', 'j': 'й', 'k': 'к',
    'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п',
    'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
    'v': 'в', 'w': 'в', 'x': 'кс', 'y': 'ы', 'z': 'з',
}


def normalize_group_name(raw: str) -> str:
    """
    Нормализует произвольное написание названия учебной группы
    к каноническому виду: «кафедра-б-о-гг-н» (нижний регистр).

    Примеры:
      "ИСС-б-о-22-3"   → "исс-б-о-22-3"
      "исс б о 22 3"   → "исс-б-о-22-3"
      "ИСС  Б О 22  3" → "исс-б-о-22-3"
      "исс-б-о22-3"    → "исс-б-о-22-3"
      "ISS-b-o-22-3"   → "исс-б-о-22-3"
      "аис25"           → "аис-б-о-25"
      "аис-25-3"        → "аис-б-о-25-3"
    """
    s = raw.strip()

    # 1. Транслитерировать латиницу → кириллицу (библиотека, если есть)
    if _TRANSLIT and re.search(r"[a-zA-Z]", s):
        try:
            from transliterate import translit
            s = translit(s, "ru")
        except Exception:
            pass

    # 2. Нижний регистр
    s = s.lower()

    # 3. Оставшиеся латинские буквы — побуквенно
    def _lat_char(m):
        res = _LAT_TO_CYR.get(m.group(0))
        return res if res is not None else m.group(0)
    s = re.sub(r'[a-z]', _lat_char, s)

    # 4. Пробелы/дефисы/подчёркивания → дефис
    s = re.sub(r'[\s\-_/\\]+', '-', s)

    # 5. Убрать всё кроме букв, цифр, дефиса
    s = re.sub(r'[^\w\-]', '', s, flags=re.UNICODE)
    s = s.strip('-')

    # 6. Разбить на токены
    tokens = [t for t in s.split('-') if t]

    # 7. Заменить алиасы формы/основы
    tokens = [_FORM_ALIASES.get(t, _BASE_ALIASES.get(t, t)) for t in tokens]

    # 8. Короткая запись "аис25" / "аис253" → "аис-б-о-25-3"
    if len(tokens) == 1 and re.match(r'^[а-яё]+\d{2,}$', tokens[0]):
        m = re.match(r'^([а-яё]+)(\d{2})(\d?)$', tokens[0])
        if m:
            tokens = [m.group(1), "б", "о", m.group(2)]
            if m.group(3):
                tokens.append(m.group(3))

    # 9. Если 2 токена вида "кафедра-25" — добавить б-о между ними
    if len(tokens) == 2 and re.match(r'^\d{2}$', tokens[1]):
        tokens = [tokens[0], "б", "о", tokens[1]]

    return '-'.join(tokens)


def normalize_group_variants(raw: str) -> list[str]:
    """
    Возвращает несколько вариантов нормализации одного запроса.
    Используется для $or-поиска в MongoDB.
    """
    canonical = normalize_group_name(raw)
    lower_raw = raw.strip().lower()
    # Вариант без разделителей: "иссбо223"
    no_sep = re.sub(r'[\s\-_]+', '', canonical)
    # Дедупликация с сохранением порядка
    seen, variants = set(), []
    for v in [canonical, lower_raw, no_sep]:
        if v and v not in seen:
            seen.add(v)
            variants.append(v)
    return variants


def fuzzy_match(query: str, candidates: list[str], threshold: int = 75) -> list[str]:
    if not candidates:
        return []
    results = fz_process.extract(query, candidates, scorer=fuzz.WRatio, limit=20)
    return [r[0] for r in results if r[1] >= threshold]


def fuzzy_match_group(query: str, candidates: list[str], threshold: int = 70) -> list[str]:
    """
    Fuzzy-match для групп: нормализуем и запрос, и кандидатов,
    чтобы регистр/дефисы/пробелы не влияли на score.
    """
    if not candidates:
        return []
    norm_query = normalize_group_name(query)
    norm_map = {normalize_group_name(c): c for c in candidates}
    results = fz_process.extract(
        norm_query, list(norm_map.keys()),
        scorer=fuzz.WRatio, limit=10,
    )
    return [norm_map[r[0]] for r in results if r[1] >= threshold]


def build_mongo_search(q: str, text_fields: list[str]) -> dict:
    """Build a $text or $regex query depending on query length."""
    if len(q) >= 3:
        return {"$text": {"$search": q, "$language": "russian"}}
    return {text_fields[0]: {"$regex": f"^{re.escape(q)}", "$options": "i"}}


def build_group_search(raw_query: str) -> dict:
    """
    MongoDB filter для поиска группы, устойчивый к опечаткам,
    разным разделителям, регистру и сокращениям.

    Стратегия:
      1. $text на канонической форме (использует индекс, быстро)
      2. $regex на каждом из вариантов (fallback)
    Возвращает $or всех условий.
    """
    variants = normalize_group_variants(raw_query)
    conditions: list[dict] = []

    canonical = variants[0]
    # $text поиск — убираем дефисы, т.к. $text их игнорирует
    text_query = re.sub(r'-', ' ', canonical)
    if len(text_query.strip()) >= 3:
        conditions.append({"$text": {"$search": text_query, "$language": "russian"}})

    # Regex для каждого варианта
    for v in variants:
        if not v:
            continue
        # Разрешаем любые разделители между токенами
        flex = re.escape(v)
        flex = re.sub(r'(\\\s|\\-|_)+', r'[\\s\\-_]*', flex)
        conditions.append({"name": {"$regex": flex, "$options": "i"}})

    if not conditions:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"$or": conditions}
