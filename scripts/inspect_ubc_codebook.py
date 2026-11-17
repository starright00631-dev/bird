"""Inspect the De Groot READ.ME workbook without assuming its column mapping.

The output is a bounded, reproducible schema preview. It is not a data
transformation and does not authorize joining the six source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


def _json_value(value: Any, max_cell_chars: int) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    rendered = str(value)
    if len(rendered) > max_cell_chars:
        return rendered[: max_cell_chars - 3] + "..."
    return rendered


def inspect_codebook(
    path: str | Path,
    *,
    max_preview_rows: int = 40,
    max_preview_columns: int = 24,
    max_cell_chars: int = 240,
) -> dict:
    """Return workbook metadata and a bounded non-empty preview for every sheet."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if max_preview_rows < 1 or max_preview_columns < 1 or max_cell_chars < 8:
        raise ValueError("Preview limits must be positive and max_cell_chars >= 8")

    payload = source.read_bytes()
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        sheets = []
        for worksheet in workbook.worksheets:
            preview_rows = []
            row_limit = min(worksheet.max_row or 0, max_preview_rows)
            column_limit = min(worksheet.max_column or 0, max_preview_columns)
            for row in worksheet.iter_rows(
                min_row=1,
                max_row=row_limit,
                min_col=1,
                max_col=column_limit,
                values_only=True,
            ):
                values = [_json_value(value, max_cell_chars) for value in row]
                while values and values[-1] is None:
                    values.pop()
                if any(value not in (None, "") for value in values):
                    preview_rows.append(values)
            sheets.append({
                "title": worksheet.title,
                "state": worksheet.sheet_state,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "preview_rows": preview_rows,
                "preview_truncated": (
                    (worksheet.max_row or 0) > max_preview_rows
                    or (worksheet.max_column or 0) > max_preview_columns
                ),
            })
    finally:
        workbook.close()

    return {
        "file_name": source.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "sheet_count": len(sheets),
        "sheets": sheets,
        "interpretation": (
            "Schema discovery only. Previewed labels are not validated field mappings; "
            "inspect the complete codebook and source data before joining or modelling."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-preview-rows", type=int, default=40)
    parser.add_argument("--max-preview-columns", type=int, default=24)
    args = parser.parse_args()

    report = inspect_codebook(
        args.input,
        max_preview_rows=args.max_preview_rows,
        max_preview_columns=args.max_preview_columns,
    )
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
