from openpyxl import Workbook

from scripts.inspect_ubc_codebook import inspect_codebook


def test_inspect_codebook_reports_sheets_and_bounded_preview(tmp_path):
    path = tmp_path / "READ.ME.xlsx"
    workbook = Workbook()
    first = workbook.active
    first.title = "Data dictionary"
    first.append(["File", "Field", "Definition"])
    first.append(["Search.Efficiency.csv", "s1", "First searcher detection result"])
    second = workbook.create_sheet("Study design")
    second.append(["Season", "Survey days"])
    second.append(["Fall", 45])
    workbook.save(path)
    workbook.close()

    report = inspect_codebook(
        path,
        max_preview_rows=1,
        max_preview_columns=2,
    )

    assert report["file_name"] == "READ.ME.xlsx"
    assert report["bytes"] == path.stat().st_size
    assert len(report["sha256"]) == 64
    assert report["sheet_count"] == 2
    assert report["sheets"][0]["title"] == "Data dictionary"
    assert report["sheets"][0]["preview_rows"] == [["File", "Field"]]
    assert report["sheets"][0]["preview_truncated"] is True
    assert report["sheets"][1]["preview_rows"] == [["Season", "Survey days"]]


def test_inspect_codebook_rejects_invalid_preview_limits(tmp_path):
    path = tmp_path / "empty.xlsx"
    workbook = Workbook()
    workbook.save(path)
    workbook.close()

    try:
        inspect_codebook(path, max_preview_rows=0)
    except ValueError as exc:
        assert "Preview limits" in str(exc)
    else:
        raise AssertionError("invalid preview limits should be rejected")
