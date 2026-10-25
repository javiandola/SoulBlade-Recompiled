# Lista reproducible de pruebas — Soul Blade (port nativo Linux)

Cada prueba indica: cómo se ejecuta, qué evidencia se recoge y su estado real.
Estados: **SUPERADA** (con evidencia enlazada) · **FALLIDA** · **NO EJECUTADA** · **BLOQUEADA**.

Preparación común:

```bash
cd "<project>"
./build.sh                 # build-release
./build.sh --debug         # variante con servidor de depuración (para inyectar entradas)
```

Todas las pruebas con entrada automatizada usan el servidor TCP de la variante debug:

```bash
D=source/SoulBladeRecomp/psxrecomp/tools/debug_client.py
./run.sh --debug &                                  # abre ventana y escucha en 127.0.0.1:4370
python3 $D screenshot                                # captura a build-debug/psx_screenshot.png
python3 $D press 0xFFF7 4                            # Start
python3 $D press 0xDFFF 4                            # Círculo (ACEPTAR)
python3 $D savestate                                 # guarda estado del emulador
python3 $D pause ; python3 $D continue               # congelar / reanudar
```

## Mapa de botones (determinado empíricamente)

| Botón | Word de pad | Evidencia |
|---|---|---|
| Start | `0xFFF7` | saca del attract al menú; con Select sale al título |
| Círculo | `0xDFFF` | **botón de aceptar** (confirma opción de menú y personaje) |
| Cross | `0xBFFF` | no confirma; comportamiento aún no determinado |
| Select+Start | `0xFFF6` | sale del combate al título |
| Arriba | `0xFFEF` | mueve el cursor de la lista (con envolvente) |
| Abajo | `0xFFBF` | mueve el cursor de la lista hacia abajo |

El word es activo a nivel bajo: bit a 0 = pulsado.

Navegación confirmada al combate (todo en una sola llamada, el menú caduca por inactividad
en pocos segundos):

```
Start → esperar 1,4 s → Abajo → esperar 0,35 s → Círculo   → selección de personaje
      → esperar 2,2 s → Círculo                             → combate
```

---

## T1. Compilación reproducible — SUPERADA

- `./build.sh` → exit 0, 6/6 objetivos, `ELF 64-bit LSB pie executable, x86-64`, 39 MB.
- Segunda ejecución incremental: 0,9 s, mismo BuildID `3dca9176…` (determinista).
- Evidencia: `logs/build-release.log`, `logs/build-release.log.configure`.

## T2. Binario nativo, no emulador ni Wine — SUPERADA

- `file build-release/SoulBlade_Recompiled` → ELF x86-64 PIE enlazado con SDL3, libGLX, libcrypto del sistema.
- `ldd` sin prefijos de Wine. Evidencia: salida de `ldd` en el informe de sesión.

## T3. Arranque y detecta el disco — SUPERADA

- `./run.sh --headless` → «loaded game config … (SoulBlade, SLUS-00240)», «disc region NTSC-U».
- `verify-disc` → exit 0.

## T4. BIOS y ejecución del código del juego — SUPERADA

- «bios_backend=LLE (recompiled BIOS) bios_boot=HLE», «executing from PC=0xBFC00000».
- Llega a la intro FMV con MDEC y al menú. Evidencia: capturas `sb_a.png`, `sb_b.png`.

## T5. Menú principal y navegación — SUPERADA

- Menú con EDGE MASTER MODE / OPTION / ARCADE MODE / VS / TEAM BATTLE / TIME ATTACK / SURVIVAL.
- El resaltado cambia con Arriba/Abajo: verificado por diff de píxeles restringido a la lista
  (x 178-464, y 116-176) entre `men_up.png` y `men_dn.png`.

## T6. Inicio de combate real — SUPERADA (corregida)

**Corrección importante:** las escenas de combate que se reportaron en la primera sesión
(`r3.png`, `a4.png`, `fight2.png`) eran compatibles con el **modo attract** del juego, que
reproduce peleas CPU vs CPU mientras espera START. No eran prueba de una partida del jugador.

La secuencia real, verificada pantalla a pantalla, es:

1. START desde el attract → menú principal (cursor en ARCADE MODE).
2. Círculo → «SELECT YOUR CHARACTER» con el rótulo **INSERT COIN** y sin marcador 1P.
3. **START** → inserta la moneda: aparece el marcador **1P** y «PRESS START+SELECT TO EXIT».
4. Círculo → confirma el personaje → pantalla **VS** (STAGE 1).
5. «BATTLE 1» → combate.

Evidencia: `P2_charselect.png` (INSERT COIN, sin 1P), `X2_fight.png`/`X3_pause.png`
(marcador 1P ya activo), `Z2_circle.png` (VS), `Z6_start.png` («BATTLE 1»).

Prueba de que la partida es del jugador: en `T1.png` aparece el menú **«1P PAUSE»**
(CANCEL / COMMAND / VOL / RESET) superpuesto a un combate en curso. Ese menú solo existe en
una partida de un jugador; en el attract no aparece.

## T7. Control del personaje — PARCIAL (con evidencia direccional)

Método: savestate del emulador (`savestate op=save|load slot=1`) para partir siempre del mismo
frame y comparación píxel a píxel de las capturas resultantes.

| Comparación | Píxeles distintos | Lectura |
|---|---|---|
| Neutro vs neutro (mismo estado, sin entrada) | **0** | el banco de pruebas es determinista y exacto |
| Neutro vs mantener IZQUIERDA 3 s | 53.327 | la entrada cambia el estado del juego |
| Neutro vs mantener DERECHA 3 s | 65.122 | idem, y distinto de izquierda |
| IZQUIERDA vs DERECHA | 41.321 | **la dirección importa** |

**Control negativo en el attract:** en una demostración automática, mantener IZQUIERDA y
mantener DERECHA produjo capturas **idénticas** (0 píxeles de diferencia). Es decir, en el
attract la cruceta no altera nada y en partida sí, y de forma dependiente de la dirección.

Limitación honesta: no he medido el desplazamiento del personaje en píxeles porque la cámara
sigue a los dos luchadores y zooma, de modo que la posición en pantalla no es una medida
directa. La prueba definitiva de «el personaje camina hacia donde pulso» queda pendiente de
la prueba física con mando, que el usuario puede validar de forma directa al jugar.

Pendiente también: qué botón corresponde a cada ataque (falta mapear Cuadrado/Triángulo/Cross
por separado) y el ataque con daño verificable.

## T8. Ritmo / velocidad — SUPERADA

- Cronómetro del juego 0'20"19 → 0'30"26 en 10 s de reloj de pared (build RelWithDebInfo,
  overlays interpretados). Evidencia: `t0c.png`, `t1c.png`.

## T9. Audio — SUPERADA (con control)

- Captura del monitor del sumidero (`parecord --device=…analog-stereo.monitor`) mientras el
  juego corre. Método validado con un tono de control (440 Hz, volumen 0,3): se registra a
  amplitud 0,300018, así que la cadena no enmascara silencio.
- Menú de tarjeta de memoria: amplitud máxima 0,000000 (silencio real en esa pantalla).
- **Combate (Mitsurugi vs Seung Mina): amplitud máxima 0,999969**, con tramos de 0,79 y 0,72.
- Evidencia: `sb_audio.wav`, `ctrl2.wav`, `sb_fight.wav`, salidas de `sox … stat`.
- Matiz: falta aclarar si el silencio de los menús es BGM desactivado por defecto.

## T10. Guardado en memory card — SUPERADA

- Las tarjetas se crean formateadas al arrancar: `source/SoulBladeRecomp/saves/card1.mcd` y
  `card2.mcd`, 131.072 B, cabecera `MC`.
- Ruta: menú → OPTION → MEMORY CARD → SAVE CONFIG & RECORDS → Slot 1 → **START** → «SAVE OK!».
- Evidencia en disco: `card1.mcd` md5 `a7b6af52…` → `3bea444d…` y aparición de la entrada
  `BASLUS-00240S_B_SAVE`. Copia: `tests/referencias/card1-tras-guardado.mcd`.

## T11. Salida limpia — SUPERADA

- `python3 $D quit` → el proceso termina con **exit=0** (`logs/run-debug-2.log` acaba en
  `exit=0`). El servidor responde «emu busy or frozen» antes de salir: mensaje engañoso.
- SIGTERM sobre la instancia release → también **exit=0** (SDL traduce la señal a evento de
  cierre y el proceso sale ordenado). No se pierde ni se corrompe la tarjeta (md5 idéntico).
- El runtime no imprime líneas de apagado: el código de salida es la evidencia. Persistido en
  `docs/cierres-y-codigos.md` porque el volcado del job en segundo plano no queda en `logs/`.

## T12. Segundo arranque tras cierre limpio — SUPERADA

- Proceso nuevo (`./run.sh --debug`), BIOS + disco + navegación completos.
- Carga del guardado del ciclo anterior: MEMORY CARD → LOAD CONFIG & RECORDS → Slot 1 →
  START → «LOAD OK!».
- Observación: la tarjeta cambia 5 bytes en el frame de checksum del bloque 0 tras la carga
  (`0x1F80-0x1FFF`); el contenido del save no se toca.

## T13. Estabilidad en sesión larga — PARCIAL

- Proceso release ha estado >20 min en attract a 60 fps sin caídas.
- Falta una sesión de juego real cronometrada.

---

## Comparación con referencia PS1 — NO EJECUTADA

No hay emulador de referencia instalado ni se ha ejecutado el disco en uno. Sin esta
referencia no se pueden afirmar diferencias de gráficos, audio o timing.

## T14. Mando GameSir T4n Lite — SUPERADA (un mando)

- **Detección del sistema y de SDL**: `sdlprobe` (en `tests/diagnostico/`) enumera 2 joysticks:
  `Ducky One 3 SF RGB` (isGamepad=0, el teclado expone un joystick y SDL lo descarta) y
  `Generic X-Box pad` (isGamepad=1, GUID `03008665373500004010000000010000`).
- **SDL recibe las pulsaciones**: sonda en modo escucha → `GAMEPAD_BUTTON_DOWN` con
  button 0(A), 1(B), 2(X), 3(Y), 6(START), 13/14 (cruceta).
- **El runtime no las usaba** (bug, ver `docs/decisiones-tecnicas.md` D10): el asiento 1 caía en
  «keyboard» en ambas builds. Corregido con `[controller] p1_device = "auto"` en `game.toml`.
- **Palabras PSX que llegan al juego tras la corrección** (`pad_status`): `0xFFEF` arriba,
  `0xFFDF` derecha, `0xFF7F` izquierda, `0xFF3F` abajo+izquierda, `0xBFFF` Cross, `0xDFFF`
  Círculo, `0xEFFF` Triángulo.
- **Partida real jugada con el mando**: el usuario salió del attract, entró en Arcade, insertó
  moneda, eligió personaje y jugó (captura final: GAME OVER, Mitsurugi vs Li Long).
- **Correspondencia correcta por posición física**: B (este) = ○ = confirmar; A (sur) = × =
  cancelar. Confirmado por el usuario en partida.

### Matices medidos (no son fallos del proyecto)
- **START del mando físico: VERIFICADO por medición** en la sesión de dos mandos. Con el
  muestreo corregido (conexión por muestra) aparece `0xFFF7` en `slot0` procedente del GameSir,
  además de `0xFFBF` (abajo) y `0xFF9F`. El primer intento de medirlo no valía: usaba socket
  persistente y el servidor atiende **un comando por conexión**, así que solo obtuvo una
  muestra y luego `Broken pipe`.
- **El receptor 2.4G no numera los botones como el mapeo genérico de Xbox.** SDL declara para
  este GUID `back:b6, start:b7`, pero los pares observados a nivel de evento son
  joystick 6 → gamepad 4 (LB), joystick 7 → gamepad 6 (BACK), joystick 1 → 1, joystick 2 → 2.
  Nunca se observó `gamepad button=7`. Consecuencia: no se puede deducir el botón físico por
  el número SDL; hay que verificarlo jugando. Queda anotado como peculiaridad del mando.
- **SELECT**: no verificado. Puede no estar reportado por el mando o no tener función en este
  juego; no se marca como soportado ni como fallo.

## T15. Dos mandos y partida de dos jugadores — SUPERADA

- **El propio runtime lo registra al arrancar** (`logs/run-pad-dos.log`):
  `opened controller for slot 1 (instance 6): Generic X-Box pad` y
  `opened controller for slot 2 (instance 7): Generic X-Box pad`. Dos instancias distintas,
  una por asiento. Contraste: en la instancia anterior al arreglo D10 esa línea **no aparece
  ninguna vez** (0 ocurrencias en `logs/run-pad-1.log`), que es la firma del bug.
- **Asignación por asiento medida, no inferida**: pulsar izquierda **solo en el mando 1**
  produce `slot0 buttons=0xFF7F` (3 veces) y pulsar **solo en el mando 2** produce
  `slot1 buttons=0xFF7F` (3 veces). Ningún cruce.
- **Salvedad medida en el cierre**: al apagar, el runtime reabre los mandos y en esas
  reaperturas ambos asientos llegan a apuntar a la **misma instancia** (`slot 1` y `slot 2`
  con `instance 6`, luego con `instance 9`). Ocurre después de `executing from PC=...` y
  justo antes de `exit=0`, es decir **durante el apagado**, no durante la partida: las
  mediciones de asignación y la partida 2P se hicieron antes y son válidas. Se anota como
  indicio de que el camino de reapertura no aplica la reserva por asiento.
- **Ambos asientos activos en partida**: 55 s de muestreo a 40 ms → **1224 muestras, 0 fallos,
  73 cambios**. `slot0` acumuló 34 pulsaciones no neutras con `0xFFF7` (START) ×5, `0xBFFF`,
  `0xDFFF` ×4, `0xEFFF` ×2 y cruceta; `slot1` 6 (`0xFF9F` ×3, `0xFFBF`, `0xDFFF` ×2). El
  jugador 2 se incorporó después, de ahí el recuento menor.
- **Simultaneidad real**: a los 46,01 s **ambos puertos registran `0xDFFF` en el mismo
  instante** (los dos jugadores pulsando ○/B a la vez). Es la prueba más fuerte de que los dos
  puertos son independientes y se leen por separado, no un solo mando replicado.
- **Partida de dos jugadores**: VS BATTLE MODE, cada jugador insertó su moneda con START en su
  mando, eligieron personajes distintos y jugaron. Evidencia: `VS2P.png` (Taki vs Voldo, modo
  versus sin rótulo STAGE, temporizador 08) y `pad_two2.txt`.
- Configuración: `[controller] p1_device = "auto"` y `p2_device = "auto"` en `game.toml`.

### Pendiente
- Teclado: la ruta existe (`pad_from_keyboard`, `keybinds.ini` aún sin generar) y era el
  dispositivo por defecto antes de la corrección; no se ha validado en partida con teclado.
- SELECT sigue sin función conocida en este juego.

## T15 — Coordenadas y reconstrucción del bloque de 0x10D00 (superada)

Reproducible: `python3 tests/diagnostico/verify_10d00.py`.

- Destino `0x80010D00` (físico `0x10D00`, offset EXE `0x1500`, offset BIN `0xF198`).
- Origen `0x80010F60` (offset EXE `0x1760`, offset BIN `0xF3F8`), 768 B, desplazamiento `0x260`.
- `sha256` del origen `227f606c9711c4a2…`; la imagen del EXE en el destino **difiere**
  (`4d1d74e7…`), luego la copia cambia esos bytes.

## T16 — Copia del bloque por el BIOS (superada, con traza)

`PSX_WTRACE_BOOT_RANGES='0x00010D00-0x00011000'` + `wtrace_boot_dump`:

- 192 palabras contiguas de `0x10D00` a `0x10FFC`, sin huecos, frame 51.
- PC escritor `0x000008B8` (BIOS), `$ra` `0xBFC03BE8`/`0xBFC03BFC`, `$sp` `0x801FFCF8` (pila del juego).
- El punto de llamada del lado del juego **no** quedó registrado (pendiente).

## T17 — Rendimiento real de la build release (superada)

`PSX_FPS_TELEMETRY=1 ./SoulBlade_Recompiled --game game.toml --disc <cue>`, 55 s, 3.302 frames:

```text
[FPS] game: 59.9 fps (1.00x) | frames: 2881
[FPS] game: 60.0 fps (1.00x) | frames: 3001
[FPS] game: 59.6 fps (0.99x) | frames: 3121
[FPS] game: 60.4 fps (1.01x) | frames: 3302
```

Resultado: **1,00x sostenido**, sin caídas por debajo de 0,99x. Log: `logs/run-fps-release.log`.
Salvedad: el pacer de reloj de pared fija la cadencia, así que esto prueba «llega a 60», no cuánto
margen sobra.

## T18 — Validez de la tarjeta de memoria que produce el port (revisado: NO es defecto)

> **Corrección posterior (D14).** Las tarjetas de ejemplo del propio framework
> (`tests/fixtures/memcards/*.mcd`) tienen el mismo tipo de frame con `0x7F` incoherente en los
> bloques de datos (frames 64, 128, 192). El campo se mantiene en los sectores de estructura y
> no en los de datos, y el runtime valida el checksum de transacción. Por tanto **no está
> demostrado que sea un defecto**; se retira esa etiqueta. El texto siguiente queda como
> registro de lo observado.

Herramienta: `python3 tests/diagnostico/check_mcd.py <tarjeta.mcd>`.

```text
card1.mcd: checksums 1013/1024 correctos, 11 invalidos
           frames [64..74]  -> bloque 1 (8 KB), el del guardado
           BASLUS-00240S_B_SAVE, 8192 B, estado 0x51
card2.mcd: 1024/1024 correctos (vacia)
```

Los 11 frames con checksum invalido son **exactamente los del guardado** (el frame 64 empieza por
`53 43` = "SC", cabecera de save PS1). Los frames no escritos conservan su checksum valido.

Causa localizada: `memcard_write_sector()` (`runtime/src/memcard.c:375`) copia los 128 B tal cual,
sin validar ni recalcular el XOR. En hardware real la tarjeta **rechaza** un frame con checksum
erroneo; aqui se acepta en silencio. Consecuencia: el guardado del port funciona dentro del port
(la lectura no valida) pero una tarjeta manejada por hardware real, por otro emulador estricto o por
un gestor de tarjetas lo marcaria como corrupto.

No se ha "reparado" la imagen a mano: recomputar los checksums en el fichero ocultaria el fallo y no
demostraria que el guardado es correcto.

## T19 — Modos del checksum interno de frame (superada, unitaria)

`ninja -C psxrecomp/runtime/build-tests sio_card_protocol_test` + ejecución directa:

```text
test_frame_internal_checksum_modes: 7/7 ok
=== TOTAL: 346 checks, 0 failures ===
```

Cubre: por defecto un frame incoherente se acepta y se almacena verbatim; con
`PSX_MC_STRICT_FRAME_CHK=1` se rechaza (end byte `4Eh`) y no se escribe; en estricto, un frame
coherente se acepta.

## T20 — Modo estricto no altera el arranque normal (superada)

Build debug recompilada con el parche; ejecución con `PSX_MC_STRICT_FRAME_CHK=1` y
`PSX_MC_WRITE_LOG=1` sobre tarjetas de prueba aisladas:

```text
[MCW] sec=63 stored7f=0x0E xor0_7E=0x0E match=1 tx_chk=0x3F exp_chk=0x3F chk_ok=1
[MCW] sec=63 stored7f=0x0E xor0_7E=0x0E match=1 tx_chk=0x3F exp_chk=0x3F chk_ok=1
```

La escritura válida se acepta, 0 errores y el juego arranca. Tarjetas de prueba con md5 sin
cambios (`35bcc543…`, `8a250fe6…`).

## T21 — Disco inválido: aviso claro, sin caída (superada)

`./SoulBlade_Recompiled --disc /tmp/cue-malo.cue` con un CUE que referencia un `.bin` inexistente:

```text
Disc Image Warning: No ISO9660 CD001 header was found at the standard PS1 disc locations.
```

Sin `segmentation fault`, sin `abort`, proceso vivo hasta el `timeout` de la prueba (exit 124 por
el timeout, no por el binario). Comportamiento equivalente a una consola sin disco: avisa y
continúa. Log: `/tmp/run-cue-malo.log`.

## T22 — Estabilidad sostenida en release (superada)

Release con `PSX_FPS_TELEMETRY=1`, 8 min 34 s, **31.006 frames**, sin entrada inyectada (demos
del attract, que sí ejecutan código de juego).

| métrica | resultado |
|---|---|
| FPS | 399 muestras en el primer tramo: **min 59,5**, media 60,50, **0 muestras por debajo de 59** |
| Pico anómalo | 1 muestra de 288,9 fps (4,82x) en el frame 294, durante el arranque antes de que asiente el pacer |
| CPU | 42,8–43,5 % de un núcleo, estable |
| RSS | 269 MB → 359 MB, con crecimiento que se frena (341→345→347→349→359) en 8:34 |
| Errores en el log | 0 |
| Cierre | `SIGTERM` → **exit=0**, sin caída |
| Tarjetas | md5 idénticos antes y después (`35bcc543…`, `8a250fe6…`) |

Log: `logs/soak-release.log`. No se observa fuga evidente; para descartarla del todo haría falta
una ventana más larga, que queda como pendiente.

## T23 — Escalado interno sin pérdida de velocidad (superada, parcial)

| config | factor | FPS |
|---|---|---|
| nativa | 1x | 60,0 (1,00x) |
| `game-hd-test.toml` (1080p, ss 2) | 5x | 59,9 (1,00x) |
| `game-4k-test.toml` (4k, ss 2) | 9x | 59,9 (1,00x), min 59,5 |

El log confirma que el escalado se aplica (`internal resolution 1080p … 5x requested`,
`supersampling 5x`). **No verificado visualmente**: la captura del servidor es el framebuffer de la
consola (256x240), no la ventana reescalada.

## T24 — Estabilidad con escalado 1080p en release (superada)

Release con `game-hd-test.toml` (1080p interno, 5x) y telemetría, 7 min 24 s, **27.044 frames**:

| métrica | resultado |
|---|---|
| Muestras FPS | 442: min 59,5, max 289,2 (arranque), **0 por debajo de 59** |
| Tras el arranque | min 59,5, media 59,92 |
| CPU | 43,5 % de un núcleo |
| RSS | 360 MB, sin crecimiento sostenido |
| Cierre | `SIGTERM` → **exit=0** |
| Tarjetas | md5 idénticos (`35bcc543…`, `8a250fe6…`) |

Log: `logs/soak-hd.log`. El escalado 1080p no introduce inestabilidad ni pérdida de velocidad en
esta ventana.

## T25 — Estado de la suite de pruebas del framework (parcial, con hallazgos)

Contexto: al compilar todos los targets de prueba de esta revisión aparecieron fallos de enlace
**preexistentes** (verificados contra `HEAD~1`), no relacionados con el juego ni con los cambios de
esta sesión.

Arreglado en esta sesión (commits del framework `daa85f7a`, `c2165c73`):

| problema | efecto | arreglo |
|---|---|---|
| `memcard_last_flush_result` sin stub en 5 tests | 5 targets no enlazaban | stub añadido |
| `CMAKE_C_STANDARD 99` con `dma.c` usando `timespec_get` (C11) | ~170 targets no construían | `CMAKE_C_STANDARD 11` |
| `psx_mod_host_output_scope` sin stub en `test_mod_texture_banks` | 1 target no enlazaba | stub añadido |

Resultado medido:

- **Área sio/card/memcard: 11/11 en verde** (antes 5 ni compilaban).
- Suite global: de 65/279 pruebas construibles a ~114 en verde; siguen fallando por símbolos
  ausentes en otros targets (`cdrom_snapshot_validate`, `g_boot_state_cpu_timing_restored`,
  `psx_devices_service_to_now`, `spu_catch_up`, `spu_cd_snapshot_bytes`…), todos ajenos al juego.
- Fallos de test en áreas no tocadas (GL, tcc bundle, frame interpolation, overlay compile arch):
  `host_pause_first_present_test`, `gpu_gp0_history_guard_test`,
  `frame_interpolation_context_ownership_test`, `overlay_compile_arch_test`,
  `gl_scale_invariance_test`, `linux_tcc_bundle_smoke_test`, `gl_frame_gen_test`.

No se persigue arreglar la suite completa: es deuda del framework en esta revisión y no afecta al
juego. Queda documentada para no confundirla con fallos del port.

## T26 — A/B: release con y sin caché de shards (superada)

Misma build release, mismo protocolo, tres minutos:

| configuración | shards | muestras | min | media | <59 fps |
|---|---:|---:|---:|---:|---:|
| `build-release` sin `cache/` | 0 | 399 | 59,5 | 60,50 | 0 |
| `build-release` con `cache/` copiada de debug | 177 | 183 | 57,3 | 59,92 | 1 |

Conclusión: **la cobertura nativa no cambia el rendimiento medible** en esta máquina. La diferencia
de la media viene del tramo de arranque incluido en la primera medida; el cuerpo estacionario es
59,92 en ambos casos. La única muestra a 57,3 con shards es un transitorio aislado.

Esto cierra la discusión abierta desde el principio del proyecto: convertir overlays no hacía el
juego más rápido, y ahora está medido sobre la build que se distribuiría.

## T27 — Build combinada: arranque repetido, mandos y cierre limpio (superada)

Dos arranques consecutivos de `build-static-debug` (caché dinámica + overlays estáticos +
`overlay_region_floor = 0x96000`), sin entrada inyectada:

| comprobación | arranque 1 | arranque 2 |
|---|---|---|
| `checked` | `[0x0, 0x96000, 0x110000, 0x111000]` | idéntico |
| `loads` / `registered` | 4 / 107 | 4 / 107 |
| Despachador estático | 197 entradas, 10.799 despachos | idéntico |
| `slot0` / `slot1` | `connected=True` / `connected=True` | — |
| Cierre con `SIGTERM` | **exit=0** | **exit=0** |
| Tarjetas | md5 `35bcc543…` / `8a250fe6…` | sin cambios |

Cubre los puntos 10 (dos mandos), 12 (cierre limpio) y 13 (segundo arranque) de la lista de
regresión **para la build combinada**, que hasta ahora solo se había probado con la build debug
normal. No cubre menús, combate ni guardado (requieren navegación).

## T28 — Construcción de la AppImage (superada)

`package/build-appimage.sh` sobre `build-release`: payload preparado desde cero, copia del disco
verificada por hash, empaquetado con `appimage-tool` 1.9.1 + `linuxdeploy` (SHA-256 verificado) y
validación automática posterior. Artefacto: **371.300.856 B**, sha256 `b79621c1…`.

Incidencias encontradas y corregidas durante la construcción:

| síntoma | causa | solución |
|---|---|---|
| `Bundled BIOS Missing` con el BIOS dentro del paquete | `exe_dir_from_argv()` prefiere `$APPIMAGE` (el fichero), y esa misma función resolvía el BIOS | nuevo `bundle_dir_from_argv()` basado en `/proc/self/exe`; BIOS y `mods/` se resuelven ahí, ajustes siguen junto al paquete |
| el segundo anclaje del BIOS seguía fallando | `resolve_bios_path()` tenía su propia lógica `find_upward` sobre el directorio de ajustes | recorre ambos anclajes (paquete y directorio del binario) |
| `cannot launch with selected mods: Read-only file system` | `save_state()` trata como fatal no poder crear `mods/` | en solo lectura avisa (`mods state not persisted`) y continúa |

## T29 — Arranque independiente del paquete (superada)

Ejecutada desde `/tmp/otro sitio` (ruta con espacios) a través de un enlace simbólico al `.AppImage`,
con `XDG_DATA_HOME` aislado: BIOS cargado desde el montaje, `disc region NTSC-U (serial SLUS-00240)`,
**59,9-60,4 fps** sostenidos, sin errores ni bibliotecas ausentes.

## T30 — Independencia del directorio de desarrollo (superada)

Con el proyecto **completamente oculto** (`bwrap --dev-bind / / --tmpfs "~/Juegos/Proyecto
Soul Blade"`, verificado que el directorio queda vacío) y modo `APPIMAGE_EXTRACT_AND_RUN=1`: arranca,
carga su BIOS, detecta el disco y corre a **60,4 fps (3725 frames)**. No depende ni del repositorio ni
del CUE/BIN originales.

## T31 — Verificación visual (superada)

Capturas reales del escritorio con `spectacle` separadas 8 s: ventana titulada **"SoulBlade
Recompiled"** mostrando la intro (barco, espada, rótulo), con hashes de imagen distintos entre
capturas (la imagen se anima).

## T32 — Integridad del paquete (superada)

| comprobación | resultado |
|---|---|
| BIN empaquetado vs original | sha1 `e1a48d3e5c3614be1a5f3fe7f1f4036dbc6c5b94` — idéntico |
| CUE empaquetado vs original | md5 `a4567ab2da5249af10bf8a47530e4af9` — idéntico |
| referencia `FILE` del CUE | `Soul Blade (v1.1).bin` presente con ese nombre exacto |
| rutas `~` en AppRun/game.toml/.desktop | 0 |
| bibliotecas sin resolver | 0 |
| originales tras todas las pruebas | BIN, CUE, PSV y tarjetas sin cambios |

## T33 — Bazzite: causa raíz del fallo SDL y verificación en la sesión real (parcial)

Síntoma reportado: `SDL_Init failed: No available video device` tras cargar `game.toml`, BIOS y disco.

**Causa raíz**: el intento se ejecutó por SSH. Esa sesión no hereda `WAYLAND_DISPLAY` ni `DISPLAY`, y
SDL3 sin ninguno de los dos no encuentra backend de vídeo. No era Mesa, ni Vulkan, ni el paquete: el
arranque llegaba al disco porque eso ocurre antes de crear la ventana.

Entorno real de Bazzite: Fedora 44, kernel 7.2.9, uid 1000, **Steam Gaming Mode**
(`gamescope-session-plus ogui-steam`). El socket del compositor es `gamescope-0`; no existe
`wayland-0`. Hay Xwayland (`:0`).

Correcciones (AppRun, en la AppImage `65b195b6…`):

| defecto | corrección | verificación |
|---|---|---|
| sin variables de pantalla, SDL abortaba | detectar `wayland-*`/`gamescope-*` en `XDG_RUNTIME_DIR`, o `DISPLAY=:0` | por SSH sin variables: 59,6-60,4 fps |
| `LD_LIBRARY_PATH` imponía nuestro `libcrypto` a los hijos (`zenity`: `OPENSSL_3.0.1 not found`) | eliminado: el binario ya lleva `RUNPATH=$ORIGIN/../lib` | 60 fps en CachyOS y Bazzite |

Pruebas superadas en Bazzite:

- Hash del artefacto en destino idéntico al construido; original conservado como `.orig`.
- Arranque por SSH sin entorno gráfico y desde otro directorio de trabajo (`/tmp`) como unidad
  systemd de usuario: BIOS y disco del paquete, 60 fps.
- Vía Wayland (`gamescope-0`) y vía X11 (Xwayland): ambas arrancan.
- Menú interactivo, selección de personaje con marcador **1P**, pantalla VS (`STAGE 1 — MITSURUGI VS
  TAKI`) y combate animado: capturados con el servidor de depuración (no hay `grim` y `spectacle` no
  funciona sin kwin en Gaming Mode).
- Audio: cliente PipeWire `application.name = "SoulBlade_Recompiled"` activo durante la partida.
- Datos escribibles en `~/.local/share/soulblade/`; cierre limpio por `systemctl --user stop`.

**No superado / no comprobado**:

- Estado 6/7 del proyecto (combate con HUD y menú `1P PAUSE`): la inyección `press` llega al menú y a
  la selección con marcador 1P, pero se detiene en `PRESS 2P START`. Probado también con
  `p2_device="none"` en un `XDG_DATA_HOME` aislado, sin éxito. No se declara superado.
- Mandos GameSir: no había ninguno conectado en Bazzite durante la sesión (solo un receptor Logitech),
  así que no se pudo verificar detección ni reparto 1P/2P en el paquete final.
