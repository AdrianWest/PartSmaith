# Phase 12.3 working increment

The desktop now exposes Evidence, Conflicts, Component Data, Symbol / Footprint,
and Validation / Release review tabs. Original local text and provenance remain
inspectable. Retained page images show source-region overlays using the recorded
crop, rotation and pixel-to-page affine mapping. Evidence uses virtual rows.

Acquisition controls expose explicit one-based pages/ranges or All Pages, DPI,
forced OCR and recorded OCR languages. Every acquisition has a new identity.
The OpenAI checkbox authorizes deliberate requests from the Evidence tab;
local extraction completes first. Selected evidence IDs and trusted target
paths produce an exact canonical request preview with provider, model, count,
bytes and retention/cost disclosure. Adapter limits remain 1–128 records and
512 KiB. Oversized requests fail without truncation or silent splitting.

Resource Limits records byte/count budgets in the session. Source and evidence
objects remain immutable. Images load by hash on selection; derived image
memory is bounded. Transport writes use bounded copy buffers, archives have
object/count/expanded-byte limits, and log capture stops with an explicit
diagnostic and cancellation request if its configured limit is reached.
The packaged offline `session-index-1.0.schema.json` validates session transport.

Recorded checks before Phase 12.4:

- `phase-12.3-source-results.xml`: **42 passed**, covering session, page selection,
  exact requests, both adapter limits, overlays and real wx evidence controls.
- `phase-12.3-provenance-results.xml`: **101 passed**, covering the existing AI
  contracts/transport and native PDF crop/rotation/DPI/UserUnit fixtures.
- Source imports are selected explicitly in Python 3.12.10.

Session JSON revealed a Decimal/float tolerance mismatch in source-region
validation; the coordinate service now accepts retained Decimal coordinates.
Engineering dimensions and request bytes remain exact.

Installed-wheel checks, final resource/responsiveness verification and full
gate hash closeout remain at Phase 12.10. The combined native regression finding
remains open and is not superseded by these scoped passing checks.
