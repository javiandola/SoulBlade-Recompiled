# AppImage de Soul Blade Recompiled

Artefacto para uso personal en CachyOS y Bazzite (x86-64, gráficos AMD).
Contiene el ejecutable nativo, el runtime, el BIOS incluido (OpenBIOS + aviso MIT) y una
**copia del disco original** (BIN + CUE) para que la aplicación sea autosuficiente.

- Fichero: `package/out/SoulBlade-Recompiled-x86_64.AppImage`
- Tamano: 371.300.856 B (354 MiB)
- SHA-256: se guarda junto al artefacto en `SoulBlade-Recompiled-x86_64.AppImage.sha256`
- Tipo: AppImage tipo 2 (squashfs + runtime FUSE), construida con `appimagetool` 1.9.1 y
  `linuxdeploy` 1-alpha-20251107-1, ambos descargados con SHA-256 verificado.

## Ejecutar

```bash
chmod +x SoulBlade-Recompiled-x86_64.AppImage
./SoulBlade-Recompiled-x86_64.AppImage
```

También funciona con doble clic desde el gestor de archivos (el `.desktop` va dentro), y desde
cualquier directorio, ruta con espacios o a través de un enlace simbolico al propio `.AppImage`.

Registros: la salida del runtime va a la consola. Para telemetria de FPS:

```bash
PSX_FPS_TELEMETRY=1 ./SoulBlade-Recompiled-x86_64.AppImage
```

## Datos escribibles

Nada se escribe dentro de la AppImage (se monta en solo lectura). Todo el estado vive en:

| Ruta | Contenido |
|---|---|
| `${XDG_DATA_HOME:-~/.local/share}/soulblade/game.toml` | configuracion de partida (se copia del paquete la primera vez y luego se conserva) |
| `${XDG_DATA_HOME:-~/.local/share}/soulblade/saves/` | tarjetas de memoria (`memcard_dir = "saves"`, relativo al `game.toml`) |
| `${XDG_DATA_HOME:-~/.local/share}/soulblade/overlay_captures.json` | almacen de capturas de overlays (`PSX_OVERLAY_CAPTURES`) |
| junto al `.AppImage` | `settings.toml`, `input.ini` y `mods/state.toml` si el runtime los crea (asi lo decide el framework: ancla escribible = directorio del paquete) |

Para reiniciar de cero: borrar el directorio `soulblade` de arriba (las tarjetas incluidas).

## Estructura del paquete

```
AppRun                          lanzador (ver abajo)
soulblade.desktop, soulblade.png, .DirIcon
usr/bin/SoulBlade_Recompiled    ELF nativo (Release)
usr/bin/SoulBlade_Recompiled.execution.json
usr/bin/bios -> ../share/soulblade/bios      (el runtime resuelve el BIOS junto a argv[0])
usr/bin/assets -> ../share/soulblade/assets  (SDL resuelve sus recursos desde el ELF real)
usr/lib/*.so                    bibliotecas incluidas (6)
usr/share/soulblade/
  disc/Soul Blade (v1.1).bin    copia identica al original (sha1 e1a48d3e...)
  disc/Soul Blade (v1.1).cue    copia identica al original (md5 a4567ab2...)
  bios/openbios.bin             BIOS OpenBIOS
  bios/OpenBIOS.LICENSE         aviso MIT
  game.toml, game_options.toml  configuracion de referencia
  assets/psxrecomp.png          icono de la ventana
```

El CUE original referencia el BIN por nombre relativo (`FILE "Soul Blade (v1.1).bin" BINARY`).
Ambos se copian **en el mismo directorio** y se verifica por hash: sin enlaces que apunten fuera.

## AppRun

1. Localiza el AppDir con `$APPDIR` (lo define el runtime) o, si no existe, resolviendo `$0` con
   `readlink -f`, de modo que funciona por enlace, desde otra ruta y con espacios.
2. Fija los datos escribibles en `${XDG_DATA_HOME:-$HOME/.local/share}/soulblade`.
3. Anade solo `usr/lib` a `LD_LIBRARY_PATH`; el resto (Mesa, X11/Wayland, glibc) lo pone el sistema.
4. Lanza:

```sh
exec "$EXE" --game "$DATA/game.toml" --disc "$SHARE/disc/Soul Blade (v1.1).cue" --bios "$SHARE/bios/openbios.bin" "$@"
```

`--disc` es **obligatorio**: la clave `disc` de `game.toml` solo la usa el recompilador, no el
runtime (comprobado ejecutando la release; ver `docs/requisitos-empaquetado.md` seccion 8). Los
argumentos extra del usuario se pasan tal cual al final, y el codigo de salida es el del juego.

## Dependencias

Incluidas (6): `libSDL3.so.0`, `libcrypto.so.3`, `libzstd.so.1`, `libbrotlicommon.so.1`,
`libbrotlidec.so.1`, `libbrotlienc.so.1`.

Del sistema anfitrion: glibc (**suelo GLIBC_2.38**), `libstdc++` (necesita hasta
**GLIBCXX_3.4.30**, GCC 11), `libgcc_s`, `libm`, `libpthread`, `libdl`, `librt`, `libGL`, `libEGL`,
`libX11`/`libwayland` y el driver grafico (Mesa RADV/AMD). No se empaqueta nada de eso a proposito:
incluir Mesa o GL rompe el driver del anfitrion.

Compatibilidad razonada:

| Sistema | glibc | libstdc++ | Estado |
|---|---|---|---|
| CachyOS (rolling) | > 2.38 | GLIBCXX 3.4.36 | **probado** (construido y ejecutado aqui) |
| Bazzite / Fedora 44 | 2.43 | GLIBCXX 3.4.34+ | **probado** (59,6-60,4 fps en Steam Gaming Mode) |

Ambos sistemas se han ejecutado con el mismo artefacto. Lo unico que podria fallar en un sistema mas
antiguo es una version de `libstdc++` anterior a GLIBCXX_3.4.30 (Fedora 34 o anterior).

## Reconstruir

```bash
cd source/SoulBladeRecomp
ninja -C build-release psx-runtime -j 12
cd ../..
package/build-appimage.sh            # o: DISC_DIR="/ruta/alternativa" package/build-appimage.sh
package/build-appimage.sh --verify-only   # solo verifica el artefacto existente
```

El script prepara el payload desde cero (ejecutable + manifiesto + BIOS + aviso + `game.toml` +
`game_options.toml` + assets + copia del disco), **verifica por hash** las copias contra el original,
neutraliza la ruta absoluta de `disc` en el `game.toml` empaquetado, empaqueta y luego valida el
resultado (AppRun ejecutable, BIOS resoluble, BIN/CUE identicos, ausencia de rutas
`~`, cero bibliotecas sin resolver).

La primera ejecucion necesita red: el empaquetador descarga `linuxdeploy` y `appimagetool` en
`~/.cache/recomp-appimage-tools` verificando sus SHA-256.

## Pruebas realizadas (ver `tests/PRUEBAS.md`, T28-T32)

- Arranque desde `/tmp` con ruta con espacios y a traves de un enlace al `.AppImage`: OK.
- BIOS cargado desde el montaje, disco detectado como NTSC-U `SLUS-00240`, 59,9-60,4 fps.
- Capturas reales de pantalla: ventana "SoulBlade Recompiled" con la intro animada.
- **Independencia total**: con el directorio del proyecto oculto (`bwrap --tmpfs`), arranca y corre a
  60,4 fps.
- Hashes del BIN/CUE empaquetados identicos a los originales; originales sin tocar.
- No hay rutas `~` en `AppRun`, `game.toml` ni `.desktop`.

## Limitaciones conocidas

1. **Guardado manual no validado**: se navegaria por menus y se descarto como requisito por
   indicacion expresa del usuario. No se registra como prueba superada. El diseño de rutas escribe
   fuera del paquete, asi que no hay motivo para esperar fallos por solo-lectura.
2. **Mods**: el paquete no incluye `mods/`. El runtime intenta crear `mods/` junto al ejecutable y,
   en solo lectura, avisa (`mods state not persisted`) y continua. Es un parche local al framework
   (ver `docs/decisiones-tecnicas.md` D17); sin el, el juego no arrancaba desde la AppImage.
3. **`settings.toml`** se crea, si el juego lo guarda, junto al `.AppImage`, no en XDG: el framework
   no admite ruta de configuracion por variable.
4. Sin overlay cache ni conjunto estatico: medido, la cobertura nativa no cambia el rendimiento
   (T26), y el conjunto estatico con `0x96000` congelaba el video.
5. No probado en Bazzite ni con doble clic real sobre el escritorio (se ejecuto desde terminal y por
   enlace; el `.desktop` esta incluido y validado en formato).

## Licencias y datos

Se incluye `bios/OpenBIOS.LICENSE` (MIT). El disco del juego es una copia privada del original del
usuario; **este paquete no es redistribuible** y no se ha publicado en ningun sitio.

## 9. Bazzite: causa raíz del fallo `SDL_Init failed: No available video device`

**No era la aplicación, ni Mesa, ni Vulkan: era el entorno de lanzamiento.** El intento se hizo por
SSH, y una sesión SSH no hereda `WAYLAND_DISPLAY` ni `DISPLAY`. SDL3, sin ninguno de los dos, no
encuentra backend de vídeo y aborta. El resto del arranque (BIOS, disco, runtime) ya funcionaba: es
exactamente lo que muestra el log, porque la carga del disco ocurre antes de crear la ventana.

Datos del equipo: Bazzite (Fedora 44), kernel 7.2.9, usuario sin privilegios (uid 1000), **sesión de Steam
Gaming Mode** (`gamescope-session-plus ogui-steam`), no Plasma. Consecuencias:

- El compositor expone `gamescope-0` en `/run/user/1000`; **no hay `wayland-0`**.
- Hay Xwayland (`/tmp/.X11-unix/X0` y `X1`), así que X11 también sirve de respaldo.
- `spectacle` no funciona en Gaming Mode (no hay kwin) y `grim` no está instalado: la captura de
  pantalla se hizo con el servidor de depuración del runtime, no con herramientas del escritorio.

### Corrección aplicada (AppRun)

Si no llegan `WAYLAND_DISPLAY` ni `DISPLAY`, el lanzador deduce el compositor del propio usuario:
primero busca `wayland-*` y `gamescope-*` en `XDG_RUNTIME_DIR`, y si no hay, cae a `DISPLAY=:0` con
Xwayland. No toca la configuración de la sesión ni necesita privilegios.

### Segundo defecto encontrado y corregido: `LD_LIBRARY_PATH`

El AppRun exportaba `LD_LIBRARY_PATH=$APPDIR/usr/lib`. Es innecesario (linuxdeploy ya fija
`RUNPATH=$ORIGIN/../lib` en el ejecutable) y **contaminaba los procesos hijos**: en Bazzite, un
`zenity` lanzado por el runtime cargaba nuestro `libcrypto` y fallaba con
`version OPENSSL_3.0.1 not found (required by /usr/lib64/libssl.so.3)`. Eliminado: el ejecutable
resuelve sus bibliotecas por RUNPATH y los hijos usan las del sistema. Verificado sin regresión en
CachyOS y en Bazzite (60 fps en ambos).

## 10. Verificación en Bazzite (2026-10-25)

Instalado en el directorio del juego, sha256 `65b195b65d0475530bc28327a0af84f0bf91fac6d540b5bcb86cfc46abdde01d`
(el artefacto original se conserva como `.AppImage.orig`, sha256 `b79621c1…`).

| prueba | resultado |
|---|---|
| Hash del artefacto en destino | idéntico al construido |
| Lanzado por SSH **sin** `WAYLAND_DISPLAY`/`DISPLAY` | arranca: BIOS del paquete, `NTSC-U SLUS-00240`, **59,6-60,4 fps** |
| Lanzado desde otro directorio de trabajo (`/tmp`) como unidad systemd de usuario | idem, 60 fps |
| Vía Wayland explícita (`WAYLAND_DISPLAY=gamescope-0`) | 59,9-60,1 fps |
| Vía X11 (`DISPLAY=:0`, Xwayland) | arranca y carga el disco |
| Menú interactivo | capturado; el cursor responde (ARCADE MODE resaltado) |
| Selección de personaje | capturada con marcador **1P** (criterio del proyecto: pantalla de jugador, no attract) |
| Pantalla VS | capturada: `STAGE 1 — MITSURUGI VS TAKI` |
| Combate en pantalla | capturado: dos luchadores con armas, escena animada (md5 distintos entre capturas) |
| Audio | `pactl` muestra cliente `application.name = "SoulBlade_Recompiled"` activo durante la partida |
| Datos escribibles | `~/.local/share/soulblade/{game.toml,saves/card1.mcd,card2.mcd}` |
| Cierre | `systemctl --user stop` deja la unidad inactiva sin errores |

### Limitaciones de esta verificación

1. **No se llegó al estado 6/7 del proyecto** (combate con HUD/temporizador y menú `1P PAUSE`). La
   navegación por inyección (`press`) alcanza el menú y la selección de personaje con marcador 1P,
   pero se queda en `PRESS 2P START` en la selección y el flujo acaba volviendo a la demo. Se ha
   probado también con `p2_device="none"` en un `XDG_DATA_HOME` aislado, sin conseguirlo. No se
   declara superado.
2. **Mandos no verificados**: en Bazzite no había ningún GameSir conectado durante la sesión (solo un
   receptor Logitech), así que no se pudo comprobar ni la detección ni el reparto 1P/2P en el paquete.
3. La captura se hace del framebuffer de consola (256x240); no hay captura de la ventana escalada.

## 11. Artefacto único para ambos equipos

**Sí, se mantiene una sola AppImage.** No hizo falta variante por distribución: el binario exige
glibc ≥ 2.38 y `GLIBCXX_3.4.30`, y Bazzite (Fedora 44) los supera con holgura. La diferencia entre
equipos era de *entorno de lanzamiento* (SSH y Gaming Mode), resuelta en el AppRun, no de paquete.
