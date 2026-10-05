# Phase 11 — AI provider adapter

**Gate: PASS**, verified 2026-10-04 against specification v0.9.6.
Prerequisite: [Phase 10 PASS](phase-10.md).
Scope: local Windows AMD64, Python 3.12.10, native KiCad 10.0.6,
OpenAI Responses API with `gpt-4.1-mini-2025-04-14`.
No remote CI, Linux/macOS, or additional live provider is claimed.

| Phase work item | Implementation and evidence |
| --- | --- |
| Normalized provider interface | Immutable `AIRequest`/`AIResult` and `AIProvider.analyze` protocol. A closed `ai-result-1.0` schema normalizes provider output before it enters the Evidence workflow. Narrow tasks explicitly select trusted IR targets or Evidence-only package/translation/explanation candidates. |
| User API-key configuration | Customer keys come from the existing native OS credential store or `OPENAI_API_KEY`. Credentials authenticate only to the fixed OpenAI HTTPS endpoint, without redirects, proxy forwarding, tools, or arbitrary endpoints. The production app never loads repository `.env`. |
| Provider/model metadata | The [packaged adapter manifest](../../src/partsmith/ai/adapter-manifest-1.0.json) pins provider, Responses v1 API, model snapshot, adapter/prompt/result versions, capabilities, authentication and dated official references. Results retain request ID, timestamp, input/output hashes, output-affecting version bindings and separate operational settings. |
| Extraction/interpretation tasks | Selected Phase 10 Evidence text, local OCR and original-page provenance feed narrow requests. Typed candidate values must match the trusted IR 1.2 target registry. Package candidates retain the full required order number. Translations retain originals and separate provider/model/timestamp metadata. Image-only drawing interpretation is not claimed. |
| Evidence/IR workflow boundary | Candidate bundles retain source Evidence, normalized results and new IR 1.2-compatible unreviewed Evidence. No Component IR, engineering artifact, approval or validation state is produced or applied by the adapter. Existing deterministic validation rejects inferred/unreviewed engineering inputs. Phase 12 application/review remains required. |
| Prompt-injection/security | Document/OCR/translation text is user data, separate from trusted instructions. No tools or executable output path exists. Tests reject schema/authority fields, fabricated references and quotations, unrequested targets, wrong value types, malformed JSON, secret echoes, model mismatches and unsupported output items. HTTPS errors discard provider bodies. |
| Conflict and ambiguity handling | Source-linked issues remain visible; conflicting values for the same target are independently detected and remain unresolved regardless of confidence. Missing full order numbers do not become inferred packages. |

The GUI defaults to local extraction, visibly discloses OpenAI/model, selected
text/provenance, local OCR, billing and retention before its optional AI path.
It retains unreviewed candidates in job state, reports unresolved issues and
the remaining Phase 12 boundary without false component-build success.
The CLI writes a review-only candidate bundle through `ai analyze`.

`store=false` disables response application-state storage for this request;
provider retention and abuse monitoring remain subject to OpenAI account
terms. This is not a zero-retention guarantee. User API charges are paid
directly to OpenAI. See the dated official references in the adapter manifest:
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[model snapshot](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[data controls](https://developers.openai.com/api/docs/guides/your-data).

The development live gate explicitly loads `BFT_TOKEN` from repository `.env`
under AI-005. It exercises the real LM2575 ordering table, a missing order
number, and a separately identified synthetic prompt-injection augmentation.
Its retained JSON results are local generated outputs under
`.tools/phase11/live/`; no testing credential is retained in those outputs or
in committed test fixtures. Missing credentials fail clearly without a skip.
The offline contract and HTTPS suite uses dummy credentials and no network.

Requests and responses have bounded size, time, retry count and candidate
counts. Only transport timeouts, rate limits and temporary service/network
failures retry. Schema, reference, model, refusal and value failures do not.
Cancellation discards responses and closes the HTTPS connection; any blocking
OS transport thread is daemonized and bounded by its socket timeout. Local
mode makes no external request and requires no provider credential.

`RecordedProvider` reuses an immutable validated result offline, with exact
request, output and adapter/cache bindings. It preserves the original provider
request ID/timestamp, and never claims a fresh inference. It cannot make the
candidates reviewed or turn them into artifacts.

Verification:

- Final full source, native wx/KiCad and credential restart
  suite: **638 passed**, zero failures/errors/skips. This includes
  all offline/native checks. The separately verified **3 live tests** pass.
- Installed-wheel adapter, HTTPS/security, CLI, processing isolation, GUI,
  native KiCad and credential checks: **108 passed**, zero
  failures/errors/skips. Packaged adapter-manifest identity is verified.
- Lint, formatting and dependency consistency: PASS.
- [Source results](phase-11-source-results.xml),
  [installed-wheel results](phase-11-wheel-results.xml), and
  [live-provider cases extracted from the final provider run](phase-11-live-results.xml).
  The [combined provider/security run](phase-11-provider-results.xml) has
  **69 passes**, including the live cases.
- Exact code, test, fixture, document and wheel hashes are recorded in
  [the artifact manifest](phase-11-artifacts.json).

Development attempts rejected schema constraints, malformed citations or
unresolved references instead of accepting invalid candidates. The final
live gate uses exact source-anchor/Evidence-ID constraints and distinguishes
consulted source records from candidate references. Earlier local attempt
results are labeled and archived under `docs/gates/history/`; they are not
the final acceptance evidence.

Reproduce with the project-local runtime:

```powershell
.tools/python/python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir .tools/phase11/dist
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase11/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys; sys.path[:0]=['src','.']; import pytest; raise SystemExit(pytest.main(['tests','scripts/verify_gui.py','-q','--junitxml=docs/gates/phase-11-source-results.xml']))"
.tools/python/python.exe -c "import sys; sys.path.insert(0,'.'); import partsmith.ai; assert 'site-packages' in partsmith.ai.__file__; import pytest; raise SystemExit(pytest.main(['tests/test_ai.py','tests/test_ai_transport.py','tests/test_gui.py','tests/test_cli.py','tests/test_extraction_isolation.py','tests/test_kicad_runtime.py','scripts/verify_gui.py','-q','--junitxml=docs/gates/phase-11-wheel-results.xml']))"
.tools/python/python.exe -c "import sys; sys.path[:0]=['src','.']; import pytest; raise SystemExit(pytest.main(['scripts/verify_ai_live.py','-q','--junitxml=docs/gates/phase-11-live-results.xml']))"
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
```

Finish wheel installation before regression suites start. Native wx, KiCad and
credential-store checks require a normal desktop shell. Earlier manifests are
archived before refreshing shared CLI/GUI/documentation hashes; historical
gate tests and wheel identities retain their original scope.
