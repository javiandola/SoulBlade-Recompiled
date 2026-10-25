#!/usr/bin/env python3
"""Valida checksums y directorio de una tarjeta de memoria PS1 (128 KB).

Uso:
    python3 check_mcd.py <tarjeta.mcd> [<otra.mcd> ...]

Comprueba, por frame de 128 B, que el byte 0x7F sea el XOR de los bytes 0x00-0x7E,
que es lo que una tarjeta real verifica al escribir. Tambien lista las entradas
del directorio y los bloques marcados como defectuosos.

Codigo de salida: 0 si todas las tarjetas son validas, 1 si alguna tiene fallos.
"""
import functools
import struct
import sys

FRAME = 128
FRAMES = 1024
BLOCK = 8192


def xor_frame(f):
    return functools.reduce(lambda a, b: a ^ b, f[:127], 0)


def check(path):
    data = open(path, "rb").read()
    print(f"== {path}  ({len(data)} B)")
    if len(data) != FRAMES * FRAME:
        print(f"   AVISO: se esperaban {FRAMES*FRAME} B (128 KB)")
        if len(data) < FRAMES * FRAME:
            return 1

    print(f"   firma frame 0: {data[0:2]!r}")

    bad = [i for i in range(FRAMES)
           if xor_frame(data[i*FRAME:(i+1)*FRAME]) != data[i*FRAME+127]]
    ok = FRAMES - len(bad)
    print(f"   checksums: {ok}/{FRAMES} correctos, {len(bad)} invalidos")
    if bad:
        bloques = sorted({b // 64 for b in bad})
        print(f"   frames invalidos: {bad[:16]}{' ...' if len(bad) > 16 else ''}")
        print(f"   bloques afectados (8 KB): {bloques}")

    print("   directorio:")
    entradas = 0
    for i in range(1, 16):
        e = data[i*FRAME:(i+1)*FRAME]
        if e[0] not in (0x51, 0x52, 0x53):
            continue
        entradas += 1
        orden = struct.unpack("<H", e[0x02:0x04])[0]
        size = struct.unpack("<I", e[0x04:0x08])[0]
        nxt = struct.unpack("<H", e[0x08:0x0A])[0]
        name = e[0x0A:0x1E].decode("ascii", "replace").rstrip("\x00")
        print(f"     estado=0x{e[0]:02X} orden={orden:#06x} tamaño={size} B "
              f"siguiente={nxt:#06x} nombre={name!r}")
    if not entradas:
        print("     (vacia)")
    return 1 if bad else 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for p in sys.argv[1:]:
        rc |= check(p)
    print()
    print("RESULTADO:", "tarjetas validas" if rc == 0 else "HAY FALLOS DE CHECKSUM")
    return rc


if __name__ == "__main__":
    sys.exit(main())
