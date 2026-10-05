# Phase 10 native parser correction — 2026-10-04

**Gate: PASS for the local Windows AMD64 runtime described here.** Finding 3 in
[the independent review](phase-10-11-review-2026-10-04.md) is addressed by replacing
the MuPDF reading/rendering path, with three consecutive combined wheel passes.
Remote CI and other operating systems were not executed for this report.

Native text, graphics, images and tables now use **pdfplumber 0.11.10 /
pdfminer.six 20260107**. Rendering uses **PDFium through pypdfium2 5.14.0**;
PNG/grid processing uses Pillow, and local Tesseract remains responsible for OCR.
Production extraction does not import MuPDF, and the wheel does not depend on it.
PyMuPDF 1.28.2 is retained only as a development fixture tool. The wheel and
requirements pin the production parsers. PDFium calls are serialized within each
process, native handles are explicitly closed, and PNGs retain physical DPI.

The native content adapter reads an in-memory clone of the selected page's
content and resources. It removes display rotation and unrelated annotation/link
references on that clone. This avoids malformed named destinations in otherwise
readable manufacturer PDFs. Original input bytes, hash, page numbering, geometry,
and rendered assets retain their original provenance. UserUnit and shifted
MediaBox/CropBox coordinates are mapped back to physical original-page points.
Grid snapping can place a border slightly outside a page; Evidence retains its
visible intersection, with the original detector extent in supporting records.

Text-containing graphics envelopes preserve open outer parameter and unit columns.
The Infineon regression checks all five columns, merged-cell nulls, units and the
distinct drain-current values **252, 175, 37, 748** in their separate rows. Native
ordering/electrical table oracles, exact package matching, multilingual native and
scanned OCR, diagram/image provenance and coordinate overlays all pass. A test
deliberately makes the retired MuPDF detector fail if called. Eight new table
coordinate cases cover every orthogonal rotation, shifted crop/media boxes and
UserUnit 1/2. Parser errors fail explicitly instead of silently losing tables.

Verification:

- **662 source/native cases passed**, including the original Phase 11
  review probes and real desktop/native integration.
- **Three combined installed-wheel runs passed 194 cases each** with
  zero failures, errors, skips or unexpected parser terminations. Each covers extraction,
  isolation, adapter/HTTPS, CLI, GUI, credentials and native KiCad checks together.
- Each corpus run exercises all **24 supplied PDFs and 279 selected pages** from
  4,102 original pages. The existing sampling policy and input hashes are unchanged:
  every page through 32 pages, first/middle/last for larger documents. The three
  final wheel runs therefore cover **837 selected-page extractions** plus fixtures.
- **79 extraction/isolation cases passed** as part of the complete source suite,
  including an import-guarded fresh-process check proving that the production
  reader and renderer operate without loading MuPDF. The extraction XML is a
  subset of that actual full-source JUnit report, not an independent rerun.
- Ruff, formatting, dependency consistency and whitespace checks passed. All
  **92 installed package files** match the final wheel byte for byte. Mandatory
  Phase 5/6/8 input-hash checks pass after preserving prior manifests and refreshing
  shared inputs; historical wheel/test identities remain identified as historical.

The [manifest](phase-10-parser-fix-2026-10-04.json) binds code, constraints, corpus, native binaries,
wheel, reports and raw output. Final wheel reports are
[round 1](phase-10-parser-fix-2026-10-04-wheel-1.xml), [round 2](phase-10-parser-fix-2026-10-04-wheel-2.xml), and
[round 3](phase-10-parser-fix-2026-10-04-wheel-3.xml). The
[source report](phase-10-parser-fix-2026-10-04-source-results.xml) records the complete source gate.

Earlier failures are preserved. An upgrade-only implementation passed two combined
wheel runs, then crashed in the third with exit code **3221225477** and no complete
JUnit report. It is rejected, not treated as acceptance. Its
[raw native failure](history/phase-10-parser-upgrade-2026-10-04-round-3.stderr.txt)
and [failed gate manifest](history/phase-10-parser-upgrade-2026-10-04-manifest.json)
are retained along with the original 1.26.7 review crash. The first alternate-parser
development suite had 660 passes and a Bourns out-of-page border failure; its
[report](history/phase-10-pure-table-initial-source-results-2026-10-04.xml) remains
historical. Separate development probes exposed the malformed hyperlink case.
Replacing only tables still allowed a native graphics crash while reading LM2575.
Its [raw failure](history/phase-10-parser-upgrade-graphics-round-1.stderr.txt) and
[failed manifest](history/phase-10-parser-upgrade-graphics-manifest.json) are
retained. That table-only implementation is also rejected. Final acceptance is
for the complete replacement reader/renderer, not either intermediate approach.
The final runs follow these corrections and do not relabel earlier attempts.

Reproduce after installing the pinned CI, extraction and Windows GUI requirements
and building/installing the wheel:

```powershell
.tools/python/python.exe scripts/verify_pdf_stability.py --rounds 3 --desktop --output .tools/pdf-stability/new-verification
```

The runner asserts installed imports, parser versions and matching package code,
captures each round's stdout/stderr and complete JUnit status, and fails at the
first failed round. It never automatically retries. Use a fresh output directory.
CI also runs three combined wheel rounds without the optional desktop suite and
uploads each attempt's output, including failures. Remote execution is pending.

These checks establish reliable extraction for this runtime and the recorded
corpus policy; they do not assert perfect OCR or universal recognition of every
manufacturer table. Extracted engineering values remain unreviewed UNKNOWN
Evidence, and the existing human-review boundary remains enforced.
