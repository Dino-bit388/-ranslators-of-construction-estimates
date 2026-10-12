import re


def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def normalize_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("\xa0", " ")
    if text in ("", "-", "—"):
        return None
    text = text.replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_unit(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    text = re.sub(r"\.$", "", text)   # убрать точку в конце: "кг." → "кг"
    return text or None