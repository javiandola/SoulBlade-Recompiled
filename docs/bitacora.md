# Bitácora técnica — Proyecto Soul Blade

## Sesión 1 — 2026-10-24 (19:19 → 21:0x CEST)

### Objetivo de la sesión
Pasar del estado "preparación" a una build nativa Linux verificada: auditoría, framework,
proyecto de juego, primera compilación reproducible y validación funcional.

### Tareas realizadas y comandos

1. **Auditoría de sistema (solo lectura)**
   - `cat ~/.hermes/sysinfo.md`, `uname -a`, `lscpu`, `df -h`, `pacman -Q`
   - Comprobación de herramientas: `git`, `cmake`, `ninja`, `gcc`, `clang`, `python3`, `pkg-config`.
   - Resultado: nada que instalar. Registro de paquetes instalados: **ninguno**.

2. **Verificación de los originales**
   - `sha1sum` / `sha256sum` / `md5sum` del BIN, `cat -A` del CUE, `stat` de los tres archivos.
   - SHA-1 `e1a48d3e…` coincide con el dato del usuario. Nada modificado.

3. **Investigación del repositorio del autor**
   - `git ls-remote https://github.com/fabioap-cpu/SoulBlade_Recomp.git HEAD` → pide credenciales.
   - `curl api.github.com/repos/fabioap-cpu/SoulBlade_Recomp` → 404. Igual para `/releases`.
   - `api.github.com/users/fabioap-cpu/repos` → la cuenta existe, el repo no está.
   - `recomp.fyi` lo marca como "repo missing".
   - Clonado `WWF-SmackDown-2-Recomp` (público, solo README + punteros) para leer su método:
     submódulo `psxrecomp` en `20ae6db9`, `recomp-ui` en `87bbf43c`.

4. **Framework**
   - `git clone --recurse-submodules https://github.com/RetroPortingToolKit/psxrecomp.git`
   - HEAD `31df2e1e` (`nightly-870-g31df2e1e`). `git merge-base --is-ancestor 20ae6db9 HEAD` → sí.
   - `cmake -S recompiler -B recompiler/build -G Ninja -DCMAKE_BUILD_TYPE=Release` + build → 348/348.

5. **Proyecto de juego**
   - `sh tools/new_project_layout/setup_project.sh --disc "<cue>" --dir source --name SoulBladeRecomp
     --players 2 --zip-prefix soulblade --no-recomp-ui --no-netplay --no-wizard --no-ci
     --no-fetch-boxart --no-generate --no-build --no-github --yes`
   - Resultado: commit `04a49cd`, `game.toml`, 1453 seeds, `disc/SLUS_002.40`, símbolos.
   - `verify-disc` → exit 0.

6. **Generación del código**
   - Primer intento: exit 1, "Toolchain ensure succeeded but bin/ is not usable for emitters".
     Causa: `activate_embedded_toolchain()` es Win32-only y el flujo no lo contempla en Linux.
   - Segundo intento con `--no-toolchain-download`: exit 0. 59 shards, 2.409.187 líneas,
     dispatch de 3994 entradas, OpenBIOS recompilado.

7. **Build del runtime**
   - Primer intento: fallo de compilación por `std::u8string` (GCC 16 usa C++20 por defecto).
   - Reconfigurado con `-DCMAKE_CXX_STANDARD=17`: exit 0, 319/319, `SoulBlade_Recompiled`
     ELF x86-64 de 40 MB.
   - Build de depuración: `build-debug` RelWithDebInfo con `PSX_DEBUG_TOOLS=ON` → 383/383,
     servidor TCP en 4370.

8. **Pruebas funcionales ejecutadas**
   - Arranque headless: BIOS LLE/OpenBIOS, ejecución desde `0xBFC00000`. OK.
   - Arranque con ventana (Wayland, OpenGL/RADV): 60 fps estables, intro FMV con MDEC.
   - Menú principal, modo Arcade, selección de personaje con rejilla y marcador 1P.
   - Combate real STAGE 1 Mitsurugi vs Voldo con barras de vida, temporizador y cronómetro.
   - Entrada por mando vía TCP (`press`): verificada por cambio de resaltado y de pose.
   - Ritmo: cronómetro del juego 0'20"19 → 0'30"26 en 10 s de reloj de pared.
   - Audio: flujo PipeWire `s16le 2ch 44100Hz` abierto y no silenciado.

### Ficheros creados o modificados
- `docs/auditoria-inicial.md`, `docs/plan.md`, `docs/decisiones-tecnicas.md`, `docs/bitacora.md`
- `build.sh`, `run.sh`, `tests/PRUEBAS.md`, `.gitignore` (raíz)
- `source/SoulBladeRecomp/` (proyecto completo, repo propio)

### Versiones relevantes
kernel 7.3.0-4-cachyos · Plasma 6.8.1 Wayland · Mesa 26.2.5 · cmake 4.4.4 · ninja 1.13.2 ·
gcc 16.2.1 · clang 23.1.3 · SDL3 3.4.18 · psxrecomp `31df2e1e`

### Errores pendientes / no resueltos
- El dump es de una sola pista; las puertas multi-pista de netplay lo rechazan (sin efecto local).
- Huella del disco no cotejada contra Redump (no hay verificación remota hecha).
- Overlays ejecutados por intérprete; la compilación estática queda para más adelante.

### Siguiente paso técnico
Guardado/carga en memory card, audio audible y segundo arranque tras cierre limpio.

---

## Sesión 2 — 2026-10-24 (continuación)

### Objetivo
Documentar, crear y probar los scripts, commit local, lista reproducible de pruebas y
después las pruebas pendientes: memory card, audio y segundo arranque.

### Estado de procesos al empezar
- PID 12771 → `build-release/SoulBlade_Recompiled` (sin servidor de depuración).
- PID 15474 → `build-debug/SoulBlade_Recompiled` (TCP 4370, instrumentado).

### Tareas realizadas

**1. Inspección de procesos antes de tocar nada**
- Vivos: PID 12771 = `build-release/SoulBlade_Recompiled` (sin servidor de depuración,
  telemetría a `logs/run-windowed.log`) y PID 15474 = `build-debug/SoulBlade_Recompiled`
  (TCP 4370, instrumentado). Se mantuvo el release hasta que hizo falta liberar la tarjeta.

**2. Scripts creados y probados**
- `build.sh`: comprueba herramientas, exige `generated/`, fija `CMAKE_CXX_STANDARD=17`
  (sin esto GCC 16 rompe el runtime), compila y verifica que el binario sea ELF x86-64.
  - Prueba: `./build.sh` → exit 0, 6/6 objetivos, 0,9 s en incremental, **mismo BuildID
    `3dca9176…`** que la build anterior → compilación determinista.
- `run.sh`: resuelve ruta del disco, distingue `--debug`/`--headless`, hace `cd` al
  directorio de build (el runtime resuelve `game.toml`, `saves/` y `cache/` contra el cwd)
  y pasa el control con `exec`.
  - Prueba: `./run.sh --headless` → arranca y carga `SLUS-00240`; `./run.sh --help` correcto.
- Logs: `logs/build-release.log`, `logs/build-release.log.configure`.

**3. Commits locales (sin push, sin publicar)**
- Raíz del workspace `e62971e` — `.gitignore`, `build.sh`, `run.sh`, `docs/`, `tests/`.
  Comprobado que no entra ningún `.bin`/`.cue`/`.psv` (el `.gitignore` los excluye).
- Repo del juego `58592fa` — `generated/` (59 shards) + `game_options.toml`.
  `git ls-files` sin ficheros del juego ni BIOS.

**4. Técnicas de prueba descubiertas (clave para automatizar)**
- `pause` **ya no existe** en esta versión (`"pause is removed"`): no se puede congelar el
  emulador para inspeccionar entre pasos.
- El menú principal con el cursor en ARCADE MODE es **byte-estable** (md5
  `ffc166f5…`), así que se puede esperar su aparición comprobando el hash de la captura.
  Esto sustituye a los tiempos fijos y elimina las carreras con el temporizador de inactividad.
- `pgrep -f "<cadena>"` coincide con la propia línea de comandos del shell: un `kill` basado
  en él se mató a sí mismo. Hay que filtrar con `grep -F … | grep -v grep` sobre `ps`.

**5. Guardado y carga en memory card (T10 y T12)**
- El juego tenía tarjetas ya creadas y formateadas en `source/SoulBladeRecomp/saves/`
  (`card1.mcd`, `card2.mcd`, 131.072 B, cabecera `MC`, 8.041 bytes de directorio).
- Ruta en el juego: menú → OPTION → MEMORY CARD → SAVE CONFIG & RECORDS → Slot 1 →
  el diálogo pide **START** (no Círculo) → «SAVE OK!».
- Evidencia en disco: `card1.mcd` pasó de md5 `a7b6af52…` a `3bea444d…` con la entrada
  `BASLUS-00240S_B_SAVE` escrita. Copia en `tests/referencias/card1-tras-guardado.mcd`.
- Carga en un **proceso nuevo**: arranque → OPTION → MEMORY CARD → LOAD CONFIG & RECORDS →
  Slot 1 → START → «LOAD OK!». Eso cierra el ciclo guardar → cerrar → arrancar → cargar.
- Observación: tras la carga, la tarjeta cambia **5 bytes** en el frame de checksum del
  bloque 0 (`0x1F80-0x1FFF`: aparecen `4D 43` = «MC» y el checksum `0x0E`). El contenido del
  save no se altera. Queda anotado como efecto colateral a vigilar, no como fallo.

**6. Audio (T9)**
- Primer registro (menú de tarjeta, 6,14 s): amplitud máxima **0,000000**.
- Experimento de control por la misma vía (tono 440 Hz generado con `sox` y reproducido con
  `paplay`, monitor del mismo sumidero): amplitud máxima **0,300018** = la del tono.
  La cadena de captura es válida, así que ese silencio era real.
- Segundo registro durante un combate (Mitsurugi vs Seung Mina): amplitud máxima
  **0,999969**, con tramos de 0,79 y 0,72 → hay audio de juego.
- Conclusión: el audio funciona en partida; los menús de tarjeta/opciones son mudos
  (a confirmar si es por BGM de menú o por diseño).

**7. Cierre y segundo arranque (T11 y T12)**
- Cierre del release con SIGTERM: **exit=0**, SDL traduce la señal a evento de cierre y el
  proceso sale ordenado; **no corrompe la tarjeta** (md5 intacto). (Corregido: en el primer
  informe lo describí como salida sin volcado ordenado; el `$?` del wrapper desmiente eso.)
- Cierre del debug con `quit` por TCP: responde «emu busy or frozen» y aun así sale con
  **exit=0** (`logs/run-debug-2.log` acaba en `exit=0`). Cierre ordenado confirmado.
- Códigos persistidos en `docs/cierres-y-codigos.md` (el runtime no imprime líneas de apagado).
- Segundo arranque: proceso nuevo, BIOS, disco y navegación completos, y carga del save OK.

### Ficheros creados o modificados
- `build.sh`, `run.sh`, `.gitignore`, `tests/PRUEBAS.md`, `tests/referencias/card1-tras-guardado.mcd`
- `docs/bitacora.md` (este archivo), `docs/plan.md` y `docs/decisiones-tecnicas.md` sin cambios de fondo
- `source/SoulBladeRecomp/saves/card1.mcd` (guardado del propio juego, no versionado)

### Errores pendientes / no resueltos
- `quit` devuelve error aunque el proceso sale con 0: mensaje engañoso del servidor.
- Los menús de opciones/tarjeta parecen mudos; falta determinar si es BGM desactivado por defecto.
- Sin comparación con referencia PS1 (no hay emulador de referencia instalado ni ejecutado).
- Overlays siguen ejecutándose por intérprete.

### Siguiente paso técnico
Compilación estática de los overlays capturados (`overlay_captures.json` tiene 10 regiones con
seeds) y comparación con una referencia PS1.


---

## Sesión 3 — 2026-10-24 (corrección de la validación de combate y auditoría de entrada)

### Motivo
El usuario aclaró que los combates vistos hasta ahora son demostraciones del modo attract.
Los informes previos los presentaron como partida jugada: **error de validación asumido y
corregido aquí**. Material nuevo: `docs/estados-de-juego.md`, con la escala de 7 estados y los
marcadores que distinguen una partida del jugador de una demo.

### Qué se ha verificado de verdad
- **Secuencia completa de una partida 1P**, pantalla a pantalla:
  START → menú (cursor en ARCADE) → Círculo → «SELECT YOUR CHARACTER» con **INSERT COIN**
  → START (moneda) → marcador **1P** → Círculo (confirma personaje) → VS STAGE 1
  → «BATTLE 1» → combate. Evidencia: `P2_charselect.png`, `X2_fight.png`, `Z2_circle.png`,
  `Z6_start.png`.
- **Prueba de que es partida del jugador:** menú **1P PAUSE** (CANCEL/COMMAND/VOL/RESET) sobre
  un combate en curso (`T1.png`).
- **Entrada dependiente de dirección, con control negativo:** desde el mismo savestate,
  neutro vs neutro = 0 píxeles distintos (determinista), neutro vs IZQUIERDA = 53.327,
  neutro vs DERECHA = 65.122, IZQUIERDA vs DERECHA = 41.321. En el attract, IZQUIERDA y
  DERECHA dieron capturas **idénticas** (0 píxeles): la entrada se ignora.
- Mapa de botones confirmado en el código (`sio.c`: `out[2]=low`, `out[3]=high`):
  Start `0xFFF7`, Círculo `0xDFFF` (aceptar), Cross `0xBFFF`, Cuadrado `0x7FFF`,
  Triángulo `0xEFFF`, Select+Start `0xFFF6`, Arriba `0xFFEF`, Abajo `0xFFBF`,
  Izquierda `0xFF7F`, Derecha `0xFFDF`.

### Auditoría de entrada (sin mando encendido)
- El runtime usa la API **GameController de SDL3** (`SDL_GameControllerGetButton/GetAxis`,
  `SDL_GameControllerGetJoystick`, `SDL_GamepadButtonFromString`), no joystick crudo, así que
  se beneficia de la base de datos de mandos de SDL.
- Configuración por `input.ini` junto al ejecutable (`build-debug/input.ini` existe con los
  valores por defecto): `[controller] enabled=true, device=0, deadzone=3277` y `[mapping]`
  con nombres estilo Xbox: `a→cross, b→circle, x→square, y→triangle, start→start,
  back→select`, cruceta→cruceta, hombros/gatillos→L1/R1/L2/R2, clics de stick→L3/R3.
- **No hay hotplug** de mandos: no existe manejo de `SDL_EVENT_GAMEPAD_ADDED`. El mando debe
  estar conectado **antes** de lanzar el juego.
- Dos asientos (`PSX_MAX_PLAYERS=2`): cada uno acepta `none`, `keyboard`, `auto`/`gamepad`
  (primer mando disponible) o un GUID de SDL concreto. La asignación por asiento se lee de
  `game.toml` `[controller] p1_device` / `p2_device` (existen hasta `p5_device`).
- Ruta de teclado disponible (`pad_from_keyboard`, `keybinds.ini`), aunque `keybinds.ini` aún
  no se ha generado.

### Pendiente
Prueba física con GameSir T4n Lite (mando encendido antes de lanzar), y con dos mandos para
comprobar asignación a dos asientos. Sin tocar overlays.

### Sesión 3 (continuación) — prueba física con GameSir T4n Lite

- **El mando no funcionaba y no era problema de Linux ni de SDL.** La sonda
  `tests/diagnostico/sdlprobe.c` demostró que SDL enumeraba y leía el mando
  (`Generic X-Box pad`, GUID `03008665373500004010000000010000`), mientras que el juego recibía
  `0xFFFF` constante.
- **Causa raíz** (`runtime/src/main.cpp`): el asiento 1 se inicializa a `"auto"` solo bajo
  `#if defined(PSX_DEBUG_TOOLS)`, macro que **no define ninguna de nuestras dos builds**
  (la release define `PSX_NO_DEBUG_TOOLS=1`; la debug, ninguna). Sin ella, el asiento cae en
  `"keyboard"` y `open_player()` nunca abre el mando.
- **Corrección mínima, sin tocar el framework**: `game.toml` → `[controller] p1_device = "auto"`.
  Reconstruido `build-debug` y relanzado.
- **Verificación**: `pad_status` pasó de `0xFFFF` fijo a registrar las palabras reales
  (`0xFFEF` arriba, `0xFFDF` derecha, `0xFF7F` izquierda, `0xDFFF` Círculo, `0xBFFF` Cross,
  `0xEFFF` Triángulo). El usuario jugó una partida completa con el mando (GAME OVER,
  Mitsurugi vs Li Long).
- **Duda resuelta del usuario**: confirmar con **B** y no con A es lo correcto. `input.ini`
  mapea por posición física (A=×, B=○, X=□, Y=△) y Soul Blade usa ○ para aceptar; ○ está en la
  posición este, que en un mando Xbox es B.
- **Pendiente**: segundo mando y partida de dos jugadores; reportar el `#if` invertido al
  proyecto original (no se ha parcheado el submódulo).

### Sesión 3 (cierre) — matices del mando medidos

- `pad_status` por TCP **no sirve para pulsaciones cortas**: devuelve el último intercambio
  serie, así que un tap de START cae entre muestras (probado a 250 ms y a 40 ms; nunca apareció
  `0xFFF7`). El usuario confirma que START funciona en el juego, así que la limitación es del
  instrumento de medida, no del juego. Para direcciones mantenidas sí es fiable.
- El receptor 2.4G del GameSir **no numera los botones igual que el mapeo genérico de Xbox**:
  SDL declara `back:b6,start:b7` para el GUID `03008665…`, pero a nivel de evento se observa
  joystick 6 → gamepad 4 (LB) y joystick 7 → gamepad 6 (BACK), y `gamepad button=7` no aparece
  nunca. Conclusión práctica: el botón físico se verifica jugando, no por el número de SDL.
- SELECT sin verificar (puede no reportarlo el mando o no tener función en el juego).
- Sonda nueva: `sdlprobe` (en `tests/diagnostico/`) y `pad_poll_fast.py` (muestreo a 40 ms).

### Corrección de método (mismo día)

El primer `pad_poll_fast.py` usaba un **socket persistente** contra el servidor de depuración.
Ese servidor atiende **un comando por conexión** y cierra: se obtuvo 1 muestra y después
`Broken pipe` en bucle. Conclusión errónea que llegué a escribir: «el muestreo no captura
pulsaciones cortas». Lo correcto es que **el instrumento estaba roto**.

- Corregido: conexión nueva por muestra. Validado con 84 muestras y 0 fallos en 5 s a 50 ms.
- Copia en `tests/diagnostico/pad_poll_fast.py`.
- La medición de START por TCP queda **sin repetir**; la evidencia válida de que START funciona
  es la comprobación del usuario en partida (pausa y navegación).

### Sesión 3 (dos mandos) — asignación y partida 2P

- `game.toml`: añadido `[controller] p2_device = "auto"`. Con un solo mando, el asiento 2 se
  queda sin dispositivo (no roba el del asiento 1); con dos, cada uno coge el suyo.
- **Asignación medida**: pulsando izquierda solo en el mando 1 → `slot0 0xFF7F` ×3; solo en el
  mando 2 → `slot1 0xFF7F` ×3. Sin cruces.
- **Partida 2P jugada** en VS BATTLE MODE (Taki vs Voldo, modo versus sin rótulo STAGE). Durante
  la sesión `slot0` acumuló 34 pulsaciones no neutras y `slot1` 6.
- **START del mando físico, verificado por fin**: aparece `0xFFF7` en `slot0`. La duda anterior
  era del instrumento (socket persistente contra un servidor de un comando por conexión).
- Herramienta nueva: `pad_two.py` (muestrea ambos asientos con conexión por muestra).

- **Simultaneidad medida**: en el muestreo de 55 s (1224 muestras, 0 fallos) hay un instante,
  46,01 s, con `slot0` y `slot1` en `0xDFFF` a la vez: los dos jugadores pulsando ○/B
  simultáneamente. Los dos puertos se leen de forma independiente.
- Recuento de la sesión: `slot0` 34 pulsaciones no neutras (START ×5, ○ ×4, △ ×2, cruceta),
  `slot1` 6 (el jugador 2 se incorporó más tarde).

- **Evidencia del propio runtime** (`logs/run-pad-dos.log`): al arrancar registra
  `opened controller for slot 1 (instance 6)` y `opened controller for slot 2 (instance 7)`.
  En la instancia anterior al arreglo D10 esa línea no aparece nunca (0 ocurrencias), que es
  la firma del bug de la macro invertida.
- **Salvedad**: en el apagado el runtime reabre los mandos y ambos asientos llegan a apuntar
  a la misma instancia (6 y luego 9). Ocurre tras `executing from PC=0xBFC00000` y justo antes
  de `exit=0`: es el camino de cierre, no la partida. Las mediciones de asignación y la partida
  2P son anteriores y válidas, pero queda anotado que la reapertura no respeta la reserva por
  asiento.

## Sesión — ingeniería inversa, métricas y bloque 0x10D00 (24 oct 2026, noche)

**Objetivo:** auditar el estado, integrar REA, aclarar las métricas de intérprete y atacar el
siguiente punto caliente.

**Hecho:**
- Auditoría: workspace limpio en `ae8392a`; proyecto en `9f74cde` con cambios propios (commit
  `4faa5a0`); framework en `31df2e1e`; builds release (39 MB), debug (160 MB), estática (39 MB)
  y combinada (161 MB); 177 shards en `build-debug/cache`; almacén de capturas volátil (1 región
  en el fichero principal, 199 en el histórico `.d`).
- **REA instalado y habilitado** (`hermes plugins install rea` + `enable`). Node v26.7.0 y `npx`
  presentes. Aviso: los servidores MCP **cargan en la siguiente sesión**, así que en esta no hubo
  herramientas de REA. No se ejecutó `npx rea-agents setup --client hermes` (prohibido por el
  brief: pisaría la configuración del plugin).
- Métricas aclaradas y documentadas (§22 de `overlays-aot.md`): los «hits» son entradas de bloque
  al intérprete, acumulativas por sesión; el 493× es el cociente de ese contador, no FPS. Se
  declara **no medido** el rendimiento real (FPS/CPU/tiempos de carga).
- Punto caliente nuevo identificado: `0x80010D3C`/`0x80010D94` = copia de 0x300 bytes del propio
  EXE (desde `0x10F60`, `sha256 227f606c…`), invisible al gancho de captura porque la copia la
  hace la CPU, no el DMA de CD.
- Captura creada a mano desde volcado verificado + 5 shards compilados (0 fallos).
- Mecanismo del cargador leído en `overlay_loader.c`: `checked` es una memo de regiones con primer
  fallo de despacho, no un barrido al arrancar.

**Pendiente inmediato (próxima sesión):**
1. Comprobar REA: `skill_view('reverse-engineer-anything')` y localizar sus herramientas MCP.
2. Cerrar la verificación de `0x10D00`: llegar a menú/combate en sesión continua y confirmar que
   `0x00010D00` entra en `checked` y que sus hits caen a 0.
3. Con REA sobre `SLUS_002.40`: seguir la rutina que copia `0x10F60 → 0x10D00`, identificar el
   cargador y ver si hay más bloques copiados por CPU que nunca se capturan (candidatos: cualquier
   región con hits altos y sin captura en el histórico).
4. Regresiones pendientes de la build combinada: guardado/carga por interfaz y segundo arranque.

### Ampliación — bloque 0x10D00 resuelto estáticamente

- Script reproducible `tests/diagnostico/verify_10d00.py` con todas las coordenadas.
- Traza de arranque (`PSX_WTRACE_BOOT_RANGES`): la copia son 192 palabras contiguas, PC `0x8B8` del
  BIOS, frame 51, pila del juego.
- Desensamblado: biblioteca de matemáticas GTE (15 `lwc2`, 10 `swc2`, 5 `ctc2`, 2 `div`) con tres
  `jr $ra` en `+0xAC`, `+0x2AC`, `+0x2B4`. Las 4 seeds son continuaciones interiores.
- Pendiente: punto de llamada del juego (los `$ra` son del BIOS), despacho y corrección semántica.

### Ampliación — validez de las tarjetas de memoria

- Creada `tests/diagnostico/check_mcd.py` (valida XOR por frame y lista directorio).
- `card1.mcd` (con guardado): **11 frames invalidos**, exactamente los del bloque del save (64-74).
  `card2.mcd` (vacia): 1024/1024 validos.
- Causa: `memcard_write_sector()` copia sin validar; el XOR solo se calcula al formatear. En hardware
  real esa escritura se rechazaria. Documentado como D12 y T18, sin "reparar" la imagen.
- El `Soul Blade.psv` original **no es una tarjeta**: 3.809.916 B con cabecera `ARS2` ("ARS2CPU"),
  es un estado, no un memory card. Confirma que no debia usarse como tarjeta de pruebas.

## Turno autónomo nocturno — 2026-10-25 (01:05 → )

Detalle completo en `logs/turno-autonomo-2026-10-25.md` (no versionado: `logs/` está ignorado).

**Memcard / checksums**
- Instrumentación `PSX_MC_WRITE_LOG=1` y validación opt-in `PSX_MC_STRICT_FRAME_CHK=1` en
  `sio.c` (commit del framework `66cbc3a2`), con test nuevo de 7 comprobaciones.
- Probado que el camino de escritura es fiel y que la escritura de arranque (sector 63) es
  coherente; el modo estricto no altera el arranque.
- **Corrección de mi diagnóstico previo**: las tarjetas de ejemplo del framework tienen el mismo
  tipo de `0x7F` incoherente en bloques de datos ⇒ no hay defecto demostrado (D14).

**Infraestructura de pruebas**
- Cinco targets de test no enlazaban en esta revisión (fallo preexistente,
  `memcard_last_flush_result`). Stub añadido (commit `daa85f7a`): **10/10 en verde** en sio/card.

**Estabilidad**
- Soak release: 8:34, 31.006 frames, 0 errores, SIGTERM→exit 0, RSS con meseta ~350 MB, 0 muestras
  < 59 fps (T22).
- Soak release con escalado 1080p: en curso al cerrar, `logs/soak-hd.log`.

**Calidad**
- 1080p (5x) y 4K (9x) de resolución interna sostienen 1,00x en escenas ligeras; no activado por
  defecto por falta de verificación visual (D15/T23).

**Empaquetado (solo requisitos)**
- `docs/requisitos-empaquetado.md`: contratos de los scripts, resolución de rutas, diseño de AppRun,
  glibc 2.38, lista de bibliotecas y qué debe empaquetarse.

**Herramientas nuevas**
- `tests/diagnostico/check_mcd.py` (valida frames y directorio de una tarjeta).
- `tests/diagnostico/dispatch_report.py` (clasifica PCs interpretados: hueco / sin candidato / CRC).

### Ampliación del turno — suite de pruebas y caché de la release

- **La release no lleva `cache/`**: `build-release/` se ejecutó 8:34 sin un solo shard y a 1,00x.
  Es la confirmación más directa de que la cobertura nativa no cambia el rendimiento percibido.
  Añadido a `docs/requisitos-empaquetado.md` como requisito (copiar la caché o enlazar estático).
- **Suite del framework**: 3 fallos preexistentes de enlace/estándar arreglados (D16); área
  sio/card/memcard 11/11 en verde; el resto de fallos documentados como deuda ajena al juego (T25).

### Ampliación — regresión de la build combinada

Dos arranques consecutivos: estado del cargador idéntico (`checked` con `0x96000`, `loads=4`,
`registered=107`), despachador estático con 197 entradas y 10.799 despachos, **los dos mandos
conectados** y cierre limpio `exit=0` en ambos. Tarjetas sin cambios (T27).
