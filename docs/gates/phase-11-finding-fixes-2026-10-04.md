# Phase 11 review findings 1 and 2 — resolved

The first two findings in [the independent review](phase-10-11-review-2026-10-04.md)
are resolved. The Phase 10 native parser finding remains deferred at the user's
request. This record verifies the two corrections and does not declare all phase
gates passed or waive the remaining Phase 10 issue.

Package candidates now require an exact supporting source quotation containing
the full order number. Matching preserves suffixes, rejects partial matches,
and allows the typographic hyphens used by manufacturer ordering tables. If the
anchor is absent, the candidate remains UNKNOWN with a source-linked ambiguity;
existing conflict status remains unresolved. Re-normalizing the result does not
duplicate the issue. A package name or unrelated ordering entry alone cannot
support an INFERRED package for the requested part.

Request and result snapshots, normalized payloads, CLI input and candidate bundle
serialization now preserve exact decimal tokens. Provider revalidation checks
that the reconstructed request has exactly the original input hash before reading
credentials or transmitting data. Evidence creation, serialized bundle round trips
and offline replay retain the same bindings. CLI and live-test outputs use the
project's canonical JSON serializer rather than converting decimals to floats or
strings. The adapter and prompt versions are **1.1**, separating the corrected
behavior from prior cached results; the result schema remains `ai-result-1.0`.

Verification on local Windows:

- **121 targeted source/native tests passed**, including both original review
  probes, new missing/prefix/suffix/quote tests, exact decimal transport and replay,
  CLI serialization, HTTPS/security, GUI, credential and KiCad checks.
- **121 installed-wheel tests passed** against the rebuilt and reinstalled wheel.
- **3 live OpenAI cases passed**: grounded real order number, missing order number,
  and synthetic prompt injection. The real-order test now requires an INFERRED
  candidate, so UNKNOWN output cannot satisfy it.
- Lint, formatting, dependency consistency, whitespace and credential export
  checks passed. Current package contents match the rebuilt wheel.

The [correction manifest](phase-11-finding-fixes-2026-10-04.json) binds the changed
code, regression tests, results, report and wheel. Earlier gate manifests and the
review's failing results are retained as historical evidence, rather than relabeled
as tests of the corrected code. The original Phase 10 crash remains recorded.
No Phase 10 extraction implementation or parser dependency was changed, and its
full corpus suite was not rerun for these corrections.

The targeted suite includes
[the original review probes](../../scripts/verify_phase11_review.py) and the
regressions in [test_ai.py](../../tests/test_ai.py). Fresh live outputs are retained
separately under `.tools/phase11-fixes/live/` so the earlier live-output identities
are preserved. The wheel is a local generated artifact under
`.tools/phase11-fixes/dist/`.
