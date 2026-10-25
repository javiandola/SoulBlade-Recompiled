#!/bin/bash
# Build the recompiler and generate the game-specific C from YOUR OWN copy of the
# disc. Nothing derived from the game ships in this repository: this step is where
# the machine code is translated, on your machine, from your dump.
#
# Usage: SOULBLADE_DISC_DIR="/path/to/Soul Blade V1.1" scripts/generate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
GAME="$ROOT/source/SoulBladeRecomp"
FW="${PSXRECOMP_ROOT:-$GAME/psxrecomp}"
DISC_DIR="${SOULBLADE_DISC_DIR:?define SOULBLADE_DISC_DIR with the folder holding your .cue/.bin}"
CUE_NAME="Soul Blade (v1.1).cue"
JOBS="${JOBS:-$(nproc)}"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -d "$FW/recompiler" ] || die "falta el framework: ejecuta scripts/fetch-framework.sh"
[ -f "$DISC_DIR/$CUE_NAME" ] || die "no encuentro $DISC_DIR/$CUE_NAME"
[ -f "$DISC_DIR/Soul Blade (v1.1).bin" ] || die "falta el .bin junto al .cue (el CUE lo referencia por nombre)"

echo "== 1/3 preparar disco (copia a disc/ y extrae el EXE) =="
python3 "$FW/tools/prepare_disc.py" "$DISC_DIR/$CUE_NAME" \
    --config "$GAME/game.toml" --project-root "$GAME"

echo "== 2/3 compilar el recompilador =="
cmake -S "$FW/recompiler" -B "$GAME/build-recompiler" -G Ninja \
      -DCMAKE_BUILD_TYPE=Release > /dev/null
ninja -C "$GAME/build-recompiler" -j "$JOBS"

echo "== 3/3 generar el codigo del juego =="
"$GAME/build-recompiler/psxrecomp-game" --config "$GAME/game.toml" \
      --out-dir "$GAME/generated" --project-root "$GAME"

[ -d "$GAME/generated" ] || die "la generacion no produjo generated/"
echo "OK: $(ls "$GAME/generated" | wc -l) ficheros en generated/"
echo
echo "Siguiente: ninja -C \"$GAME/build-release\" psx-runtime -j $JOBS"
