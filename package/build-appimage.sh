#!/bin/bash
# Construye SoulBlade-Recompiled-x86_64.AppImage desde este repositorio.
#
# Requisitos: generated/ y build-release/ compilados (ninja -C build-release psx-runtime),
# el disco original en "$DISC_DIR", y red la primera vez (el empaquetador
# descarga linuxdeploy y appimagetool con SHA-256 verificado).
#
# Uso:  package/build-appimage.sh [--verify-only]
#       SOULBLADE_DISC_DIR="/ruta/a/Soul Blade V1.1" package/build-appimage.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PKG="$ROOT/package"
GAME="$ROOT/source/SoulBladeRecomp"
RELEASE="$GAME/build-release"
PAYLOAD="$PKG/payload"
OUTDIR="$PKG/out"
APPIMAGE="$OUTDIR/SoulBlade-Recompiled-x86_64.AppImage"
DISC_DIR="${SOULBLADE_DISC_DIR:-${DISC_DIR:-$ROOT/Soul Blade V1.1}}"
# Framework: psxrecomp checkout (pinned commit + patches from patches/, see scripts/fetch-framework.sh)
PSXRECOMP="${PSXRECOMP_ROOT:-$GAME/psxrecomp}"
CUE_NAME="Soul Blade (v1.1).cue"
BIN_NAME="Soul Blade (v1.1).bin"

die() { echo "ERROR: $*" >&2; exit 1; }

verify_disc() {
    local dir="$1"
    [ -f "$dir/$BIN_NAME" ] || die "falta $dir/$BIN_NAME"
    [ -f "$dir/$CUE_NAME" ] || die "falta $dir/$CUE_NAME"
    local want got
    want="$(sha1sum "$DISC_DIR/$BIN_NAME" | cut -d' ' -f1)"
    got="$(sha1sum "$dir/$BIN_NAME" | cut -d' ' -f1)"
    [ "$want" = "$got" ] || die "el BIN empaquetado no coincide con el original"
    want="$(md5sum "$DISC_DIR/$CUE_NAME" | cut -d' ' -f1)"
    got="$(md5sum "$dir/$CUE_NAME" | cut -d' ' -f1)"
    [ "$want" = "$got" ] || die "el CUE empaquetado no coincide con el original"
    # El CUE referencia el BIN por nombre relativo: deben convivir.
    grep -aqF "FILE \"$BIN_NAME\" BINARY" "$dir/$CUE_NAME" \
        || die "el CUE no referencia $BIN_NAME"
}

verify_appimage() {
    local tmp
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/soulblade-verify.XXXXXX")"
    ( cd "$tmp" && "$APPIMAGE" --appimage-extract >/dev/null 2>&1 ) \
        || die "no se pudo extraer la AppImage"
    local root="$tmp/squashfs-root"
    [ -x "$root/AppRun" ] || die "AppRun no ejecutable en el paquete"
    [ -f "$root/usr/bin/SoulBlade_Recompiled" ] || die "falta el ejecutable"
    [ -f "$root/usr/bin/bios/openbios.bin" ] || die "el BIOS no se resuelve junto al ejecutable"
    [ -f "$root/usr/share/soulblade/disc/$BIN_NAME" ] || die "falta el BIN en el paquete"
    verify_disc "$root/usr/share/soulblade/disc"
    if grep -rlF "$HOME" "$root/AppRun" "$root/usr/share/soulblade/game.toml" \
            "$root/soulblade.desktop" >/dev/null 2>&1; then
        die "el paquete contiene rutas absolutas del equipo de desarrollo ($HOME)"
    fi
    if LD_LIBRARY_PATH="$root/usr/lib" ldd "$root/usr/bin/SoulBlade_Recompiled" 2>/dev/null \
            | grep -q "not found"; then
        die "quedan bibliotecas sin resolver"
    fi
    echo "Verificacion del paquete: OK"
    rm -rf "$tmp"
}

if [ "${1:-}" = "--verify-only" ]; then
    [ -f "$APPIMAGE" ] || die "no existe $APPIMAGE"
    verify_appimage
    echo "$APPIMAGE"
    sha256sum "$APPIMAGE"
    exit 0
fi

[ -d "$PSXRECOMP/runtime" ] || die "falta el framework en $PSXRECOMP (ejecuta scripts/fetch-framework.sh)"
[ -d "$GAME/generated" ] || die "falta generated/: ejecuta scripts/generate.sh con tu copia local del juego"
[ -x "$RELEASE/SoulBlade_Recompiled" ] || die "compila antes: ninja -C $RELEASE psx-runtime"
verify_disc "$DISC_DIR"

echo "== Payload =="
rm -rf "$PAYLOAD"
mkdir -p "$PAYLOAD/disc" "$PAYLOAD/assets" "$PAYLOAD/bios"
cp "$RELEASE/SoulBlade_Recompiled" "$RELEASE/SoulBlade_Recompiled.execution.json" "$PAYLOAD/"
cp "$RELEASE/bios/openbios.bin" "$RELEASE/bios/OpenBIOS.LICENSE" "$PAYLOAD/bios/"
ICON="$RELEASE/assets/psxrecomp.png"
[ -f "$ICON" ] || ICON="$PSXRECOMP/assets/psxrecomp.png"
[ -f "$ICON" ] || die "no encuentro psxrecomp.png ni en el build ni en el framework"
cp "$ICON" "$PAYLOAD/assets/"
cp "$RELEASE/game.toml" "$RELEASE/game_options.toml" "$PAYLOAD/"
# game.toml del paquete: sin rutas del equipo de desarrollo. La clave `disc`
# solo la usa el recompilador; el runtime recibe --disc desde el AppRun.
sed -i "s|^disc = .*|disc = \"disc/$CUE_NAME\"|" "$PAYLOAD/game.toml"
cp "$DISC_DIR/$BIN_NAME" "$DISC_DIR/$CUE_NAME" "$PAYLOAD/disc/"
verify_disc "$PAYLOAD/disc"

echo "== Empaquetado =="
mkdir -p "$OUTDIR"
rm -f "$APPIMAGE" "$APPIMAGE.sha256"
( cd "$PSXRECOMP" && ./tools/package_appimage.sh \
    --payload "$PAYLOAD" --exe-name SoulBlade_Recompiled --payload-name soulblade \
    --app-run "$PKG/AppRun" --desktop-file "$PKG/soulblade.desktop" --icon "$PKG/soulblade.png" \
    --output "$APPIMAGE" --framework "$PSXRECOMP" \
    --prune-unreferenced-libs --jobs "${JOBS:-8}" )

verify_appimage
( cd "$OUTDIR" && sha256sum "$(basename "$APPIMAGE")" > "$(basename "$APPIMAGE").sha256" )
echo
echo "AppImage: $APPIMAGE"
ls -l "$APPIMAGE" | awk '{print "Tamano:  " $5 " bytes"}'
cat "$APPIMAGE.sha256"
