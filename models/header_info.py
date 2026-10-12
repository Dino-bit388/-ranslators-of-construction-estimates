from dataclasses import dataclass, field


@dataclass
class HeaderInfo:
    start_row: int                      
    end_row: int                        
    data_start_row: int                 
    columns: dict[str, int] = field(default_factory=dict)   