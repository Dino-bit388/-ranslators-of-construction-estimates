from dataclasses import dataclass, field
from models.work import Work

@dataclass
class Section:
    name: str
    number: int | None = None
    works: list[Work] = field(default_factory=list)