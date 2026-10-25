# Limpieza final y estado de conservación

Fecha: 2026-10-25. El proyecto se da por terminado: este documento registra qué se ha conservado,
qué se ha eliminado y con qué evidencia se puede reconstruir el paquete.

## Artefacto final

`package/out/SoulBlade-Recompiled-x86_64.AppImage`

- 371.300.856 B
- sha256 `65b195b65d0475530bc28327a0af84f0bf91fac6d540b5bcb86cfc46abdde01d`
- Verificado con `package/build-appimage.sh --verify-only` **antes y después** de la limpieza: OK.
- Idéntico al instalado en el segundo equipo (Bazzite).

## Conservado en CachyOS (entradas y salidas necesarias)

| elemento | por qué |
|---|---|
| `source/SoulBladeRecomp/generated/` (62 ficheros, versionados) | código MIPS recompilado; sin él habría que regenerar desde el disco |
| `source/SoulBladeRecomp/build-release/` | el script de empaquetado copia de aquí el ejecutable y el manifiesto |
| `source/SoulBladeRecomp/build-recompiler/` | binario del recompilador, por si hay que regenerar código |
| `source/SoulBladeRecomp/psxrecomp/` | framework con los parches de la versión final (commits `daa85f7a`, `c2165c73`, `25899d51`) |
| `source/psxrecomp/` | clon de referencia del framework (revisión `31df2e1e`), sin su árbol de build |
| `package/AppRun`, `build-appimage.sh`, `.desktop`, icono | flujo de empaquetado |
| `docs/`, `tests/` | decisiones, pruebas y herramientas de diagnóstico |
| `Soul Blade V1.1/` | originales del usuario (BIN, CUE y PSV), intactos |
| `~/.cache/recomp-appimage-tools` (33 MB) | `linuxdeploy` y `appimagetool` fijados, evita redescargar |

## Eliminado (2.378 MB)

| ruta | tamaño | motivo |
|---|---:|---|
| `build-debug/` | 477 MB | build de depuración; no interviene en la release |
| `build-static-debug/` | 473 MB | experimento estático descartado (§16-18 de `overlays-aot.md`) |
| `build-static/` | 115 MB | idem, versión release |
| `psxrecomp/runtime/build-tests/` | 676 MB | árbol de pruebas del framework (se regenera con cmake) |
| `package/payload/` | 542 MB | staging que `build-appimage.sh` regenera en cada ejecución |
| `source/psxrecomp/recompiler/build/` | 93 MB | build del clon de referencia |
| `build-dev/` | 2 MB | caché de compilación de overlays |
| `logs/*.log` (73 ficheros), `package/*.log`, `out/input.ini` | ~3,5 MB | trazas de sesiones concluidas; conclusiones en `docs/` y `tests/PRUEBAS.md` |

Conservados a propósito por no poder demostrar que sobran: `static-overlays/` (568 KB, artefactos del
experimento estático documentado en `docs/overlays-aot.md`) y `logs/*.md` (notas de los turnos).

## Reconstrucción

```
cd source/SoulBladeRecomp && ninja -C build-release psx-runtime -j 12
cd ../.. && package/build-appimage.sh          # empaqueta y autovalida
package/build-appimage.sh --verify-only        # solo verifica el artefacto
```

## Reconstrucción ejecutada (no solo comprobada)

Tras la limpieza se ejecutó una compilación **desde cero** en un directorio temporal
(`cmake -S . -B /tmp/rebuild-check -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17`
seguido de `ninja psx-runtime`): configure correcto, 381 pasos, binario de 40.341.264 B. Ese binario
se ejecutó y alcanzó `disc region NTSC-U (serial SLUS-00240)` y **59,9 fps**. El binario no es
byte-idéntico al de `build-release/` (difieren el build-id y las rutas incrustadas), lo que es normal;
lo relevante es que la cadena fuente → binario → ejecución funciona con lo conservado. El directorio
temporal se borró después.

## Nota sobre el historial de Git

Un `git add -A` anterior versionó `package/debug-payload/`, incluido un binario de depuración de
160 MB. En esta limpieza se han retirado del índice y se ha añadido la ruta a `.gitignore`, pero el
blob **sigue en el historial** (el `.git` ocupa 75 MB). No se ha reescrito el historial: no era el
objetivo de la tarea y habría implicado reescribir commits locales.
