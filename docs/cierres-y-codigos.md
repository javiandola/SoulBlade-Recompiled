# Códigos de salida observados (evidencia de cierre)

Los códigos provienen del `$?` del proceso del juego en el wrapper de cada ejecución en
segundo plano. El runtime **no imprime** ninguna línea de apagado en stdout, así que el código
de salida es la única prueba registrada; aquí queda persistido porque el volcado del job no
vive en `logs/` (y `logs/` está fuera de Git).

| Ejecución | Cómo terminó | Código | Nota |
|---|---|---|---|
| `build-release/SoulBlade_Recompiled` (ventana, telemetría FPS) | `SIGTERM` (`kill -TERM`) | **0** | SDL convierte la señal en evento de cierre; sale ordenado |
| `build-debug/SoulBlade_Recompiled` (1.ª instancia, TCP 4370) | terminó junto a su shell padre | **0** | — |
| `./run.sh --debug` (2.ª instancia, prueba de carga del save) | `quit` por TCP | **0** | `logs/run-debug-2.log`, última línea `exit=0` |

Comprobaciones asociadas:

- Tarjeta `saves/card1.mcd`: md5 `3bea444d…` antes y después del SIGTERM → **no se corrompe**.
- `overlay_captures.json` se reescribe en el cierre (20:00, 6.460 B) y el histórico vive en
  `overlay_captures.json.d/` (10 capturas).
- Ninguna de estas salidas dejó procesos huérfanos: `ps -eo args | grep -F SoulBlade_Recompiled`
  queda vacío después de cada una.

## Corrección respecto al informe previo

En el informe de la sesión 2 dije que el SIGTERM «termina sin volcado ordenado». El batch de
procesos en segundo plano demostró lo contrario: el wrapper registró `run exit=0`, es decir,
SDL tradujo la señal a un evento de cierre y el proceso salió normalmente. Queda corregido en
`tests/PRUEBAS.md` (T11) y en la bitácora.
