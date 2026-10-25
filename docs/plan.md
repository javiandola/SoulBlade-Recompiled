# Plan de trabajo — Port nativo Linux de Soul Blade

Estado: fases 0–2 ejecutadas en esta sesión. Este documento se actualiza a medida que
avanza el trabajo.

## Fase 0 — Auditoría (COMPLETA)

Ver `auditoria-inicial.md`. Resumen: sistema apto, framework compila, disco identificado
como SLUS-00240, repositorio original del juego inexistente.

## Fase 1 — Recuperación y preparación del código (COMPLETA con desviación)

- Repositorio `fabioap-cpu/SoulBlade_Recomp`: inaccesible (404 + “repo missing” en recomp.fyi).
  No se localizó copia legítima. **Desviación aprobada por el brief:** proyecto nuevo con el
  scaffolding oficial.
- Framework: `RetroPortingToolKit/psxrecomp` @ `31df2e1e` con submódulos.
- Proyecto: `source/SoulBladeRecomp` (commit inicial `04a49cd`), `psxrecomp` como submódulo,
  `recomp-ui` omitido, netplay omitido, CI omitida.

## Fase 2 — Primera compilación reproducible (EN CURSO)

Hecho:
- `recompiler` configurado y compilado (Release, Ninja, clang 23.1.3) → 348/348 OK.
- Emisores en el proyecto (`build-recompiler`) → `psxrecomp-game`, `psxrecomp-bios` OK.
- `verify-disc` OK.
- `generate` OK: OpenBIOS recompilado + 59 shards del juego (`generated/`, 76 MB, 2.409.187 líneas,
  dispatch de 3994 entradas).
- `cmake -S . -B build-release` OK: OpenBIOS enlazado, juego enlazado, Vulkan detectado.

Pendiente inmediato:
- Enlazar `psx-runtime` y comprobar que el binario es ELF x86-64 nativo (`file`, `ldd`).
- Arranque en headless (`PSX_HEADLESS=1`) para ver si llega a ejecutar código del juego.

## Fase 3 — Adaptación a Linux

Hasta ahora no ha hecho falta parchear código: el framework soporta Linux y compila con
las herramientas del sistema. Única incidencia: el camino de “toolchain portable” del CLI
solo funciona en Windows (ver auditoría §8.2); se evita con `--no-toolchain-download`.

Riesgos previstos para Linux/Wayland:
- Ventana SDL3 en Wayland (se probará tanto nativo como XWayland si hiciera falta).
- Audio vía PipeWire/ALSA a través de SDL3.
- Mando: “Generic X-Box pad” por SDL; el framework documenta `input.ini` y soporte XInput/SDL.

## Fase 4 — Generación del juego y ejecución

- El código generado cubre **solo el EXE de arranque**. Soul Blade carga overlays desde
  `SOUL.BNS` (25,8 MB), `SOULOVL.BNS` (4,7 MB) y `SOULSYS.BNS` (620 KB). El runtime tiene
  dos capas: captura de overlays en runtime (`overlay_captures.json`) y compilación estática
  (`generated/overlays.c`), además de la vía dinámica.
- Plan: arrancar y observar hasta dónde llega; si se queda en el intérprete dentro de un
  overlay, capturar y compilar los overlays con `tools/compile_overlays.py`.
- Seeds: 1453 iniciales del EXE. Se ampliarán con descubrimiento en runtime si aparecen
  “misses” (funciones ejecutadas que no estaban en la tabla).

## Fase 5 — Pruebas funcionales (COMPLETA salvo referencia PS1)

Ejecutadas y con evidencia: arranque y detección del disco, menú y navegación, inicio de
combate, movimiento y ataques, audio (con experimento de control), guardado y carga en
memory card, cierre ordenado y segundo arranque. Detalle y evidencias en `tests/PRUEBAS.md`.

Pendiente: comparación con una referencia de PlayStation 1 (no hay emulador de referencia
instalado ni se ha ejecutado el disco en uno) y sesión larga cronometrada.

## Fase 6 — Calidad

Solo tras ejecución funcional: escalado HD, comparación con referencia PS1, glitches de agua
(citados en la documentación pública del proyecto original), rendimiento.

## Fase 7 — Entrega

Instrucciones de compilación/ejecución, revisiones exactas, logs, informe de pruebas,
limitaciones y procedimiento de limpieza. Sin publicar nada ni incluir BIN/CUE/PSV/BIOS.
