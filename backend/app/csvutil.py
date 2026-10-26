import csv
import io

from fastapi.responses import StreamingResponse


def _safe(v) -> str:
    s = "" if v is None else str(v)
    # Neutralise spreadsheet formula injection (=, +, -, @, tab, CR at start of a cell)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def csv_response(filename: str, headers: list[str], rows: list[list]) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([_safe(c) for c in r])
    data = "\ufeff" + buf.getvalue()  # BOM so Excel reads UTF-8 accents correctly
    return StreamingResponse(iter([data]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
