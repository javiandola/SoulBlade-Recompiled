#!/bin/bash
# One-shot build: framework -> generation -> release runtime.
# The AppImage is a separate step (package/build-appimage.sh) because it also
# needs the disc folder to embed the copy you are allowed to use locally.
#
# Usage: SOULBLADE_DISC_DIR="/path/to/Soul Blade V1.1" scripts/build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
GAME="$ROOT/source/SoulBladeRecomp"
JOBS="${JOBS:-$(nproc)}"

if [ ! -d "$GAME/psxrecomp/runtime" ]; then
    "$ROOT/scripts/fetch-framework.sh"
fi
if [ ! -d "$GAME/generated" ]; then
    "$ROOT/scripts/generate.sh"
fi

echo "== compilar el runtime de release =="
cmake -S "$GAME" -B "$GAME/build-release" -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON \
      -DPSXRECOMP_ROOT="$GAME/psxrecomp" > /dev/null
ninja -C "$GAME/build-release" psx-runtime -j "$JOBS"

echo
echo "Binario: $GAME/build-release/SoulBlade_Recompiled"
echo "AppImage: SOULBLADE_DISC_DIR=\"$SOULBLADE_DISC_DIR\" package/build-appimage.sh"
