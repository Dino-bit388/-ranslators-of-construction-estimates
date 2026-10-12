from enum import Enum

class EstimateRowType(Enum):
    HEADER = "header"
    SECTION = "section"
    WORK = "work"
    RESOURCE = "resource"
    TOTAL = "total"
    UNKNOWN = "unknown"