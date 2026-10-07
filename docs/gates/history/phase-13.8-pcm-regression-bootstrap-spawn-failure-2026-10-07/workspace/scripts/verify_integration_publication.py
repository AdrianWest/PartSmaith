"""@file verify_integration_publication.py
@brief Captures real owned publication, update and fresh rollback evidence.
@details Uses a new explicit disposable managed fixture and OS authentication.
Original source database and project bytes remain unchanged.
"""

import argparse
from hashlib import sha256
from pathlib import Path

from partsmith.integration.planner import Planner, read_project
from partsmith.integration.publication import STRATEGY, Publisher
from partsmith.integration.quiescence import ClosedProject
from partsmith.integration.review import IntegrationReview
from partsmith.integration.sources import resolve_approved_source
from partsmith.integration.staging import Stager
from partsmith.integration.store import IntegrationStore
from partsmith.integration.target import OwnedTarget
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence import connect


def operation(connection, target, output, builds, name, origin=None):
    """@brief Checks, approves and publishes one disposable evidence operation.
    @param connection Owned copied authoritative application database.
    @param target Registered native fixture target.
    @param output Owned evidence directory.
    @param builds Desired approved source builds for forward publication.
    @param name Install, update or rollback evidence operation.
    @param origin Prior manifest for a fresh rollback operation.
    @return Exact publication receipt and staged generation.
    @details Deliberate fixture flag authorizes the real OS approval adapter.
    """
    publisher = Publisher(connection)
    planning = (
        publisher.rollback_plan(target, origin)
        if name == "rollback"
        else Planner(connection).plan(target.current(), target.target, builds)
    )
    stage = Stager(connection).stage(planning, output)
    store = IntegrationStore(connection)
    attempt = store.save_plan(planning.plan, planning.snapshot.document)
    Stager(connection).save(attempt, stage)
    connection.commit()
    decision = IntegrationReview(connection).decide(
        attempt,
        stage,
        "APPROVE",
        "Review disposable native " + name,
        target=target.target,
        root=target.current(),
    )
    result = publisher.publish(
        attempt,
        stage,
        target,
        ClosedProject(target.target["project_id"], True),
        intent="ROLLBACK" if name == "rollback" else "PUBLISH",
        rollback_origin=origin,
    )
    assert result.outcome == "COMMITTED" and result.committed
    assert publisher.publish(
        attempt,
        stage,
        target,
        ClosedProject(target.target["project_id"], True),
    ).reused
    directory = output / name
    directory.mkdir()
    for label, contract in (
        ("plan", planning.plan),
        ("manifest", stage.manifest),
        ("pre-validation", stage.pre),
        ("post-validation", stage.post),
        ("authorization", decision.authorization),
        ("audit", decision.audit),
    ):
        (directory / (label + ".json")).write_bytes(contract.canonical_bytes)
    receipt = parse_json(store.get(result.receipt_hash, "publication_receipt"))
    journal = store.get(receipt["journal_hash"], "integration_journal")
    (directory / "journal.json").write_bytes(journal)
    (directory / "publication.json").write_bytes(canonical_json(receipt))
    (directory / "native-stage.json").write_bytes(
        canonical_json(stage.native_receipt)
    )
    return receipt, stage


def main() -> None:
    """@brief Runs actual complete generation switches on a new owned project.
    @return None.
    @details Requires explicit fixture publication intent, leaves the verified
    current logical link available for later native editor acceptance.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--build", required=True, action="append")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--publish-fixture", required=True, action="store_true"
    )
    args = parser.parse_args()
    assert len(args.build) == 3
    original = args.database.read_bytes()
    source_hash = sha256(original).hexdigest()
    output = args.output.absolute()
    output.mkdir()
    database = output / "application.db"
    database.write_bytes(original)
    project = output / "original"
    project.mkdir()
    (project / "acceptance.kicad_pro").write_bytes(b"{}")
    before = read_project(project)
    connection = connect(database)
    identity = {
        "project_id": "phase13-publication-evidence",
        "library_id": "bft-library",
        "scope": "project-local",
    }
    try:
        sources = [
            resolve_approved_source(connection, b).binding()
            for b in args.build
        ]
        target = OwnedTarget.create(
            connection,
            identity,
            project,
            output / "managed",
            ClosedProject(identity["project_id"], True),
        )
        installed, stage = operation(
            connection, target, output, args.build[:2], "install"
        )
        _, changed = operation(
            connection,
            target,
            output,
            (args.build[2], args.build[1]),
            "update",
        )
        note = target.current() / "latest-user-note.txt"
        note.write_bytes(b"Preserved after fresh rollback\n")
        rolled_back, restored = operation(
            connection, target, output, (), "rollback", stage.manifest.sha256
        )
        assert dict(stage.objects) == dict(restored.objects)
        assert (target.current() / note.name).read_bytes() == note.read_bytes()
        assert read_project(project) == before
        assert sources == [
            resolve_approved_source(connection, b).binding()
            for b in args.build
        ]
        assert (
            connection.execute(
                "SELECT count(*) FROM integration_publications"
            ).fetchone()[0]
            == 3
        )
        assert (
            changed.manifest.data["sources"] != stage.manifest.data["sources"]
        )
    finally:
        connection.close()
    with connect(database) as reopened:
        current = OwnedTarget(reopened, identity)
        assert IntegrationStore(reopened).head(identity).sha256 == (
            restored.manifest.sha256
        )
        assert (
            read_project(current.current())[0][note.name] == note.read_bytes()
        )
        with current.api.directory(current.link, reparse=True) as handle:
            assert (
                list(current.api.identity(handle))
                == (current.metadata["link_identity"])
            )
        current.link.rmdir()
    assert sha256(args.database.read_bytes()).hexdigest() == source_hash
    (output / "receipt.json").write_bytes(
        canonical_json(
            {
                "schema_version": "partsmith-native-publication-evidence-1.0",
                "status": "PASS",
                "platform": "Windows fixed local NTFS",
                "publication_strategy": STRATEGY,
                "fresh_os_authentication": True,
                "publication_count": 3,
                "exact_retries": True,
                "independent_reopen": True,
                "owned_junction_removed_after_evidence": True,
                "first_manifest_hash": stage.manifest.sha256,
                "updated_manifest_hash": changed.manifest.sha256,
                "rollback_manifest_hash": restored.manifest.sha256,
                "installation_receipt": sha256(
                    canonical_json(installed)
                ).hexdigest(),
                "rollback_receipt": sha256(
                    canonical_json(rolled_back)
                ).hexdigest(),
                "mutable_files_preserved": True,
                "original_project_preserved": True,
                "source_bindings_preserved": sources,
                "original_database_before_sha256": source_hash,
                "original_database_after_sha256": source_hash,
            }
        )
    )
    print("PASS: real install, update, fresh rollback and independent reopen")


if __name__ == "__main__":
    main()
