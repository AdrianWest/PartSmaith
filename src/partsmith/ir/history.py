"""Immutable revision storage protocol and IR 1.2 transition validation."""

from hashlib import sha256
from typing import Protocol

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.ir.errors import IRValidationError, Issue
from partsmith.ir.revised import resolve_pointer
from partsmith.ir.schema import fragment_valid


class RevisionStore(Protocol):
    def get_revision(self, revision_id: str) -> dict: ...

    def get_inventory(self, digest: str) -> dict: ...


class MemoryRevisionStore:
    """Detached snapshot store for imports/tests; no approval is fabricated."""

    def __init__(self, revisions=(), inventories=()):
        from partsmith.ir.model import ComponentIR

        self._revisions = {}
        self._inventories = {}
        for value in revisions:
            ir = (
                value if isinstance(value, ComponentIR) else ComponentIR(value)
            )
            key = ir.data["revision"]["id"]
            if key in self._revisions:
                raise ValueError("Duplicate revision identity")
            self._revisions[key] = ir.canonical_bytes
        for inventory in inventories:
            if not fragment_valid(inventory, {"$ref": "#/$defs/inventory"}):
                raise ValueError("Invalid acquisition inventory")
            blob = canonical_json(inventory)
            self._inventories[sha256(blob).hexdigest()] = blob

    def get_revision(self, revision_id):
        return parse_json(self._revisions[revision_id])

    def get_inventory(self, digest):
        return parse_json(self._inventories[digest])


def as_data(value):
    from partsmith.ir.model import ComponentIR, normalize_ir

    return (
        value.data if isinstance(value, ComponentIR) else normalize_ir(value)
    )


def validate_revision_transition(previous, current):
    """Validate transitions with append-only historical records."""
    try:
        before, after = as_data(previous), as_data(current)
    except IRValidationError as error:
        return error.issues
    issues = []

    def add(path, message):
        issues.append(Issue(path, "IR_TRANSITION", message))

    if before["schema_version"] != "1.2" or after["schema_version"] != "1.2":
        add("/schema_version", "Transitions require IR 1.2 snapshots")
        return tuple(issues)
    old, new = before["revision"], after["revision"]
    if new["parent_id"] != old["id"] or new["id"] == old["id"]:
        add("/revision/parent_id", "Expected a new child revision")
    if before["identity"]["component_id"] != after["identity"]["component_id"]:
        add("/identity/component_id", "Revision belongs to another component")
    for domain in ("evidence", "standards", "overrides", "resolutions"):
        indexed = {r["id"]: r for r in after[domain]}
        for record in before[domain]:
            if indexed.get(record["id"]) != record:
                add("/" + domain, "Historical record changed or disappeared")
    docs = {r["id"]: r for r in after["source"]["documents"]}
    for record in before["source"]["documents"]:
        if docs.get(record["id"]) != record:
            add(
                "/source/documents", "Historical source changed or disappeared"
            )
    for field in ("target_rebindings", "evidence_exclusions"):
        if new[field][: len(old[field])] != old[field]:
            add("/revision/" + field, "Review history must remain append-only")
    old_overrides = {r["id"]: r for r in before["overrides"]}
    new_overrides = {r["id"]: r for r in after["overrides"]}
    new_resolutions = {r["id"]: r for r in after["resolutions"]}
    added_decisions = [
        new_resolutions[key]
        for key in new["active_resolution_ids"]
        if key not in old["active_resolution_ids"] and key in new_resolutions
    ]
    for key in set(old["active_override_ids"]) - set(
        new["active_override_ids"]
    ):
        replacement = any(
            new_overrides.get(i, {}).get("supersedes_override_id") == key
            and new_overrides[i]["path"] == old_overrides[key]["path"]
            for i in new["active_override_ids"]
        )
        removed = any(
            r["decision"] == "remove_override"
            and r["override_id"] is None
            and r["target_path"] == old_overrides[key]["path"]
            for r in added_decisions
        )
        if not replacement and not removed:
            add(
                "/revision/active_override_ids",
                "Override removal needs an explicit decision",
            )
    for key in set(old["active_resolution_ids"]) - set(
        new["active_resolution_ids"]
    ):
        if not any(
            r["supersedes_resolution_id"] == key for r in added_decisions
        ):
            add(
                "/revision/active_resolution_ids",
                "Resolution replacement must identify its predecessor",
            )
    # Current terminal numbers are stable identities for a reorder. Changed
    # numbering in place is a separately typed pin override, not a rebind.
    bindings = new["target_rebindings"][len(old["target_rebindings"]) :]
    for binding in bindings:
        try:
            if binding["base_revision_id"] != old["id"]:
                raise ValueError
            if binding["approval_state"] != "APPROVED":
                continue
            a = resolve_pointer(before, binding["old_path"])
            b = (
                None
                if binding["new_path"] is None
                else resolve_pointer(after, binding["new_path"])
            )
            if not isinstance(a, dict) or "number" not in a:
                raise ValueError
            if b is None:
                if any(p["number"] == a["number"] for p in after["pins"]):
                    raise ValueError
            elif not isinstance(b, dict) or b.get("number") != a["number"]:
                raise ValueError
        except (KeyError, IndexError, ValueError, TypeError):
            add(
                "/revision/target_rebindings",
                "Rebinding must preserve or explicitly retire a terminal",
            )
    old_positions = {p["number"]: i for i, p in enumerate(before["pins"])}
    new_positions = {p["number"]: i for i, p in enumerate(after["pins"])}
    if [p["number"] for p in before["pins"]] != [
        p["number"] for p in after["pins"]
    ]:
        for number, i in old_positions.items():
            j = new_positions.get(number)
            if j == i:
                continue
            # Explicit in-place number override does not reorder a terminal.
            if j is None and any(
                new_overrides.get(k, {}).get("path") == f"/pins/{i}/number"
                for k in new["active_override_ids"]
            ):
                continue
            expected = None if j is None else f"/pins/{j}"
            if not any(
                b["old_path"] == f"/pins/{i}"
                and b["new_path"] == expected
                and b["approval_state"] == "APPROVED"
                for b in bindings
            ):
                add(
                    "/revision/target_rebindings",
                    "Changed topology requires explicit target rebindings",
                )
    return tuple(sorted(set(issues)))


def revision_chain(data, store):
    """Load and validate ancestry, returning oldest first and stable issues."""
    issues = []
    chain = [data]
    seen = {data["revision"]["id"]}
    if store is None:
        return chain, [
            Issue(
                "/revision",
                "IR_HISTORY",
                "Generation requires a revision store",
            )
        ]
    try:
        stored = as_data(store.get_revision(data["revision"]["id"]))
        if stored != data:
            issues.append(
                Issue(
                    "/revision/id",
                    "IR_HISTORY",
                    "Stored revision identity cannot be rewritten",
                )
            )
    except KeyError:
        pass  # A new candidate may not have been persisted yet.
    except (ValueError, TypeError, AttributeError):
        issues.append(
            Issue("/revision", "IR_HISTORY", "Invalid revision store")
        )
    while chain[-1]["revision"]["parent_id"] is not None:
        key = chain[-1]["revision"]["parent_id"]
        if key in seen:
            issues.append(
                Issue(
                    "/revision/parent_id",
                    "IR_HISTORY",
                    "Cyclic revision ancestry",
                )
            )
            break
        seen.add(key)
        try:
            parent = as_data(store.get_revision(key))
            if (
                parent["revision"]["id"] != key
                or parent["schema_version"] != "1.2"
            ):
                raise ValueError
            issues.extend(validate_revision_transition(parent, chain[-1]))
            chain.append(parent)
        except (KeyError, ValueError, TypeError, AttributeError):
            issues.append(
                Issue(
                    "/revision/parent_id",
                    "IR_HISTORY",
                    "Missing or invalid parent snapshot",
                )
            )
            break
    return list(reversed(chain)), issues


def review_issues(data, store, chain):
    issues = []

    def add(path, code, message):
        issues.append(Issue(path, code, message))

    known = {r["revision"]["id"]: r for r in chain}
    review = data["revision"]["evidence_review"]
    if review is None or review["approval_state"] != "APPROVED":
        add(
            "/revision/evidence_review",
            "IR_REVIEW",
            "Generation requires an approved evidence review",
        )
    else:
        try:
            inventory = store.get_inventory(review["inventory_sha256"])
            if not fragment_valid(inventory, {"$ref": "#/$defs/inventory"}):
                raise ValueError
            if (
                sha256(canonical_json(inventory)).hexdigest()
                != review["inventory_sha256"]
            ):
                raise ValueError
            ids = {r["id"] for r in data["evidence"]}
            hashes = {r["sha256"] for r in data["source"]["documents"]}
            if (
                set(inventory["evidence_ids"]) != ids
                or set(review["reviewed_evidence_ids"]) != ids
                or set(inventory["source_hashes"]) != hashes
            ):
                raise ValueError
        except (KeyError, ValueError, TypeError, AttributeError):
            add(
                "/revision/evidence_review",
                "IR_INVENTORY",
                "Acquisition inventory and review must match retained inputs",
            )
    exclusions = {
        r["evidence_id"]: r
        for r in data["revision"]["evidence_exclusions"]
        if r["approval_state"] == "APPROVED"
    }
    for i, evidence in enumerate(data["evidence"]):
        base = known.get(evidence["acquisition_revision_id"])
        if base is None or evidence not in base["evidence"]:
            add(
                f"/evidence/{i}/acquisition_revision_id",
                "IR_HISTORY",
                "Acquisition snapshot must retain the exact evidence",
            )
        if (
            not evidence["candidate_targets"]
            and evidence["id"] not in exclusions
        ):
            add(
                f"/evidence/{i}/candidate_targets",
                "IR_REVIEW",
                "Unassigned evidence needs a reviewed disposition",
            )
    for domain, field in (
        ("overrides", "path"),
        ("resolutions", "target_path"),
    ):
        for i, record in enumerate(data[domain]):
            base = known.get(record["base_revision_id"])
            try:
                if base is None:
                    raise ValueError
                previous = resolve_pointer(base, record[field])
                if (
                    domain == "overrides"
                    and previous != record["previous_value"]
                ):
                    raise ValueError
            except (KeyError, IndexError, ValueError, TypeError):
                add(
                    f"/{domain}/{i}/base_revision_id",
                    "IR_HISTORY",
                    "Decision base and previous value must resolve",
                )
    return issues
