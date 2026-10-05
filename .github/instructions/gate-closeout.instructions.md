---
name: Gate completion and hash refresh
description: Refresh and verify all applicable recorded hashes before closing an implementation gate.
applyTo: "**"
---
# Gate completion and hash refresh

Completing or revalidating a gate MUST include a final hash refresh and
verification. Do not report the gate as complete or PASS until this closeout
is finished.

1. Run the required gate checks and finalize the implementation, specification,
   documentation, reports, logs, test results, and generated artifacts.
2. Refresh every recorded input and artifact SHA-256 for the completed gate
   from the exact final bytes. Include hashes stored outside a manifest's
   `sha256` map, such as the current gate's wheel and evidence identities.
3. Find every other active gate manifest that references files changed during
   this gate and refresh its affected hashes too. Shared files include the
   implementation specification, README, CI workflow, packaging configuration,
   source, schemas, migrations, and fixtures. Include all affected manifests
   checked by CI; updating only the newly completed gate is insufficient.
4. Preserve historical evidence and archived manifests under
   `docs/gates/history/`. Record the reason, scope, and previous/new hashes
   for refreshed active manifests. Existing historical test results, wheel
   identities, and golden fixture hashes retain their original scope; changes
   to those artifacts require their applicable validation, not just a new hash.
5. Verify all refreshed manifests and every manifest currently checked by CI.
   If a finalized file changes afterward, refresh its affected hashes and
   verify again. Include the manifest changes with the gate's repository
   changes and report the verification commands and results at closeout.

Use the project's Python 3.12 environment and respect `.gitattributes` so
recorded bytes match a clean Windows or Ubuntu checkout. For committed inputs,
refresh from Git blobs:

```text
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-N-artifacts.json --source git --update
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-N-artifacts.json --source git
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-N-artifacts.json
```

Replace `phase-N-artifacts.json` with each applicable manifest. While preparing
uncommitted changes, use `--source disk --update` on finalized checkout bytes;
`--source git --update` reads HEAD and cannot include uncommitted edits. Verify
against committed blobs once those input changes are committed. The script
updates only the `sha256` map; refresh other current-gate artifact identities
from their actual files separately.

CI currently verifies these manifests; inspect `.github/workflows/ci.yml` for
the current list at every closeout:

```text
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-5-artifacts.json
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-6-artifacts.json
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-8-artifacts.json
```

Investigate unexpected mismatches and rerun affected validation before
accepting changed bytes. A hash refresh records the validated state; it does
not replace a gate check or justify bypassing a failure.
