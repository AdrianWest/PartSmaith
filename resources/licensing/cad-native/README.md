# Additional native CAD libraries

This software uses the FreeImage open source image library.
See https://freeimage.sourceforge.io/ for details.

Portions of this software are copyright (C) 1996-2022 The FreeType Project
(https://www.freetype.org/). All rights reserved.

`vendors.json` identifies the additional native libraries in the original
Windows AMD64 `cadquery-ocp` 7.9.3.1.1 wheel. Its 24 additional DLLs were matched
to original Conda packages by reproducing delvewheel 1.12.1's DLL repair and
comparing the complete repaired SHA-256 with the bundled binary. JPEG XR 1.1
is linked statically into FreeImage; the matched FreeImage package's rendered
build recipe records the exact JPEG XR host package.

The vendor directories retain original copyright notices, licenses, rendered
recipes, patches and build scripts. `sources/` contains the exact original
upstream source archives named and hashed in those recipes. The Microsoft
Visual C++ redistributable is retained as an original installer, not described
as available Microsoft source code. Its two shipped DLLs retain their original
bytes; their upstream repair renamed their filenames without changing bytes.

FreeImage is distributed under its GPL-3.0-or-later option, with the original
alternative license texts also retained. FreeType uses the FreeType License
(FTL) option. Other selected terms appear in `vendors.json`. PartSmith itself
is distributed under GPL-3.0-only. An upstream package's alternative license
declaration does not impose every alternative simultaneously.

The corresponding-source material for FreeImage includes the original source
archive plus the Conda build recipe, all original patches and CMake files.
LibRaw's corresponding material includes both the original LibRaw archive and
the exact LibRaw-cmake archive, together with its original build recipe.
The original source archives retain embedded copyright and license headers.
No application EULA restricts reverse engineering for debugging modifications
to these libraries. SHA-256 checks provide integrity, not a license restriction
on replacing or modifying library code.

To rebuild or replace a library, unpack its archive(s) in the layout described
by its rendered recipe, apply the retained patches and run its retained build
script with the declared build dependencies. Apply the upstream delvewheel
1.12.1 repair to a producer copy of the wheel using its recorded DLL dependency
names. Retain your changed source and notices, update the runtime and vendor
lock identities for your build, then use `scripts/prepare_production_runtime.py`
and `scripts/build_production_pcm.py` to regenerate the inventory and PCM.
The application's Python source and launcher/packaging source are distributed
with PartSmith and in its repository; there is no signing key needed to produce
a replacement inventory. This is a producer operation; normal installation
uses the bundled interpreter and does not require independent build tools.

This supplement verifies the additional CAD vendors only. It does not certify
the cached OCP/OCCT SDK's header-only dependencies or vendor closure in the
other native Python wheels. Consult the Phase 14 native audit for open findings.
