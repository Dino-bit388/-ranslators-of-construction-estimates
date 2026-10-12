from dataclasses import dataclass, field
from models.resource import Resource


@dataclass
class Work:
    code: str | None
    name: str
    unit: str | None = None
    quantity: float | None = None
    resources: list[Resource] = field(default_factory=list)