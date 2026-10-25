#!/bin/bash
# Fetch the psxrecomp framework at the exact commit this project was built against
# and apply the local patches (patches/*.patch).
#
# Usage: scripts/fetch-framework.sh
# Env:   PSXRECOMP_URL  override the upstream URL
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
GAME="$ROOT/source/SoulBladeRecomp"
FW="$GAME/psxrecomp"
URL="${PSXRECOMP_URL:-https://github.com/mstan/psxrecomp.git}"

# Pinned in source/SoulBladeRecomp/framework_pins.txt
PIN="$(sed -n 's/^psxrecomp=\([0-9a-f]\{7,40\}\).*/\1/p' "$GAME/framework_pins.txt" | head -1)"
PIN="${PIN:-31df2e1e0e0a6525733e68ff70e72ecbef84bb09}"

die() { echo "ERROR: $*" >&2; exit 1; }

echo "== psxrecomp @ $PIN =="
if [ -d "$FW/.git" ]; then
    echo "   ya clonado en $FW"
else
    mkdir -p "$(dirname "$FW")"
    git clone "$URL" "$FW"
fi

git -C "$FW" fetch --quiet origin || die "no se pudo contactar con $URL"
git -C "$FW" checkout --quiet --detach "$PIN" 2>/dev/null \
    || git -C "$FW" fetch --quiet origin "$PIN" && git -C "$FW" checkout --quiet --detach "$PIN"
echo "   HEAD: $(git -C "$FW" rev-parse --short HEAD)"

echo "== submodulos (retcomm-rbengine: backend del rebobinado) =="
git -C "$FW" submodule update --init --recursive \
    || die "no se pudieron inicializar los submodulos (revisa la red)"
for sub in lib/recomp-net lib/retcomm-rbengine; do
    [ -n "$(ls -A "$FW/$sub" 2>/dev/null)" ] || die "submodulo vacio: $sub"
done

echo "== parches =="
shopt -s nullglob
count=0
for p in "$ROOT"/patches/*.patch; do
    if git -C "$FW" apply --check "$p" 2>/dev/null; then
        git -C "$FW" apply "$p"
        echo "   aplicado $(basename "$p")"
        count=$((count + 1))
    elif git -C "$FW" apply --reverse --check "$p" 2>/dev/null; then
        echo "   ya aplicado $(basename "$p")"
    else
        die "no se pudo aplicar $(basename "$p"): el framework no coincide con el commit fijado"
    fi
done
echo "   $count parche(s) aplicados"

[ -f "$FW/runtime/runtime.cmake" ] || die "el checkout no parece psxrecomp (falta runtime/runtime.cmake)"
echo "Framework listo en $FW"
