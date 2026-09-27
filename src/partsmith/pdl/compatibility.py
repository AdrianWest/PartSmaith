"""Deterministic Component IR to PDL compatibility checks."""

from partsmith.ir.errors import Issue


def ir_pdl_issues(ir: dict, pdl: dict) -> tuple[Issue, ...]:
    """Return topology and identity mismatches between validated records."""
    issues = []

    def add(path: str, message: str) -> None:
        issues.append(Issue(path, "PDL_IR_MISMATCH", message))

    if ir["package"]["family"] != pdl["identity"]["family"]:
        add("/package/family", "Package families disagree")
    if ir["package"]["variant"] != pdl["identity"]["variant"]:
        add("/package/variant", "Package variants disagree")
    if ir["package"]["pin_count"] != pdl["identity"]["pin_count"]:
        add("/package/pin_count", "Pin counts disagree")

    expected = {item["number"]: item for item in pdl["topology"]["terminals"]}
    actual_index = {
        pin["number"]: index for index, pin in enumerate(ir["pins"])
    }
    if set(actual_index) != set(expected):
        add("/pins", "Terminal numbers disagree")
    for number in sorted(set(actual_index) & set(expected)):
        index = actual_index[number]
        pin = ir["pins"][index]["physical"]
        terminal = expected[number]
        if pin["topology_side"] != terminal["side"]:
            add(
                f"/pins/{index}/physical/topology_side",
                "Terminal sides disagree",
            )
        if pin["topology_index"] != terminal["topology_index"]:
            add(
                f"/pins/{index}/physical/topology_index",
                "Terminal topology indexes disagree",
            )
    return tuple(sorted(set(issues)))
