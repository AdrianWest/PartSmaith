"""@package partsmith.integration.bindings
@brief Verifies acyclic cross-object installation contract identities.
@details Hash declarations are resolved against exact immutable documents.
"""

from collections.abc import Mapping
from hashlib import sha256

from partsmith.integration.contracts import (
    REQUIRED_RULES,
    InstallationManifest,
    IntegrationAuditEnvelope,
    IntegrationAuthorizationBinding,
    IntegrationJournal,
    IntegrationPlan,
    IntegrationValidationReport,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy


def verify_files(inventory: list[dict], objects: Mapping[str, bytes]) -> None:
    """@brief Resolves every exact final file hash and length.
    @param inventory Declared complete final file inventory.
    @param objects Exact relative-path-to-byte mapping.
    @return None.
    @details Missing, extra or changed content fails before native checks.
    """
    if set(objects) != {entry["path"] for entry in inventory}:
        raise IntegrationError(FailureCode.TAMPERED_SOURCE)
    if any(not isinstance(blob, bytes) for blob in objects.values()):
        raise IntegrationError(FailureCode.TAMPERED_SOURCE)
    ResourcePolicy().require_sizes([len(blob) for blob in objects.values()])
    for entry in inventory:
        blob = objects[entry["path"]]
        if (
            len(blob) != entry["byte_length"]
            or sha256(blob).hexdigest() != entry["sha256"]
        ):
            raise IntegrationError(FailureCode.TAMPERED_SOURCE)


def _matching(left: dict, right: dict, fields: tuple[str, ...]) -> None:
    """@brief Checks shared deterministic bindings between documents.
    @param left Expected document fields.
    @param right Actual document fields.
    @param fields Required matching field names.
    @return None.
    @details Target and base failures have independent machine categories.
    """
    for field in fields:
        if left[field] != right[field]:
            code = {
                "target": FailureCode.TARGET_CONFLICT,
                "expected_base": FailureCode.STALE_BASE,
            }.get(field, FailureCode.INVALID_CONTRACT)
            raise IntegrationError(code)


def _passing(report: IntegrationValidationReport) -> None:
    """@brief Requires every installation rule to have applicable PASS.
    @param report Exact deterministic validation report.
    @return None.
    @details Declared exclusions cannot bypass mandatory installation checks.
    """
    for result in report.data["results"]:
        if (
            result["status"] != "PASS"
            or result["applicability"] != "APPLICABLE"
        ):
            code = (
                FailureCode.NATIVE_CHECK_FAILED
                if result["rule_id"] == "NATIVE_PARSE"
                else FailureCode.SEMANTIC_CHECK_FAILED
            )
            raise IntegrationError(code)


def verify_contract_bindings(
    plan: IntegrationPlan,
    manifest: InstallationManifest,
    reports: Mapping[str, IntegrationValidationReport],
    post_manifest: IntegrationValidationReport,
    authorization: IntegrationAuthorizationBinding,
    *,
    current_target: dict,
    current_base: dict,
    files: Mapping[str, bytes],
) -> None:
    """@brief Resolves the exact plan/files/checks/manifest/authority DAG.
    @param plan Frozen intended operations and source identities.
    @param manifest Complete final generation document.
    @param reports Pre-manifest reports indexed by exact content hash.
    @param post_manifest Separate completed-manifest verification.
    @param authorization Exact content authorization binding.
    @param current_target Independently observed target identity.
    @param current_base Independently observed current base inventory.
    @param files Exact final aggregate bytes.
    @return None.
    @details This validates bindings; a service must additionally resolve
    approved sources, authenticate a fresh actor and recheck the live target.
    """
    p, m, a = plan.data, manifest.data, authorization.data
    _matching(p, {"target": current_target}, ("target",))
    _matching(p, {"expected_base": current_base}, ("expected_base",))
    _matching(
        p, m, ("target", "expected_base", "sources", "mappings", "versions")
    )
    if m["plan_hash"] != plan.sha256:
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    verify_files(m["files"], files)
    operations = {o["path"]: o for o in p["operations"]}
    base = {f["path"]: f for f in p["expected_base"]["files"]}
    final = {f["path"]: f for f in m["files"]}
    required_paths = {
        mapping[field]
        for mapping in p["mappings"]
        for field in ("symbol_path", "footprint_path", "model_path")
    }
    if not required_paths <= final.keys():
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    source_by_component = {s["component_id"]: s for s in p["sources"]}
    for mapping in p["mappings"]:
        model = next(
            artifact
            for artifact in source_by_component[mapping["component_id"]][
                "artifacts"
            ]
            if artifact["role"] == "model_3d"
        )
        installed = final[mapping["model_path"]]
        if (
            installed["sha256"] != model["sha256"]
            or installed["byte_length"] != model["byte_length"]
        ):
            raise IntegrationError(FailureCode.SEMANTIC_CHECK_FAILED)
    for path, entry in final.items():
        operation = operations.get(path)
        if operation is None:
            if base.get(path) != entry:
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
        elif operation["action"] == "DELETE":
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
    for path, previous in base.items():
        if previous["sha256"] is not None and path not in final:
            if operations.get(path, {}).get("action") != "DELETE":
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
    for path, operation in operations.items():
        if (operation["action"] == "DELETE") == (path in final):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
    expected_reports = {c["report_hash"] for c in m["required_checks"]}
    if set(reports) != expected_reports:
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    for digest, report in reports.items():
        r = report.data
        if (
            digest != report.sha256
            or r["phase"] != "PRE_MANIFEST"
            or r["plan_hash"] != plan.sha256
            or r["comparator_version"] != p["versions"]["comparator"]
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        _matching(
            m, r, ("target", "expected_base", "sources", "mappings", "files")
        )
        _passing(report)
    semantic = next(
        c["report_hash"]
        for c in m["required_checks"]
        if c["rule_id"] == "SEMANTIC_PRESERVATION"
    )
    if m["semantic_validation_hash"] != semantic:
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    post = post_manifest.data
    if (
        post["phase"] != "POST_MANIFEST"
        or post["manifest_hash"] != manifest.sha256
        or post["plan_hash"] != plan.sha256
        or post["comparator_version"] != p["versions"]["comparator"]
    ):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    _matching(
        m, post, ("target", "expected_base", "sources", "mappings", "files")
    )
    _passing(post_manifest)
    _matching(m, a, ("target", "expected_base", "required_checks"))
    if (
        a["plan_hash"] != plan.sha256
        or a["installation_manifest_hash"] != manifest.sha256
        or a["post_manifest_check_hash"] != post_manifest.sha256
    ):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    if tuple(c["rule_id"] for c in a["required_checks"]) != REQUIRED_RULES:
        raise IntegrationError(FailureCode.INVALID_CONTRACT)


def verify_journal_binding(
    journal: IntegrationJournal,
    plan: IntegrationPlan,
    manifest: InstallationManifest,
    authorization: IntegrationAuthorizationBinding,
) -> None:
    """@brief Resolves journal intent against exact reviewed object identities.
    @param journal Operational recoverable intent.
    @param plan Frozen integration plan.
    @param manifest Intended new generation.
    @param authorization Previously verified exact authorization binding.
    @return None.
    @details Resolution does not perform a filesystem publication or recovery.
    """
    j, a = journal.data, authorization.data
    p, m = plan.data, manifest.data
    _matching(
        p, m, ("target", "expected_base", "sources", "mappings", "versions")
    )
    _matching(p, a, ("target", "expected_base"))
    _matching(p, j, ("target", "expected_base"))
    _matching(m, a, ("required_checks",))
    _matching(a, j, ("required_checks", "post_manifest_check_hash"))
    if (
        j["plan_hash"] != plan.sha256
        or m["plan_hash"] != plan.sha256
        or a["plan_hash"] != plan.sha256
        or a["installation_manifest_hash"] != manifest.sha256
        or j["new_manifest_hash"] != manifest.sha256
        or j["authorization_hash"] != authorization.sha256
    ):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)


def verify_audit_binding(
    audit: IntegrationAuditEnvelope,
    plan: IntegrationPlan,
    manifest: InstallationManifest,
    authorization: IntegrationAuthorizationBinding,
    post_manifest: IntegrationValidationReport,
    *,
    attempt_id: str,
) -> None:
    """@brief Resolves approval audit references to its exact verified graph.
    @param audit Immutable approval decision and operational identity.
    @param plan Previously verified frozen plan.
    @param manifest Previously verified intended installation manifest.
    @param authorization Previously verified exact authorization binding.
    @param post_manifest Previously verified completed-manifest report.
    @param attempt_id Independently established current attempt identity.
    @return None.
    @details Binding does not authenticate imported actor text or grant a new
    publication permission; authentication remains the service's obligation.
    """
    decision = audit.data
    a, m = authorization.data, manifest.data
    p, post = plan.data, post_manifest.data
    _matching(
        p, m, ("target", "expected_base", "sources", "mappings", "versions")
    )
    _matching(m, a, ("target", "expected_base", "required_checks"))
    _matching(
        m, post, ("target", "expected_base", "sources", "mappings", "files")
    )
    _matching(m, decision, ("target",))
    expected = {
        "plan_hash": plan.sha256,
        "manifest_hash": manifest.sha256,
        "authorization_hash": authorization.sha256,
        "check_hashes": sorted(
            {c["report_hash"] for c in m["required_checks"]}
            | {post_manifest.sha256}
        ),
    }
    if (
        decision["attempt_id"] != attempt_id
        or decision["decision"] != "APPROVE"
        or decision["references"] != expected
        or m["plan_hash"] != plan.sha256
        or a["plan_hash"] != plan.sha256
        or a["installation_manifest_hash"] != manifest.sha256
        or a["post_manifest_check_hash"] != post_manifest.sha256
        or post["manifest_hash"] != manifest.sha256
        or post["plan_hash"] != plan.sha256
        or post["phase"] != "POST_MANIFEST"
        or post["comparator_version"] != p["versions"]["comparator"]
    ):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    _passing(post_manifest)
