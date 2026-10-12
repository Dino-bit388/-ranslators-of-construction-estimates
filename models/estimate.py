from dataclasses import dataclass, field
from models.metadata import EstimateMetadata
from models.section import Section


@dataclass
class Estimate:
    metadata: EstimateMetadata
    sections: list[Section] = field(default_factory=list)