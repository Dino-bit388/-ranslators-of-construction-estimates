import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.parser.excel_parser import ExcelParser


def diagnose(filepath: str):
    parser = ExcelParser(filepath)
    estimate = parser.parse()

    total = len(parser.diagnostics)
    unknown = sum(1 for d in parser.diagnostics if d["type"] == "unknown")

    print(f"\n{filepath}")
    print(f"Разделов: {len(estimate.sections)}")
    print(f"Не распознано: {unknown}/{total} строк ({unknown / total:.0%})" if total else "Нет строк данных")

    for d in parser.diagnostics:
        print(f"  {d['row']:>4}  {d['type']:<10}  conf={d['confidence']}")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        diagnose(path)