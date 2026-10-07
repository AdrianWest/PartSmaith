"""Conservative exact order-number mapping from extracted ordering tables."""

import re


def _normalize(text):
    # Typographic hyphens are semantically equivalent; suffixes are retained.
    return (text or "").strip().translate(str.maketrans("−–‑", "---"))


def resolve_package(result, part_number):
    if not part_number.strip():
        raise ValueError("A full manufacturer order number is required.")
    candidates = []
    for record in result["records"]:
        payload = record["payload"]
        if not isinstance(payload, dict) or "rows" not in payload:
            continue
        rows = payload["rows"]
        columns = None
        for row in rows:
            headers = [re.sub(r"\s+", " ", _normalize(c)).lower() for c in row]
            part_columns = [
                i
                for i, h in enumerate(headers)
                if h
                in {
                    "device",
                    "part number",
                    "order number",
                    "ordering code",
                    "ordering number",
                    "型号",
                    "订货型号",
                }
            ]
            package_columns = [
                i
                for i, h in enumerate(headers)
                if h
                in {
                    "package",
                    "package type",
                    "gehäuse",
                    "封装",
                }
            ]
            if len(part_columns) == len(package_columns) == 1:
                columns = part_columns[0], package_columns[0]
                continue
            if columns is None or len(row) <= max(columns):
                continue
            part, package = (_normalize(row[i]) for i in columns)
            if part == _normalize(part_number) and package:
                candidates.append(
                    {"package": package, "evidence_id": record["evidence_id"]}
                )
    packages = sorted({c["package"] for c in candidates})
    status = (
        "RESOLVED"
        if len(packages) == 1
        else ("AMBIGUOUS" if packages else "UNRECOGNIZED")
    )
    return {
        "part_number": part_number,
        "status": status,
        "package": packages[0] if status == "RESOLVED" else None,
        "candidates": candidates,
    }
