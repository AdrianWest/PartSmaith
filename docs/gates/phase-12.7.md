# Phase 12.7 — camera, layers and inspection

Rotate, Shift-drag pan, zoom, fit/reset and seven presets affect only display
state. Independent body, pad, silk, courtyard, fabrication, origin, axis and
pin-1 controls use actual STEP and footprint geometry. Absent graphic layers
remain absent. Selection shows actual pin-to-pad identity; measurements use
footprint coordinates in mm and STEP bounds declare a 0.01 mm mesh tolerance.
All XYZ placement vectors, nonuniform scale and mirrors are shown explicitly.

Source checks: 22 passed (`phase-12.7-source-results.xml`), including actual
render changes for rotation, zoom, resize, pan, body/pad/graphics visibility
and selected-pad highlighting; known 1 mm pad-centre distance and 0.35 mm body
height; IR, artifact and approval-binding invariance. Installed-wheel and final
hash closeout are rechecked in 12.10. Overall Phase 12 remains open.
