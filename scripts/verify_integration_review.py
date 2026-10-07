"""@file verify_integration_review.py
@brief Records exact review decisions in an explicit disposable fixture copy.
@details Requires an explicit fixture-approval flag, fresh OS authentication,
real native staging and a new output directory. Publishes no project files.
"""

import argparse
from hashlib import sha256
from pathlib import Path

from partsmith.integration.planner import Planner
from partsmith.integration.review import IntegrationReview
from partsmith.integration.sources import resolve_approved_source
from partsmith.integration.staging import Stager
from partsmith.integration.store import IntegrationStore
from partsmith.ir.canonical import canonical_json
from partsmith.persistence import connect


def main() -> None:
    """@brief Captures an exact decision and independent reopen receipt.
    @return None.
    @details Copies the supplied fixture database, preserving the original and
    every source approval. Exact retry retains one decision and no publication.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--build", required=True, action="append")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--approve-fixture", required=True, action="store_true"
    )
    args = parser.parse_args()
    original = args.database.read_bytes()
    before = sha256(original).hexdigest()
    output = args.output.absolute()
    output.mkdir()
    copied = output / "application.db"
    copied.write_bytes(original)
    root = output / "project"
    root.mkdir()
    target = {
        "project_id": "phase13-review-evidence",
        "library_id": "bft-library",
        "scope": "project-local",
    }
    connection = connect(copied)
    try:
        planning = Planner(connection).plan(root, target, args.build)
        stage = Stager(connection).stage(planning, output)
        attempt = IntegrationStore(connection).save_plan(
            planning.plan, planning.snapshot.document
        )
        Stager(connection).save(attempt, stage)
        connection.commit()
        review = IntegrationReview(connection)
        view = review.inspect(attempt, stage, target=target, root=root)
        reason = (
            "Deliberate review of disposable native fixture; no publication"
        )
        decision = review.decide(
            attempt, stage, "APPROVE", reason, target=target, root=root
        )
        retry = review.decide(
            attempt, stage, "APPROVE", reason, target=target, root=root
        )
        assert retry.reused and retry.audit == decision.audit
        assert (
            connection.execute(
                "SELECT count(*) FROM integration_decisions"
            ).fetchone()[0]
            == 1
        )
        after_sources = [
            resolve_approved_source(connection, build).binding()
            for build in args.build
        ]
        assert (
            sorted(after_sources, key=lambda s: s["component_id"])
            == (planning.plan.data["sources"])
        )
    finally:
        connection.close()
    reopened = connect(copied)
    try:
        assert IntegrationReview(reopened).resolve(attempt, stage).audit == (
            decision.audit
        )
    finally:
        reopened.close()
    assert sha256(args.database.read_bytes()).hexdigest() == before
    assert not (root / "BFT_Symbols.kicad_sym").exists()
    for name, contract in (
        ("plan", planning.plan),
        ("manifest", stage.manifest),
        ("pre-validation", stage.pre),
        ("post-validation", stage.post),
        ("authorization", decision.authorization),
        ("audit", decision.audit),
    ):
        (output / (name + ".json")).write_bytes(contract.canonical_bytes)
    (output / "review-view.json").write_bytes(canonical_json(view))
    (output / "receipt.json").write_bytes(
        canonical_json(
            {
                "schema_version": "partsmith-native-review-evidence-1.0",
                "status": "PASS",
                "attempt_id": attempt,
                "authorization_hash": decision.authorization.sha256,
                "audit_hash": decision.audit.sha256,
                "decision_count": 1,
                "fresh_os_authentication": True,
                "exact_retry": True,
                "independent_reopen": True,
                "target_published": False,
                "source_bindings_preserved": after_sources,
                "original_database_before_sha256": before,
                "original_database_after_sha256": before,
            }
        )
    )
    print(f"PASS: fresh exact decision {decision.audit.sha256}; one receipt")


if __name__ == "__main__":
    main()
