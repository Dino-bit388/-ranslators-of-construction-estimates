import re

HEADER_PATTERNS = {
    "code": ["обоснование", "шифр", "код", "номер расценки"],
    "name": ["наименование", "наименование работ", "материал"],
    "unit": ["ед изм", "единица измерения", "ед"],
    "quantity": ["количество", "кол во"],
    "price": ["цена", "стоимость"],
}

NORMATIVE_CODE_PATTERN = re.compile(r"^(ГЭСН|ФЕР|ТЕР|ФССЦ|ФСБЦ)\w*[\d\-.]+", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(раздел|часть|глава)\s*[№#]?\s*\d+", re.IGNORECASE)
TOTAL_PATTERN = re.compile(r"(итого|всего|составил|проверил)", re.IGNORECASE)


def normalize_text(value) -> str:
    text = str(value).lower() if value is not None else ""
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _match_header_field(cell_text: str) -> str | None:
    tokens = set(cell_text.split())
    for field_name, variants in HEADER_PATTERNS.items():
        for variant in variants:
            variant_tokens = set(normalize_text(variant).split())
            if variant_tokens.issubset(tokens):
                return field_name
    return None