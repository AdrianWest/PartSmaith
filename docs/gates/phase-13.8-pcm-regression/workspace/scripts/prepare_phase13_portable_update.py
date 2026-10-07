"""@file prepare_phase13_portable_update.py
@brief Appends a compatible approved synthetic update for acceptance.
@details Preserves the original source database and every prior approval byte.
Creates a separate data-only archive without installation execution records.
"""

import argparse
import sys
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from partsmith.gui.session import Session
from partsmith.integration.sources import resolve_approved_source
from partsmith.ir.canonical import canonical_json
from partsmith.persistence import connect


def main():
    """@brief Generates and approves one explicit compatible child revision.
    @return None.
    @details Refuses existing output and never edits historical source rows.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--parent-build", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from phase13_support import create_release

    before = sha256(args.database.read_bytes()).hexdigest()
    args.output.mkdir()
    session = Session(args.output / "sessions")
    with closing(connect(args.database)) as source:
        with closing(connect(session.database)) as destination:
            source.backup(destination)
            destination.execute(
                "CREATE TABLE desktop_session "
                "(id INTEGER PRIMARY KEY,data BLOB)"
            )
            destination.execute(
                "INSERT INTO desktop_session VALUES (1,?)",
                (canonical_json(session.state),),
            )
            parent = resolve_approved_source(destination, args.parent_build)
            updated = create_release(
                destination, parent.component_id, parent.revision_id, True
            )
            destination.commit()
            binding = resolve_approved_source(
                destination, updated.build_id
            ).binding()
            assert (
                resolve_approved_source(
                    destination, args.parent_build
                ).binding()
                == parent.binding()
            )
    archive = args.output / "approved-portable-components.partsmith"
    session.save(archive)
    assert sha256(args.database.read_bytes()).hexdigest() == before
    (args.output / "receipt.json").write_bytes(
        canonical_json(
            {
                "new_build": updated.build_id,
                "source_binding": binding,
                "parent_build": args.parent_build,
                "original_database_before_sha256": before,
                "original_database_after_sha256": before,
                "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
                "data_only": True,
            }
        )
    )
    print(updated.build_id)


if __name__ == "__main__":
    main()
