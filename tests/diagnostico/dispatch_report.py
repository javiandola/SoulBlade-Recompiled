import os
#!/usr/bin/env python3
"""Informe de despacho: cruza PCs interpretados con rangos compilados y candidatos.

Responde a la pregunta «¿por qué este código, estando compilado, se ejecuta por el
intérprete?» distinguiendo tres causas posibles:

  A) hueco de cobertura   -> el PC no cae en ningún rango .ranges
  B) sin candidato        -> hay rango compilado, pero la tabla de candidatos del
                             runtime no tiene ninguna entrada en esa region
  C) CRC no coincide      -> hay candidato, pero match=0 (los bytes vivos no son los
                             de la variante compilada)

Uso (con una instancia debug viva en 127.0.0.1:4370):
    python3 dispatch_report.py [--game-dir DIR] [--top N]

No modifica nada: solo consulta dirty_ram_stats, overlay_candidates y los .ranges.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

DEFAULT_GAME = os.environ.get("SOULBLADE_PROJECT", ".")


def dbg(game_dir, cmd, *args):
    client = os.path.join(game_dir, "psxrecomp/tools/debug_client.py")
    out = subprocess.run([sys.executable, client, cmd, *args],
                         capture_output=True, text=True, timeout=90).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"error": out[:200]}


def load_ranges(game_dir):
    pat = os.path.join(game_dir, "build-debug/cache/SLUS-00240/gcc/linux-x64/*/*.ranges")
    iv = []
    for f in glob.glob(pat):
        for line in open(f):
            s = line.strip()
            m = re.match(r"R ([0-9A-F]+) ([0-9A-F]+)", s)
            if m:
                a = int(m.group(1), 16)
                iv.append((a, a + int(m.group(2), 16)))
    return iv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", default=DEFAULT_GAME)
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    st = dbg(args.game_dir, "dirty_ram_stats")
    if st.get("error"):
        print("No se pudo consultar el runtime:", st["error"])
        return 1

    pcs = []
    for e in (st.get("per_pc") or []):
        pcs.append((int(e["pc"], 16) & 0x1FFFFF, e.get("hits", 0), e.get("insns", 0)))
    pcs.sort(key=lambda x: -x[2])

    iv = load_ranges(args.game_dir)
    cands = (dbg(args.game_dir, "overlay_candidates").get("candidates") or [])
    cand_by_addr = {int(c["addr"], 16): c for c in cands}

    def covered(p):
        return any(a <= p < b for a, b in iv)

    print(f"PCs interpretados distintos: {len(pcs)} | intervalos compilados: {len(iv)} "
          f"| candidatos del runtime: {len(cands)}")
    print(f"total insns interpretadas: {sum(i for _, _, i in pcs):,}\n")
    print(f"{'region':10s} {'hits':>9s} {'insns':>12s}  causa")

    seen = {}
    for p, h, i in pcs[:args.top]:
        region = p & 0xFFF000
        cov = covered(p)
        cand = cand_by_addr.get(p)
        if not cov:
            causa = "A) hueco de cobertura"
        elif cand is None:
            causa = "B) sin candidato en esa direccion"
        elif not cand.get("match"):
            causa = f"C) CRC no coincide (crc={cand.get('crc')} live={cand.get('live')})"
        else:
            causa = "D) candidato valido pero se ejecuto por interprete (investigar despacho)"
        print(f"0x{region:06X} {h:9,d} {i:12,d}  {causa}")
        seen[region] = seen.get(region, 0) + i

    if seen:
        print("\npeso por region (insns interpretadas de las mostradas):")
        for r, i in sorted(seen.items(), key=lambda kv: -kv[1]):
            print(f"  0x{r:06X}: {i:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
