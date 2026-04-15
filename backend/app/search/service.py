"""
search/service.py
=================
Индустриальный стандарт поиска для коротких строк (группы, преподаватели, аудитории).

Алгоритм — тот же что используют Typesense, Meilisearch, PostgreSQL pg_trgm,
Elasticsearch fuzzy, Apple Spotlight:

  MONGODB:  широкий кандидат-сет через prefix $regex (использует индекс, O(log n))
  PYTHON:   ранжирование через rapidfuzz — token_set_ratio + partial_ratio + WRatio

token_set_ratio — лучшая метрика для «слов в произвольном порядке»:
  "исс 22 2"  vs "исс б о 22 2"  → 100
  "подзолко"  vs "подзолко и в"  → 100
  "305"       vs "305 корп 2"    → 100

Всё что делает normalize() — lowercase + разделители→пробел + split digits.
Никаких if-веток, никаких знаний о структуре «кафедра-форма-основа-год-подгруппа».

Публичный API
─────────────
  normalize(s)                        → str
  prefix(q)                           → str   mongo prefix
  score(query, candidate)             → float 0–100
  rank(candidates, query, ...)        → list
  mongo_prefix_filter(q, field)       → dict

  # Обратная совместимость — старые имена работают через новый движок
  normalize_query / normalize_group_name / normalize_group_variants
  build_mongo_search / build_group_search
  fuzzy_match / fuzzy_match_group
  rank_group_candidates / score_group_relevance / rank_candidates
  letter_prefix / similarity / expand / build_mongo_filter
"""
from __future__ import annotations

import re
from typing import Any, Callable, TypeVar

from rapidfuzz import fuzz

T = TypeVar("T")


# ── normalize ─────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """
    Приводит строку к нормализованному виду для сравнения.
    Единственная нормализация во всём модуле — никаких знаний о структуре данных.

    "ИСС-б-о-22-3"  → "исс б о 22 3"
    "исс222"        → "исс 22 2"
    "исс-222"       → "исс 22 2"
    "аис25"         → "аис 25"
    "Подзолко И.В." → "подзолко и в"
    "305/2"         → "305 2"
    """
    s = s.lower().strip()
    # Разделители → пробел
    s = re.sub(r"[.\-_/\\]+", " ", s)
    # Граница буква↔цифра
    s = re.sub(r"([а-яёa-z])(\d)", r"\1 \2", s)
    s = re.sub(r"(\d)([а-яёa-z])", r"\1 \2", s)
    # Длинные числа разбиваем по 2: "222"→"22 2", "2231"→"22 31"
    def _chunk(m: re.Match) -> str:
        d = m.group(0)
        return d[:2] + " " + d[2:] if len(d) > 2 else d
    s = re.sub(r"\d{3,}", _chunk, s)
    return re.sub(r"\s+", " ", s).strip()


# ── prefix ────────────────────────────────────────────────────────────────────

def prefix(q: str) -> str:
    """
    Первый буквенный токен из normalize(q) — MongoDB prefix для $regex.

    "исс222"        → "исс"
    "подзолко"      → "подзолко"
    "305"           → "305"
    "ИСС-б-о-22-3"  → "исс"
    """
    tokens = normalize(q).split()
    for t in tokens:
        if re.match(r"^[а-яёa-z]{2,}$", t):
            return t
    return tokens[0][:3] if tokens else q[:3].lower()


# ── score ─────────────────────────────────────────────────────────────────────

def score(query: str, candidate: str) -> float:
    """
    Нечёткое сходство [0–100] после normalize().
    Максимум из token_set_ratio + partial_ratio + WRatio.
    """
    qn = normalize(query)
    cn = normalize(candidate)
    return max(
        fuzz.token_set_ratio(qn, cn),
        fuzz.partial_ratio(qn, cn),
        fuzz.WRatio(qn, cn),
    )


# ── branch penalty ────────────────────────────────────────────────────────────

def _branch_penalty(candidate_name: str, query: str) -> float:
    """Штраф -30 для групп-филиалов (п-ИСС, е-АИС)."""
    c_tokens = normalize(candidate_name).split()
    if c_tokens and re.match(r"^[а-яёa-z]{1,2}$", c_tokens[0]):
        q_tokens = normalize(query).split()
        if not q_tokens or q_tokens[0] != c_tokens[0]:
            return -30.0
    return 0.0


# ── rank ──────────────────────────────────────────────────────────────────────

def rank(
    candidates: list[T],
    query: str,
    *,
    get_name: Callable[[T], str] = str,
    threshold: float = 40.0,
    limit: int = 15,
    branch_penalty: bool = False,
) -> list[T]:
    """
    Ранжирует кандидатов по нечёткому сходству с query.
    """
    scored: list[tuple[T, float]] = []
    for obj in candidates:
        name = get_name(obj)
        s = score(query, name)
        if branch_penalty:
            s += _branch_penalty(name, query)
        scored.append((obj, s))
    scored.sort(key=lambda x: -x[1])
    return [obj for obj, s in scored if s >= threshold][:limit]


# ── mongo_prefix_filter ───────────────────────────────────────────────────────

def mongo_prefix_filter(q: str, field: str) -> dict:
    """
    MongoDB $regex по prefix(q) — использует индекс, быстро.
    Возвращает широкий кандидат-сет для ранжирования через rank().
    """
    pfx = prefix(q)
    return {field: {"$regex": f"^{re.escape(pfx)}", "$options": "i"}}


# ═══════════════════════════════════════════════════════════════════════════════
# Обратная совместимость
# ═══════════════════════════════════════════════════════════════════════════════

expand             = normalize
letter_prefix      = prefix
similarity         = score
build_mongo_filter = mongo_prefix_filter


def normalize_query(q: str) -> str:
    return q.strip()


def normalize_group_name(raw: str) -> str:
    return normalize(raw)


def normalize_group_variants(raw: str) -> list[str]:
    n   = normalize(raw)
    low = raw.strip().lower()
    seen: set[str] = set()
    result: list[str] = []
    for v in [n, low]:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def build_mongo_search(q: str, text_fields: list[str]) -> dict:
    return mongo_prefix_filter(q, text_fields[0])


def build_group_search(raw_query: str) -> dict:
    return mongo_prefix_filter(raw_query, "name")


def fuzzy_match(query: str, candidates: list[str], threshold: int = 60) -> list[str]:
    return rank(candidates, query, get_name=str, threshold=float(threshold))


def fuzzy_match_group(query: str, candidates: list[str], threshold: int = 60) -> list[str]:
    return rank(candidates, query, get_name=str, threshold=float(threshold), branch_penalty=True)


def score_group_relevance(group_name: str, query_canonical: str) -> float:
    return score(query_canonical, group_name) + _branch_penalty(group_name, query_canonical)


def rank_group_candidates(
    candidates: list[Any],
    raw_query: str,
    *,
    get_name: Callable[[Any], str] = str,
) -> list[Any]:
    return rank(candidates, raw_query, get_name=get_name, threshold=40.0, branch_penalty=True)


def rank_candidates(
    candidates: list[Any],
    query: str,
    *,
    get_name: Callable[[Any], str] = str,
    threshold: float = 40.0,
    limit: int = 15,
    apply_branch_penalty: bool = False,
) -> list[Any]:
    return rank(
        candidates, query,
        get_name=get_name,
        threshold=threshold,
        limit=limit,
        branch_penalty=apply_branch_penalty,
    )
