#!/usr/bin/env python3
"""Muestreo rápido del pad que ve el juego, para capturar pulsaciones cortas.

IMPORTANTE: el servidor de depuración de psxrecomp atiende UN comando por conexión y
cierra el socket. Un socket persistente devuelve la primera respuesta y luego falla con
"Broken pipe" en todas las siguientes (comprobado), así que aquí se abre una conexión
nueva por muestra.

Uso: python3 pad_poll_fast.py <segundos> <salida.txt> [intervalo_ms]
"""
import socket, json, time, sys

HOST, PORT = "127.0.0.1", 4370
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/pad_fast.txt"
STEP = (float(sys.argv[3]) if len(sys.argv) > 3 else 60.0) / 1000.0


def query(cmd):
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((json.dumps({"cmd": cmd}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    if not buf:
        raise RuntimeError("respuesta vacía")
    return json.loads(buf.decode(errors="replace").strip().splitlines()[-1])


t0 = time.time()
seen = {}
last = None
ok = fail = 0
print(f"muestreando {DUR:.0f}s cada {STEP * 1000:.0f} ms (conexión por muestra)")
while time.time() - t0 < DUR:
    try:
        r = query("pad_status")
        ok += 1
        w = r.get("slot0", {}).get("buttons")
        if w and w != last:
            seen[w] = seen.get(w, 0) + 1
            last = w
    except Exception:
        fail += 1
    time.sleep(STEP)

lines = [f"{w}  x{n}" for w, n in sorted(seen.items(), key=lambda kv: -kv[1])]
open(OUT, "w").write("\n".join(lines) + "\n")
print(f"muestras ok={ok} fallidas={fail}")
print("palabras observadas:")
for l in lines:
    print("  " + l)
print(f"--- guardado en {OUT}")
