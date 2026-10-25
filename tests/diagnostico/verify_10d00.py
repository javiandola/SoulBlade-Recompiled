#!/usr/bin/env python3
"""Coordenadas y verificacion del bloque copiado en 0x10D00 (Soul Blade, SLUS-00240).

Uso:
    python3 verify_10d00.py                 # solo coordenadas y comparacion EXE<->EXE
    python3 verify_10d00.py ram.bin         # ademas compara con un volcado de RAM crudo
                                            # (read_ram 0x10D00 768 en el servidor de debug,
                                            #  volcado a binario)

No necesita emulador para las coordenadas: las deduce del BIN y del PS-X EXE.
Todo lo que imprime se puede recalcular desde los originales, sin capturas manuales.
"""
import struct
import sys
import hashlib

import os
BIN = os.path.join(os.environ.get("SOULBLADE_DISC_DIR", "."), "Soul Blade (v1.1).bin")
SECT, UOFF = 2352, 24

# Direcciones del objeto de estudio
DEST = 0x00010D00          # destino (direccion fisica de RAM / kseg0 0x80010D00)
SRC  = 0x00010F60          # origen del contenido (imagen del EXE en esa direccion)
SIZE = 0x300               # bytes copiados (medido por coincidencia exacta)

# Semillas observadas por instrumentacion (dirty_ram_stats)
SEEDS = [0x80010D3C, 0x80010D94, 0x80010D9C, 0x80010DAC]


def psi_exec(f, lba):
    f.seek(lba * SECT + UOFF)
    return f.read(2048)


def parse_root(f, pvd):
    root = pvd[156:156 + 34]
    lba = struct.unpack("<I", root[2:6])[0]
    size = struct.unpack("<I", root[10:14])[0]
    data = psi_exec(f, lba) if size <= 2048 else b"".join(
        psi_exec(f, lba + i) for i in range((size + 2047) // 2048))
    out, off = [], 0
    while off < size:
        L = data[off]
        if L == 0:
            off = ((off // 2048) + 1) * 2048
            continue
        rec = data[off:off + L]
        elba = struct.unpack("<I", rec[2:6])[0]
        esz = struct.unpack("<I", rec[10:14])[0]
        nlen = rec[32]
        name = rec[33:33 + nlen].decode("ascii", "replace")
        if name not in ("\x00", "\x01"):
            out.append((name, elba, esz))
        off += L
    return out


def main():
    ram = open(sys.argv[1], "rb").read() if len(sys.argv) > 1 else None
    with open(BIN, "rb") as f:
        pvd = psi_exec(f, 16)
        vol = pvd[40:72].decode("ascii", "replace").strip()
        files = parse_root(f, pvd)
        exe_lba, exe_size = next((l, s) for n, l, s in files if n.startswith("SLUS_002.40"))
        f.seek(exe_lba * SECT + UOFF)
        exe = f.read(exe_size)
    print(f"volumen ISO9660 ......... {vol}")
    print(f"SLUS_002.40 ............. LBA {exe_lba}, {exe_size} B, "
          f"offset BIN 0x{exe_lba * SECT + UOFF:X}")

    # Cabecera PS-X EXE
    magic = exe[0:8]
    load = struct.unpack("<I", exe[0x18:0x1C])[0]
    tsize = struct.unpack("<I", exe[0x1C:0x20])[0]
    entry = struct.unpack("<I", exe[0x10:0x14])[0]
    sp = struct.unpack("<I", exe[0x30:0x34])[0]
    print(f"cabecera PS-X EXE ....... {magic!r}")
    print(f"  load {load:#010X}  entry {entry:#010X}  text {tsize:#X}  sp {sp:#010X}")
    if load != 0x80010000:
        print(f"  AVISO: base de carga inesperada {load:#010X}")

    def cols(name, phys):
        virt = 0x80000000 | phys
        exe_off = 0x800 + (phys - (load & 0x1FFFFFFF))
        return (f"{name}: virtual {virt:#010X} | fisica {phys:#08X} | "
                f"clave dispatcher {phys & 0x1FFFFF:#08X} | "
                f"offset EXE 0x{exe_off:X} | offset BIN 0x{exe_lba * SECT + UOFF + exe_off:X}")

    print()
    print(cols("destino ", DEST))
    print(cols("origen  ", SRC))

    src_bytes = exe[0x800 + (SRC - (load & 0x1FFFFFFF)):
                    0x800 + (SRC - (load & 0x1FFFFFFF)) + SIZE]
    print()
    print(f"tamano del bloque ....... {SIZE} B (0x{SIZE:X})")
    print(f"desplazamiento .......... {SRC - DEST:#x} ({SRC - DEST} B) hacia abajo")
    print(f"sha256 del origen ....... {hashlib.sha256(src_bytes).hexdigest()}")
    print(f"primeras 8 palabras ..... " +
          " ".join(f"{w:08X}" for w in struct.unpack("<8I", src_bytes[:32])))

    # Lo que la imagen del EXE tiene EN EL DESTINO (para probar que son distintos)
    dest_own = exe[0x800 + (DEST - (load & 0x1FFFFFFF)):
                   0x800 + (DEST - (load & 0x1FFFFFFF)) + SIZE]
    print(f"imagen EXE en el destino  {hashlib.sha256(dest_own).hexdigest()} "
          f"-> {'IGUAL' if dest_own == src_bytes else 'DISTINTA'} al origen")

    print()
    print("semillas observadas (direccion virtual, offset dentro del bloque, palabra):")
    for s in SEEDS:
        off = (s & 0x1FFFFFFF) - DEST
        word = struct.unpack("<I", src_bytes[off:off + 4])[0]
        print(f"  {s:#010X}  +0x{off:03X}  {word:08X}")

    if ram is not None:
        print()
        print(f"volcado de RAM .......... {len(ram)} B")
        ok = ram[:SIZE] == src_bytes
        print(f"RAM[0x10D00..] == EXE[0x10F60..] : {'SI' if ok else 'NO'}")
        if not ok:
            diff = [i for i in range(min(len(ram), SIZE)) if ram[i] != src_bytes[i]]
            print(f"  primeros bytes distintos: {[hex(d) for d in diff[:8]]}")
        print(f"sha256 del volcado ...... {hashlib.sha256(ram[:SIZE]).hexdigest()}")


if __name__ == "__main__":
    main()
