# Third-party notices

This repository contains original glue code (build scripts, packaging, documentation and
diagnostics) plus patches to an external framework. **It does not contain the game**, neither the
disc image nor any translation of the game's machine code. See "Why `generated/` is not here" in
`README.md`.

Everything below is listed with the licence as found in the upstream sources at the pinned revision.

---

## psxrecomp — PlayStation recompilation framework

- Upstream: <https://github.com/mstan/psxrecomp>
- Pinned revision: `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` (recorded in
  `source/SoulBladeRecomp/framework_pins.txt`)
- Licence: **PolyForm Noncommercial License 1.0.0**
  (<https://polyformproject.org/licenses/noncommercial/1.0.0/>)
- Copyright (c) 2026 Matthew Stanley

The framework is **not vendored** in this repository. `scripts/fetch-framework.sh` clones it from
upstream and checks out the pinned commit. The files in `patches/` are modifications to that
framework and are distributed under the same licence as the code they modify. They are published so
that a build of this project is reproducible; they grant no rights beyond those of the upstream
licence.

PolyForm Noncommercial permits use, modification and redistribution **for noncommercial purposes
only**, provided the licence text and notices are kept. Commercial use requires a separate
arrangement with the copyright holder.

## OpenBIOS — bundled PlayStation BIOS replacement

- Project: OpenBIOS (free BIOS replacement used by psxrecomp when no retail dump is supplied)
- Licence: **MIT**
- Shipped by the framework at `bios/openbios.bin` together with `bios/OpenBIOS.LICENSE`, which is
  copied into the generated AppImage by the packaging script.

No retail Sony BIOS image is included in this repository, and the build does not download one.

## SDL3

- Project: <https://github.com/libsdl-org/SDL>
- Licence: **zlib**
- Used as a dynamic dependency of the runtime and bundled into the AppImage by `linuxdeploy`.

## linuxdeploy and appimagetool

- Projects: <https://github.com/linuxdeploy/linuxdeploy>, <https://github.com/AppImage/appimagetool>
- Licences: MIT
- Downloaded on demand by the packaging script into `~/.cache/recomp-appimage-tools`, with SHA-256
  verification against the digests pinned inside `psxrecomp/tools/package_appimage.sh`.

## Build and runtime dependencies not redistributed here

glibc, libstdc++, libgcc, Mesa/RADV, PipeWire/PulseAudio, X11/XWayland and the Wayland compositor are
provided by the host distribution and are **not** bundled. Their licences are those of the
distribution you build on.

---

## Material specific to the game

- The disc image (`.bin`/`.cue`), memory cards (`.mcd`), the personal save state (`.psv`) and the
  built AppImage (which embeds a copy of the disc) are **not** part of this repository and are not
  distributed under any licence here.
- `generated/` — the C translation of the game's MIPS code — is produced locally by the user from
  their own dump (`scripts/generate.sh`). It is a derivative of the game's executable and is the
  user's responsibility; it is deliberately excluded from version control and from any release.

## Original code in this repository

`scripts/`, `package/`, `docs/`, `tests/` and the project scaffolding in `source/SoulBladeRecomp/`
(CMake glue, `game.toml`, `codegen_setup.*`) were written for this project. They are distributed
under the **same PolyForm Noncommercial 1.0.0 terms** as the framework they are useless without: no
warranty, noncommercial use only. No additional restrictions are imposed and no rights over the game
are claimed.
