from dataclasses import dataclass


@dataclass
class Resource:
    name: str
    unit: str | None
    quantity: float | None
    row_number: int
    code: str | None = None
    coefficient: float | None = None 