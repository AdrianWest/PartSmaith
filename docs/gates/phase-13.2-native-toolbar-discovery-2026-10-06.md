# KiCad 10.0.6 IPC toolbar icon discovery

Read-only official-source finding, recorded 2026-10-06. This is not a gate PASS
or an independent live-action acceptance record.

The [tagged native implementation](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/eda_draw_frame.cpp)
builds API plugin tools in `EDA_DRAW_FRAME::AddApiPluginTools`, lines 1430–1451.
It obtains the ready actions for the frame's scope, omits actions only when their
configured visibility is false, selects a valid dark icon or the light icon,
and creates each tool with an empty label. It supplies no default icon when the
selected bundle is invalid. It then binds the button to the action identifier.
Consequently, an action with no icons can occupy a blank clickable toolbar slot;
missing pixels do not prove dependency or IPC readiness failure.

The root agent reported the actual PCM 0.1.3 blank slot launching the managed
Python 3.12 board chooser. That desktop observation belongs in the root's live
evidence. The source finding explains the behavior and requires a real packaged
icon in the next release so the user can identify the action.

The exact downloaded source is retained as
`.tools/phase13-discovery/kicad-10.0.6-eda_draw_frame.cpp`, 47,420 bytes,
SHA-256 `619d60d66ceca1fbbc4c1785b7704c603582466138b8e0888b7c7ee814c1d5b2`.
This investigation changed no plugin payload, installed environment, settings,
project or UI state.
