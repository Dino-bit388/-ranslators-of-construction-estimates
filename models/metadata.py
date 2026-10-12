from dataclasses import dataclass


@dataclass
class EstimateMetadata:
    object_name: str | None = None
    estimate_name: str | None = None
    normative_base: str | None = None
    region: str | None = None
    date: str | None = None