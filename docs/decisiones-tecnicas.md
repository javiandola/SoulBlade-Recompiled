# Decisiones técnicas

## D1 — Framework: PSXRecomp de RetroPortingToolKit, HEAD actual

- **Elegido:** `https://github.com/RetroPortingToolKit/psxrecomp` en
  `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` (`nightly-870-g31df2e1e`, 2026-10-22).
- **Alternativa considerada:** el pin del proyecto WWF del mismo autor
  (`20ae6db9`, 2026-08-25) o el fork `fabioap-cpu/psxrecomp`.
- **Razón:** el pin de agosto es ancestro de la HEAD (verificado con
  `git merge-base --is-ancestor`), así que la HEAD contiene todo lo del pin más las
  correcciones posteriores, incluido soporte Linux más reciente. El fork del autor no aporta
  commits propios (mismo linaje; su última subida es de 2026-09-06).
- **Consecuencia:** si aparece una regresión específica, se puede bajar a `20ae6db9` sin
  cambiar de proyecto (`git -C psxrecomp checkout 20ae6db9`).

## D2 — Proyecto de juego propio en lugar de esperar al repositorio del autor

- El repo `fabioap-cpu/SoulBlade_Recomp` no existe (404 en API y en `git ls-remote`; recomp.fyi
  lo marca como “repo missing”). No hay copia pública legítima.
- Se generó `source/SoulBladeRecomp` con el scaffolding oficial, que produce `game.toml`,
  seeds, símbolos, `.gitignore` y el esqueleto de build.
- **Riesgo asumido:** el trabajo de seeds y overlays del autor no se puede reutilizar.

## D3 — Sin `recomp-ui`, sin netplay, sin CI

- `recomp-ui` (lanzador) no es necesario para el objetivo y añade un submódulo con interfaz
  gráfica que hay que compilar aparte.
- Netplay: el dump es de una sola pista y las puertas multi-pista lo rechazarían; además no
  aporta al hito (partida local).
- CI: no se publica nada, así que no procede.

## D4 — Herramientas del sistema en vez del “toolchain portable”

- El CLI de psxrecomp intenta descargar un pack `cmake-clang-v1` y activarlo. En Linux
  `activate_embedded_toolchain()` **siempre devuelve False** (guardado por
  `if sys.platform != "win32"`), pero el flujo de `generate` interpreta que la descarga tuvo
  éxito y aborta con *“Toolchain ensure succeeded but bin/ is not usable for emitters”*.
- **Solución:** `generate --no-toolchain-download` fuerza la rama “usar cmake/ninja del PATH”.
  No se ha modificado el framework.
- Herramientas usadas: cmake 4.4.4, ninja 1.13.2, clang 23.1.3 para emisores (decide el propio
  CLI) y gcc 16.2.1 por defecto para el runtime.

## D5 — Estándar C++ fijado a 17

- Con GCC 16 el runtime heredaba el estándar por defecto del compilador, que en esta versión
  interpreta `u8""` como `char8_t` (C++20). Eso rompe `gpu_hd_textures.cpp` y
  `duckstation_texture_pack.cpp` (`std::u8string` no convierte a `std::string`).
- `psxrecomp/runtime/CMakeLists.txt` fija `CMAKE_CXX_STANDARD 17`, pero el camino de proyecto
  de juego (`runtime.cmake` vía `psxrecomp_add_game_runtime`) no lo hace.
- **Solución:** configurar con `-DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON`.
  Es exactamente el estándar que documenta el framework (C99 + C++17).

## D6 — Disco: se usa el CUE original por ruta absoluta

- `game.toml` → `[game] disc = "<project>/Soul Blade V1.1/Soul Blade (v1.1).cue"`.
- No se copia el BIN de 527 MB dentro del proyecto: el scaffolding guarda solo el boot EXE
  (`disc/SLUS_002.40`, 1 MB) y trabaja sobre el original en modo lectura.
- Los originales no se tocan; `disc/`, `*.bin`, `*.cue`, `saves/`, `prepared_disc/` están en
  `.gitignore`.

## D7 — Ningún paquete instalado en el sistema

- Todo lo necesario estaba presente (compiladores, SDL3 3.4.18, Vulkan, Mesa, Python).
- Registro de instalaciones: ninguna. Si más adelante hiciera falta algo, se anotará aquí con
  el motivo.

## D8 — Las memory cards viven en el proyecto, no en el directorio de build

- `game.toml` declara `[runtime] memcard_dir = "saves"`, y el runtime resuelve esa ruta contra
  la **raíz del proyecto**, no contra el directorio de compilación: las tarjetas reales son
  `source/SoulBladeRecomp/saves/card1.mcd` y `card2.mcd` (131.072 B, formateadas al arrancar).
- Consecuencia práctica: `build-release/` y `build-debug/` **comparten** tarjeta. Sirve para
  comprobar que un guardado hecho en una build se carga en la otra, pero impide tener dos
  instancias guardando a la vez sin pisarse.
- Los `.mcd` están excluidos por `.gitignore` (son datos del juego del usuario).

## D9 — Estándar de los scripts: bash, no fish

- `build.sh` y `run.sh` son bash con `set -euo pipefail` y rutas entrecomilladas (el workspace
  tiene espacios en «Proyecto Soul Blade» y «Soul Blade V1.1»).
- `run.sh` hace `cd` al directorio de build antes de `exec` porque el runtime resuelve
  `game.toml`, `saves/`, `cache/` y las capturas relativas contra el cwd.

## D10 — El mando nunca se abría: causa raíz y corrección por configuración

**Síntoma.** SDL ve el mando y sus pulsaciones (comprobado con `tests/diagnostico/sdlprobe.c`),
pero el juego no reacciona a nada. `pad_status` devuelve `0xFFFF` de forma constante aunque se
pulsen todos los botones.

**Causa raíz.** En `runtime/src/main.cpp` el dispositivo por defecto de cada asiento se elige
así:

```c
#if defined(PSX_DEBUG_TOOLS)
    player_device[i] = (i == 0) ? "auto" : "none";      /* primer mando SDL */
#else
    player_device[i] = (i == 0) ? "keyboard" : "none";  /* teclado */
#endif
```

`PSX_DEBUG_TOOLS` **no lo define ninguna de las dos builds** de este proyecto: la release
define `PSX_NO_DEBUG_TOOLS=1` (226 apariciones en `build-release/build.ninja`) y la debug no
define ninguno de los dos. El resto del framework usa la convención contraria
(`#ifndef PSX_NO_DEBUG_TOOLS`), así que este `#if` está invertido. Resultado: en ambas builds
el asiento 1 queda en **teclado** y `open_player()` no llega a abrir el mando.

**Corrección aplicada (mínima, sin tocar el framework).** En `game.toml`:

```toml
[controller]
p1_device = "auto"
```

`p1_device`…`p5_device` son claves soportadas por `config_loader.cpp` y aceptan `none`,
`keyboard`, `auto`/`gamepad` (primer mando libre) o un GUID de SDL.

**Verificación.** Tras reconstruir y relanzar, `pad_status` registra las palabras reales del
mando: `0xFFEF` arriba, `0xFFDF` derecha, `0xFF7F` izquierda, `0xBFFF` Cross, `0xDFFF` Círculo,
`0xEFFF` Triángulo. Con el mando el usuario navegó de attract a la selección 1P y jugó una
partida completa (GAME OVER, Mitsuguri vs Li Long).

**Pendiente de reportar al proyecto:** el `#if defined(PSX_DEBUG_TOOLS)` de `main.cpp` debería
ser `#ifndef PSX_NO_DEBUG_TOOLS`. No se ha parcheado el submódulo.

### Correspondencia de botones (Xbox → PlayStation)

`input.ini` mapea **por posición física**, que es lo correcto para un mando tipo Xbox:

| GameSir (Xbox) | Posición | Botón PSX que recibe | En Soul Blade |
|---|---|---|---|
| A | sur | Cross (×) | cancelar |
| B | este | Circle (○) | **aceptar / confirmar** |
| X | oeste | Square (□) | ataque |
| Y | norte | Triangle (△) | ataque |
| START | — | Start | menú / pausa 1P |
| BACK | — | Select | — |

Por eso en este juego se confirma con **B**: Soul Blade usa ○ para aceptar (convención
japonesa), y ○ está en la posición este, que en un mando Xbox es B.

## D11. El bloque de 0x10D00 se trata con fragmentos interiores, no como funciones

El bloque copiado en `0x80010D00` (768 B, origen `0x80010F60` de la propia imagen del EXE) contiene
tres rutinas de matemáticas GTE con sus `jr $ra` en `+0xAC`, `+0x2AC` y `+0x2B4`. Las cuatro
direcciones que la instrumentación ve ejecutar (`0x10D3C`, `0x10D94`, `0x10D9C`, `0x10DAC`) son
puntos **interiores**: dos `div`, un `bgez` hacia atrás y un retorno.

Decisión: no declararlas como cabeceras de función. Se usa el mecanismo documentado de esta
revisión (`compile_overlays.py --force-interior`, «isolated interior fragments are per (entry,
image)»), que crea una isla por entrada y por imagen y deja el gate CRC del despachador decidir. No
se modifica el framework.

## D12. Los checksums de tarjeta no se validan al escribir (fallo conocido)

Hallazgo (ver T18): el guardado producido por el port deja 11 frames del bloque 1 con el byte 0x7F
incorrecto. La ruta de escritura del runtime (`memcard_write_sector`) solo copia; el unico punto que
calcula el XOR es `memcard_format` al formatear una tarjeta en blanco.

Decisiones:

- **No** se reescriben los ficheros `.mcd` para "arreglarlos": enmascararia el fallo y falsearia la
  evidencia.
- **No** se añade validacion al runtime por ahora: rechazar escrituras con checksum malo convertiria
  un fallo silencioso en un guardado que falla en el juego, y hay que localizar antes **quien**
  produce el byte incorrecto (el BIOS LLE recompilado o el reparto de frames en SIO). Convertirlo en
  error sin diagnostico empeoraria la situacion.
- Queda como **fallo conocido** con herramienta de comprobacion (`tests/diagnostico/check_mcd.py`) y
  se anota como requisito para la fase de distribucion: los guardados de la AppImage deben pasar ese
  chequeo antes de darlos por buenos.

## D13. Validación opt-in del checksum interno de frame (parche local del framework)

Añadido en `psxrecomp/runtime/src/sio.c` (copia del framework que usa el proyecto, commit local
`66cbc3a2` sobre `31df2e1e`):

- `PSX_MC_WRITE_LOG=1` → traza por escritura: sector, `0x7F` almacenado, XOR `0x00..0x7E`,
  checksum de transacción enviado/esperado y si cuadra. Sin contenidos.
- `PSX_MC_STRICT_FRAME_CHK=1` → rechaza con end byte `4Eh` los frames cuyo checksum interno no
  cuadra, como una tarjeta real. **Por defecto desactivado.**

Razón de que sea opt-in y no comportamiento por defecto: activarlo cambiaría un fallo latente
(el guardado actual tiene frames incoherentes) en un guardado que falla en el juego. Primero hay
que saber quién produce el byte malo; el modo estricto es la herramienta para averiguarlo, no la
corrección.

Evidencia de que no rompe lo normal: con estricto ON, la escritura de arranque del sector 63
(checksum interno correcto) se acepta igual y el juego arranca sin errores. Cubierto por
`test_frame_internal_checksum_modes` (7 comprobaciones).

## D14. Corrección: el checksum interno del frame NO está demostrado como defecto

Revisión de D12 y T18 con evidencia nueva del propio framework.

Hechos comprobados:

| tarjeta | frames con `0x7F` incoherente |
|---|---|
| `saves/card1.mcd` (guardado de Soul Blade) | 11 (64-74) |
| `tests/referencias/card1-tras-guardado.mcd` | 12 (63-74) |
| `psxrecomp/runtime/tests/fixtures/memcards/card1.mcd` (**fixture del framework**) | 3 (64, 128, 192) |
| `psxrecomp/runtime/tests/fixtures/memcards/card2.mcd` (**fixture del framework**) | 3 (64, 128, 192) |
| `saves/card2.mcd` (vacía) | 0 |
| frames 0 y 63 de `card1.mcd` (cabecera y write-test) | **válidos** |

Interpretación corregida:

- El campo `0x7F` se cumple en los sectores de **estructura** (cabecera y directorio), que produce
  el formateador o el BIOS.
- En los sectores de **datos** nadie lo mantiene: ni el juego, ni el formateador del framework, ni
  sus fixtures. Si la tarjeta real lo validara al escribir, el fixture del framework estaría mal y
  el guardado de un juego comercial fallaría en hardware, lo que no encaja.
- Nuestro runtime valida el **checksum de transacción** (probado: `chk_ok=1`, y rechaza con `4Eh`
  si no cuadra) y almacena los 128 B verbatim (probado).

Conclusión: **no hay defecto demostrado**. Lo que hay es una diferencia respecto a la convención
del formato, compartida con el propio framework. Se retira la etiqueta de «fallo detectado» de T18.

Queda como herramienta (`check_mcd.py`) y como modo estricto opt-in (`PSX_MC_STRICT_FRAME_CHK`) por
si alguna vez aparece una tarjeta que se comporte distinto. Lo que **sí** se mantiene como requisito
de la fase de distribución: pasar `check_mcd.py` sobre una tarjeta generada por el paquete y
documentar el resultado, sin «repararla».

## D15. Escalado interno: 1080p y 4K sostienen 1,00x; no se activa por defecto todavía

Medido con `[video] internal_resolution` + `supersampling` (build debug, telemetría de FPS), en las
escenas alcanzables sin navegar:

| configuración | factor pedido | FPS observado |
|---|---|---|
| nativa (sin claves) | 1x | 59,9–60,4 (1,00x) — T17/T22 |
| `internal_resolution = "1080p"`, `supersampling = 2` | **5x** | 59,9 (1,00x) |
| `internal_resolution = "4k"`, `supersampling = 2` | **9x** | 59,9 (1,00x), min 59,5 |

Lectura: la RX 7700 XT tiene margen de sobra para el escalado; no hay coste medible a 1080p ni a 4K
en estas escenas (intro/FMV, que son ligeras).

Por qué **no** se activa por defecto en `game.toml` todavía:

1. La captura del servidor de depuración es el framebuffer de la consola (**256x240**), no la
   presentación reescalada: no permite verificar visualmente la mejora. Hace falta una captura de
   escritorio (Spectacle) o validación a ojo.
2. Las escenas medidas son ligeras; falta medir un combate con geometría.
3. Cambiar la resolución por defecto afecta a todos los usuarios del paquete y debe decidirse con
   evidencia visual, no solo con FPS.

Quedan como configuraciones de prueba reproducibles: `game-hd-test.toml` (1080p) y
`game-4k-test.toml` (4K).

### Matiz sobre D15 (corrección de alcance de la medida)

En D15 escribí que las escenas medidas eran «intro/FMV, ligeras». Precisión: el bucle de attract de
Soul Blade **incluye demos de combate** (verificado en capturas de esta sesión: escenas de lucha con
«PRESS START BUTTON»). Por tanto el soak de 7:24 con 1080p —mínimo 59,5 fps, media 59,92— cubrió
varias de esas demos, no solo la intro.

Lo que sigue sin medir: un combate **controlado por el jugador** (con efectos disparados por
entrada) y escenas con streaming de CD intenso. La conclusión práctica no cambia (1080p sostiene
1,00x), pero el alcance de la evidencia es mayor de lo que dije.

## D16. Estándar C del framework de pruebas: C11, no C99

`runtime/CMakeLists.txt` fijaba `CMAKE_C_STANDARD 99` globalmente mientras el propio runtime pide
`c_std_11` (sus comentarios indican que `audio_trace.c` usa atómicos C11). Con C99, `dma.c` no ve
`timespec_get`/`TIME_UTC` y los targets de prueba que lo compilan directamente no construían:
**214 de 279 pruebas quedaban «Not Run»**.

Cambiado a `CMAKE_C_STANDARD 11`. El estándar efectivo del runtime no cambia (ya pedía C11); lo que
cambia es que los targets de prueba pueden compilar. No afecta a las builds del juego, que fijan su
propio estándar por target.

## D17. Parches locales para poder empaquetar como AppImage

El runtime daba por hecho un directorio escribible junto al ejecutable y que «directorio del
ejecutable» y «directorio del paquete» eran lo mismo. Dentro de una AppImage ninguna de las dos cosas
se cumple (el AppDir se monta en solo lectura y `$APPIMAGE` apunta al fichero). Tres parches locales,
todos con el mismo criterio: **separar recursos de solo lectura de estado escribible**.

1. `bundle_dir_from_argv()` (main.cpp): directorio real del binario vía `/proc/self/exe`, sin pasar por
   `$APPIMAGE`. Se usa para el BIOS incluido, `mods/` y `overlay_toolchain/`. `exe_dir_from_argv()`
   sigue prefiriendo `$APPIMAGE` para ajustes y tarjetas (ancla escribible junto al paquete).
2. `resolve_bios_path()` (main.cpp): recorre los dos anclajes en vez de solo el escribible.
3. `save_state()` (mod_packages.cpp): con `EROFS`/`EACCES` avisa y continúa en vez de impedir el
   arranque. Sin esto la AppImage se cerraba con «cannot launch with selected mods».

Ninguno cambia el comportamiento en instalaciones normales (directorio escribible): el primero y el
segundo solo añaden una ruta de búsqueda, y el tercero solo actúa cuando la escritura es imposible.

## D18. La AppImage deduce la pantalla y deja de exportar LD_LIBRARY_PATH

Dos defectos del lanzador descubiertos al probar en Bazzite:

1. **Sin `WAYLAND_DISPLAY`/`DISPLAY` SDL3 no arranca.** Cualquier lanzamiento por SSH, por servicio o
   desde un lanzador que no hereda el entorno del escritorio terminaba en
   `SDL_Init failed: No available video device`, con el resto del arranque correcto. El AppRun ahora
   busca `wayland-*` y `gamescope-*` en `XDG_RUNTIME_DIR` (Bazzite usa Gaming Mode: el socket es
   `gamescope-0`, no `wayland-0`) y, si no hay, cae a Xwayland con `DISPLAY=:0`.

2. **`LD_LIBRARY_PATH` era redundante y nocivo.** linuxdeploy fija `RUNPATH=$ORIGIN/../lib` en el
   ejecutable, así que las bibliotecas empaquetadas se resuelven solas. Exportarlo además imponía
   nuestro `libcrypto` a los procesos hijos: en Bazzite, `zenity` moría con
   `version OPENSSL_3.0.1 not found`. Eliminado; verificado sin regresión en ambos equipos.
