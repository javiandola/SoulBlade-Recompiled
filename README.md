# Soul Blade Recompiled

A **native x86-64 Linux** build of *Soul Blade* (PlayStation 1, SLUS-00240 v1.1), produced by static
recompilation of the game's MIPS code into C with the [psxrecomp](https://github.com/mstan/psxrecomp)
framework, plus the glue needed to build it, package it as an AppImage and verify it.

This is an independent reverse-engineering and recompilation project. It is **not** affiliated with,
endorsed by or supported by Namco, Sony or any rights holder. *Soul Blade* and PlayStation are
trademarks of their respective owners.

**No game data is distributed here.** You need your own legally obtained copy of the disc. The
repository ships no `.bin`, no `.cue`, no BIOS dump, no memory card and no build of the game.

---

## What it does

The PlayStation CPU code is translated ahead of time into C, compiled with the host toolchain and
executed by a small runtime that provides the PS1 hardware model (GPU, SPU, CD-ROM, pads, timers,
memory cards). No emulator interprets the game loop: the boot path and the game code run as native
x86-64 with the runtime handling the hardware register interface.

Verified on the reference machine (Ryzen 5 5500, Radeon RX 6600 XT, Mesa RADV):

| item | result |
|---|---|
| Frame rate | 59.6–60.4 fps, ratio 1.00x, at 1080p and 4K internal |
| Stability | 8 min 34 s soak, 31 006 frames, 0 errors, RSS plateau ~350 MB, clean SIGTERM exit |
| Video backends | Wayland (`wayland-*` / `gamescope-*`) and X11/XWayland |
| Audio | active PipeWire/PulseAudio sink-input while in a match |
| Input | one wireless pad verified by the author in the packaged build |
| Distributions | CachyOS (built and run) and Bazzite / Fedora 44 Gaming Mode (run) |
| Packaging | 371 300 856 B AppImage, self-contained (disc, BIOS and libs inside) |

### What is **not** verified

Be sceptical of anything not in the table above:

- **Saving and loading was never validated end to end** in the packaged build. The memory-card path
  is implemented and its write protocol has unit tests, but menu-driven save/load was out of scope by
  decision of the author.
- **Two pads at once were not verified in the final package.** A single pad was.
- The AppImage was not tested on a distribution older than glibc 2.38.
- Gameplay was reached through injected input during bring-up; the author confirmed it by hand with a
  pad, but there is no automated gameplay test in this repository.

---

## Why `generated/` is not here

`generated/` is 76 MB of C translated from the game's own executable. That is a derivative of the
game, so it is **not** published. You produce it locally with `scripts/generate.sh` from your own
dump; it is git-ignored, and it never leaves your machine unless you choose otherwise.

The same applies to `disc/` (the extracted boot EXE) and to the AppImage, which embeds a copy of the
disc.

---

## Requirements

Build host:

- Linux x86-64, glibc ≥ 2.38 (Fedora 39+/Ubuntu 23.10+ or any current rolling release)
- CMake ≥ 3.20, Ninja, a C/C++17 toolchain (GCC 13+ or Clang 16+)
- Python 3.10+
- Git, and network access the first time (framework checkout and packaging tools)
- `libsdl3` headers are **not** required: the framework ships its own SDL3 sources

Runtime target: glibc ≥ 2.38, `libstdc++` providing `GLIBCXX_3.4.30` (GCC 11), a working Mesa/OpenGL
stack and PipeWire or PulseAudio. Graphics drivers are deliberately **not** bundled.

Your own disc dump: a Redump-style `.bin` (MODE2/2352) plus `.cue`, single or multi-track.

---

## Build

```bash
git clone https://github.com/<your-account>/SoulBlade-Recompiled.git
cd SoulBlade-Recompiled

# 1. Framework at the pinned commit + local patches
scripts/fetch-framework.sh

# 2. Translate the game from YOUR copy of the disc into generated/
export SOULBLADE_DISC_DIR="/path/to/Soul Blade V1.1"   # holds the .cue and .bin
scripts/generate.sh

# 3. Release runtime
scripts/build.sh

# 4. AppImage (embeds the disc copy you are allowed to use locally)
SOULBLADE_DISC_DIR="$SOULBLADE_DISC_DIR" package/build-appimage.sh
```

Output: `package/out/SoulBlade-Recompiled-x86_64.AppImage`.

`scripts/build.sh` is idempotent and skips the steps already done, so a plain
`SOULBLADE_DISC_DIR=... scripts/build.sh` after a fresh clone is enough.

### Environment variables

| variable | used by | meaning |
|---|---|---|
| `SOULBLADE_DISC_DIR` | `scripts/generate.sh`, `package/build-appimage.sh` | folder with your `.cue`/`.bin`; never copied into git |
| `PSXRECOMP_ROOT` | all scripts | framework checkout path, defaults to `source/SoulBladeRecomp/psxrecomp` |
| `PSXRECOMP_URL` | `scripts/fetch-framework.sh` | override the upstream URL (mirrors) |
| `JOBS` | generate/build/package | parallelism, defaults to `nproc` |

### Verifying a build

```bash
package/build-appimage.sh --verify-only
```

Extracts the AppImage and checks: `AppRun` executable, runtime binary present, bundled BIOS reachable
next to the executable, disc files identical (SHA-1/MD5) to the ones you passed in, no absolute paths
from your home directory inside the package, and no unresolved shared libraries. It is fast and
non-destructive.

Extra diagnostics live in `tests/diagnostico/` (memory-card checksum audit, dispatch coverage report,
SDL probe, pad polling).

---

## Running

```bash
chmod +x package/out/SoulBlade-Recompiled-x86_64.AppImage
./package/out/SoulBlade-Recompiled-x86_64.AppImage
```

Writable state goes to `${XDG_DATA_HOME:-~/.local/share}/soulblade/`:

- `game.toml` — copied from the package on first run, then yours
- `saves/` — memory cards (`card1.mcd`, `card2.mcd`)
- `overlay_captures.json` — overlay capture store

The launcher (`package/AppRun`) passes `--disc` explicitly, detects the compositor when started
without a graphical environment (SSH, systemd unit) and keeps `LD_LIBRARY_PATH` untouched so the
bundled libraries never leak into child processes.

Debug output: `PSX_FPS_TELEMETRY=1` prints frame rate and frame count.

---

## Repository layout

```
docs/                     technical notes: architecture, packaging, decisions, test log, cleanup
package/                  AppRun, build-appimage.sh, .desktop and icon
patches/                  local patches to psxrecomp (4 commits over the pinned revision)
scripts/                  fetch-framework.sh, generate.sh, build.sh
source/SoulBladeRecomp/   project glue: CMakeLists.txt, game.toml, disc probe, codegen setup
tests/                    diagnostics and the test log (docs/PRUEBAS.md)
THIRD_PARTY_NOTICES.md    licences: psxrecomp (PolyForm Noncommercial), OpenBIOS (MIT), SDL3 (zlib)
```

Paths in the build tree are relative to the repository root; nothing assumes a particular home
directory. The framework is an external checkout, never vendored, so its pinned revision is explicit
in `source/SoulBladeRecomp/framework_pins.txt` and its patches are reviewable in `patches/`.

---

## Known issues

- **Saving is unproven** (see above). Treat memory cards as untested functionality.
- `settings.toml`, if the game writes it, lands next to the `.AppImage` rather than in XDG: the
  runtime has no configuration-path variable. The directory must be writable.
- `mods/` is not shipped. On a read-only install the runtime logs `mods state not persisted` and
  continues; that is expected.
- The AppImage is read-only, so overlay auto-compilation is disabled inside it. Gameplay is
  unaffected: measured coverage changes make no difference to frame rate (see
  `docs/overlays-aot.md`).
- No CI is provided that builds the game: the translation step needs a disc image, which must never
  reach a CI runner or a public artefact.

---

## Licence

See `THIRD_PARTY_NOTICES.md`. In short: the framework this project builds on is **PolyForm
Noncommercial 1.0.0** (noncommercial use only), and the original glue in this repository is offered
under the same terms. The game remains the property of its rights holders; this project grants you
nothing over it.

## History

This repository has a **fresh, audited history**. The private development history was not published
because it contained large build artefacts and paths of the author's machine; only the reviewed tree
is here, in a small number of commits.

---

## Reproduction check (performed before publication)

The whole flow was executed from a **fresh clone** of this repository, with the disc kept outside
the tree, on CachyOS (Ryzen 5 5500, RX 6600 XT):

| step | result |
|---|---|
| `git clone` | 42 files, 2 commits, no game data |
| `scripts/fetch-framework.sh` | psxrecomp `31df2e1e` + 4 patches + 2 submodules |
| `scripts/generate.sh` | 62 files / 76 MB written to `generated/` from the local disc |
| `scripts/build.sh` | `SoulBlade_Recompiled`, 40 341 264 B |
| `package/build-appimage.sh` | AppImage built and verified (`--verify-only`: OK) |
| run the built AppImage | `disc region NTSC-U (serial SLUS-00240)`, 60.0 fps |

The AppImage built from the clone is **not byte-identical** to any other build (squashfs ordering and
timestamps differ); its size was 371 304 952 B against 371 300 856 B for the reference build. What
matters is that it verifies and runs. `generated/` and `disc/` never left the working tree.
