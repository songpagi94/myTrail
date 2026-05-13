"""고정 형식 텍스트를 intent dict로 파싱."""

import datetime
import logging
import re

from ..rail.srt.constants import normalize_station as _srt_normalize

logger = logging.getLogger(__name__)

_SEAT_ALIAS: dict[str, str] = {
    "일반만": "GENERAL_ONLY",
    "일반우선": "GENERAL_FIRST",
    "일반": "GENERAL_ONLY",
    "특실만": "SPECIAL_ONLY",
    "특실우선": "SPECIAL_FIRST",
    "특실": "SPECIAL_FIRST",
}

# KTX 역명 별칭 (코레일 API는 한국어 역명을 직접 수신)
_KTX_ALIAS: dict[str, str] = {}


class ParseError(Exception):
    """파싱 실패."""


def _normalize_date(s: str) -> str:
    """YYYYMMDD / YYYY-MM-DD / MM/DD → YYYY-MM-DD"""
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    if re.fullmatch(r"\d{1,2}/\d{1,2}", s):
        m, d = s.split("/")
        year = datetime.date.today().year
        return f"{year}-{int(m):02d}-{int(d):02d}"
    raise ParseError(f"날짜 형식 오류: '{s}' — YYYYMMDD, YYYY-MM-DD, 또는 MM/DD")


def _normalize_time(s: str) -> str:
    """HHMM / HH:MM → HHMMSS"""
    clean = s.replace(":", "")
    if re.fullmatch(r"\d{4}", clean):
        return clean + "00"
    if re.fullmatch(r"\d{6}", clean):
        return clean
    raise ParseError(f"시간 형식 오류: '{s}' — HHMM 또는 HH:MM")


def _normalize_station(name: str, rail: str) -> str:
    if rail == "SRT":
        return _srt_normalize(name)
    return _KTX_ALIAS.get(name, name)


def _parse_rail(tok: str) -> str | None:
    upper = tok.upper()
    if upper == "SRT":
        return "SRT"
    if upper in ("KTX", "코레일"):
        return "KTX"
    return None


def parse(text: str, today: str | None = None, **_kwargs) -> dict:
    """고정 형식 텍스트 → intent dict.

    형식: 출발역 도착역 날짜(YYYYMMDD) 시간(HHMM) [SRT|KTX] [좌석옵션]
    예:  서울 부산 20260515 1400
         서울 부산 20260515 1400 KTX 특실우선
    """
    tokens = text.strip().split()
    if len(tokens) < 4:
        raise ParseError(
            "입력 형식: 출발역 도착역 날짜(YYYYMMDD) 시간(HHMM) [SRT|KTX] [좌석옵션]\n"
            "예: 서울 부산 20260515 1400"
        )

    dep_raw, arr_raw, date_raw, time_raw = tokens[:4]

    date = _normalize_date(date_raw)
    time_val = _normalize_time(time_raw)

    rail = "SRT"
    seat_pref = "GENERAL_ONLY"
    for tok in tokens[4:]:
        r = _parse_rail(tok)
        if r:
            rail = r
        elif tok in _SEAT_ALIAS:
            seat_pref = _SEAT_ALIAS[tok]
        else:
            raise ParseError(
                f"'{tok}' 미인식 — 사용 가능: SRT, KTX, 일반만, 일반우선, 특실만, 특실우선"
            )

    dep = _normalize_station(dep_raw, rail)
    arr = _normalize_station(arr_raw, rail)

    return {
        "rail": rail,
        "dep": dep,
        "arr": arr,
        "date": date,
        "time": time_val,
        "passengers": {"adult": 1, "child": 0, "senior": 0},
        "seat_pref": seat_pref,
        "needs_clarification": [],
    }
