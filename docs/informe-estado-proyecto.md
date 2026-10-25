==============================================================================
 INFORME DE ESTADO - PROYECTO SOUL BLADE (PORT NATIVO LINUX)
 Fecha: 24 de octubre de 2026
 Alcance: desde la auditoria inicial hasta la integracion y prueba de los mandos
==============================================================================

Este documento es autosuficiente: describe el estado real del proyecto, la evidencia
que lo respalda, los errores encontrados (incluidos los mios), lo que queda abierto y
como reproducir todo. Los datos son de ejecucion local; no hay nada estimado.


------------------------------------------------------------------------------
1. RESUMEN EJECUTIVO
------------------------------------------------------------------------------

Estado: se ha conseguido un PORT NATIVO x86-64 de Soul Blade que arranca, detecta el
disco del usuario, permite salir del modo attract, navegar menus, entrar en Arcade,
insertar moneda, elegir personaje, jugar un combate real con pausa 1P, usar mando,
reproducir audio, guardar y cargar en memory card y cerrarse de forma ordenada.

NO es emulacion ni Wine: es recompilacion estatica MIPS R3000A -> C -> binario nativo.

Lo que falta para cerrar el hito con evidencia completa:
  - Sesion de estabilidad cronometrada (pospuesta expresamente por el usuario).
  - Comparacion con una referencia de PlayStation 1 (no hay emulador de referencia
    instalado ni se ha ejecutado el disco en uno).
  - Teclado en partida (ruta existe, no validada).
  - Boton SELECT (sin funcion conocida en este juego).
  - Explicacion del silencio de los menus de opciones y memory card.
  - Los overlays del juego siguen ejecutandose por interprete (no se han optimizado,
    por decision explicita de no tocar rendimiento mientras hubiera pruebas abiertas).


------------------------------------------------------------------------------
2. EQUIPO Y ENTORNO (medido, no heredado de documentacion)
------------------------------------------------------------------------------

  Distribucion .... CachyOS x86-64 (Arch)
  Kernel .......... 7.3.0-4-cachyos
  Escritorio ...... KDE Plasma 6.8.1, KWin sobre Wayland
  CPU ............. AMD Ryzen 7 5800X (8 nucleos / 16 hilos, hasta 4,85 GHz)
  RAM ............. 15,53 GiB
  GPU ............. AMD Radeon RX 7700 XT (Navi 32), 11 GiB VRAM, RADV/Mesa 26.2.5
  Raiz ............ Btrfs, ~495 GB libres
  Herramientas .... cmake 4.4.4, ninja 1.13.2, gcc 16.2.1, clang 23.1.3,
                    python 3.14.7, SDL3 3.4.18, Vulkan 1.4.363, ccache 4.14.1
  Paquetes instalados para el proyecto: NINGUNO (todo estaba presente).


------------------------------------------------------------------------------
3. EL DISCO DEL JUEGO (originales intactos)
------------------------------------------------------------------------------

  Ruta .... <project>/Soul Blade V1.1/
  Archivos  Soul Blade (v1.1).bin   527.412.480 bytes (224.240 sectores de 2352)
            Soul Blade (v1.1).cue   83 bytes, 1 pista MODE2/2352
            Soul Blade.psv          3.809.916 bytes (guardado; NO usado ni modificado)

  SHA-1 ... e1a48d3e5c3614be1a5f3fe7f1f4036dbc6c5b94
  SHA-256 . e1b2931759985322b1c863c5e9adfeb12272447a4e244e2f906125bf5a05b120
  MD5 ..... 055175fbf6e6e48caea1fad0664f42af
  CRC32 ... aa74b3c9

Identidad obtenida por sonda propia (no por el nombre del archivo):
  Volumen ISO9660 ..... SOULBLADE
  Ejecutable de boot .. SLUS_002.40 (1.034.240 bytes) -> serial SLUS-00240 (USA)
  Cabecera PS-X EXE ... load 0x80010000, entry 0x80010FBC, text 0x000FC000,
                        stack 0x801FFFF0
  SHA-256 del boot .... 51b14b312a79f5aec13167cfc6426c97baf0ff713cfc66e9ab4d28991a8f3b6e
  Huella TOC .......... f28e869b8d07728a4b86cfe89a89872013f1a7331b483b1346677957205da19c

Contenido del ISO:
  SYSTEM.CNF 69 B | SLUS_002.40 1.034.240 B | SOUL.BNS 25.845.760 B
  SOULOVL.BNS 4.704.256 B | SOULSYS.BNS 620.544 B | SOULXA.XAS 398.993.408 B
  3MIN.DMY 27.688.960 B

Salvedad honesta: la huella no se ha cotejado contra una base de datos Redump (no hay
verificacion remota hecha). La identidad es coherente con Soul Blade (USA) v1.1, pero se
clasifica como hipotesis fuerte, no como hecho verificado contra Redump. El dump es de
una sola pista; eso bloquea las puertas multi-pista de netplay, sin efecto en local.


------------------------------------------------------------------------------
4. DE DONDE SALE EL CODIGO: EL REPOSITORIO DEL AUTOR NO EXISTE
------------------------------------------------------------------------------

Se intento usar el proyecto publico que existia para este juego
(fabioap-cpu/SoulBlade_Recomp):

  git ls-remote ........ pide credenciales (GitHub responde 404 a inexistente/privado)
  API /repos ........... 404
  API /releases ........ 404
  La cuenta existe ..... si (id 68659468), con WWF-SmackDown-2-Recomp,
                        Forza-Horizon-2-Recomp, Burnout-Revenge-Recomp
  recomp.fyi ........... lo lista con la anotacion literal "repo missing"

Conclusion: repositorio retirado o privado. No se clono ningun repositorio de nombre
parecido (riesgo de suplantacion). El proyecto del juego se construyo de cero con el
scaffolding oficial del framework.

Del proyecto WWF del mismo autor (publico, solo README y punteros de submodulo) se
extrajo el metodo y el pin que usaba: psxrecomp en el commit 20ae6db9 (25-ago-2026),
que resulto ser ANCESTRO de la HEAD usada aqui.


------------------------------------------------------------------------------
5. FRAMEWORK Y DECISIONES TECNICAS
------------------------------------------------------------------------------

Framework: RetroPortingToolKit/psxrecomp
  Commit ...... 31df2e1e0e0a6525733e68ff70e72ecbef84bb09 (2026-10-22)
  git describe  nightly-870-g31df2e1e   (RELEASE_NOTES v0.3.2-alpha)
  Submodulos ... lib/recomp-net e5305930..., lib/retcomm-rbengine 2a03e736...
  Licencia ..... PolyForm Noncommercial 1.0.0 (Copyright 2026 Matthew Stanley)
  BIOS incluida  OpenBIOS (PCSX-Redux) MIT, como bios/openbios.bin

Decisiones y por que:

  D1 Usar la HEAD actual en vez del pin de agosto: el pin es ancestro de la HEAD
     (comprobado con git merge-base --is-ancestor), asi que la HEAD incluye todo lo
     suyo mas correcciones de soporte Linux.

  D2 Proyecto de juego propio (source/SoulBladeRecomp) en lugar de esperar a un
     repositorio inaccesible. Riesgo asumido: el trabajo de seeds y overlays del autor
     no se puede reutilizar.

  D3 Sin recomp-ui (lanzador), sin netplay (dump de una pista), sin CI (no se publica).

  D4 Herramientas del sistema en vez del "toolchain portable" del CLI.

  D5 Estandar C++ fijado a 17 (obligatorio, ver 6.2).

  D6 El CUE original se usa por ruta absoluta; no se copia el BIN al proyecto.

  D7 Ningun paquete instalado en el sistema.

  D8 Las memory cards viven en la raiz del proyecto (saves/), compartidas por las dos
     builds: sirve para comprobar que un guardado de una se carga en la otra, pero
     impide dos instancias guardando a la vez.

  D9 Scripts en bash con set -euo pipefail y rutas entrecomilladas (el workspace tiene
     espacios en los nombres).

  D10 El mando no se abria por una macro invertida del framework (ver 6.3).


------------------------------------------------------------------------------
6. TRES FALLOS REALES ENCONTRADOS Y COMO SE RESOLVIERON
------------------------------------------------------------------------------

6.1 EL CLI NO GENERA EN LINUX (fallo del framework, esquivado sin parchear)

  Sintoma: psxrecomp_cli.py generate aborta con
           "Toolchain ensure succeeded but bin/ is not usable for emitters"
  Causa:   activate_embedded_toolchain() devuelve siempre False fuera de Windows
           (if sys.platform != "win32": return False), pero el flujo interpreta que la
           descarga del pack portable tuvo exito y aborta.
  Solucion: --no-toolchain-download (fuerza la rama de cmake/ninja del sistema).
  Estado:   documentado como incidencia upstream; el submodulo no se ha parcheado.

6.2 LA BUILD RELEASE NO COMPILABA (estandar C++)

  Sintoma: errores de std::u8string en gpu_hd_textures.cpp y
           duckstation_texture_pack.cpp.
  Causa:   el runtime heredaba el estandar por defecto de GCC 16, que interpreta u8""
           como char8_t (C++20). El framework documenta C99 + C++17, y
           runtime/CMakeLists.txt lo fija, pero el camino de proyecto de juego no.
  Solucion: -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON.

6.3 EL MANDO NUNCA SE ABRIA (fallo del framework, corregido por configuracion)

  Sintoma: SDL ve el mando y sus pulsaciones, pero el juego recibe 0xFFFF constante.
  Causa:   runtime/src/main.cpp elige el dispositivo por asiento asi:

             #if defined(PSX_DEBUG_TOOLS)
                 player_device[i] = (i == 0) ? "auto" : "none";      // mando SDL
             #else
                 player_device[i] = (i == 0) ? "keyboard" : "none";  // teclado
             #endif

           PSX_DEBUG_TOOLS no lo define NINGUNA de las dos builds: la release define
           PSX_NO_DEBUG_TOOLS=1 (226 apariciones en build.ninja) y la debug no define
           ninguno. El resto del framework usa la convencion contraria
           (#ifndef PSX_NO_DEBUG_TOOLS), asi que ese #if esta invertido. Resultado: en
           ambas builds el asiento 1 caia en teclado.
  Solucion: game.toml -> [controller] p1_device = "auto" y p2_device = "auto"
           (claves soportadas: none | keyboard | auto/gamepad | GUID de SDL).
  Estado:   el #if invertido queda pendiente de reportar aguas arriba.


------------------------------------------------------------------------------
7. PROYECTO, GENERACION Y COMPILACION (numeros reales de build)
------------------------------------------------------------------------------

Estructura:
  <project>/
    Soul Blade V1.1/      originales (intactos, fuera de Git)
    docs/                 auditoria, plan, decisiones, bitacora, estados, cierres
    tests/                PRUEBAS.md y tests/diagnostico/ (sondas)
    logs/                 logs completos de cada compilacion y ejecucion
    build.sh / run.sh     compilacion y ejecucion
    source/psxrecomp/     framework (clon de referencia)
    source/wwfref/        proyecto WWF del mismo autor (solo para leer el metodo)
    source/SoulBladeRecomp/  proyecto del juego (repo propio)

Cifras de compilacion:
  Recompilador del framework .... 348/348 objetivos
  Scaffolding del proyecto ...... completado (commit inicial 04a49cd)
  Emisores del proyecto ......... 69/69
  Generacion del juego .......... OpenBIOS recompilado +
                                  59 shards, 2.409.187 lineas de C,
                                  tabla de dispatch de 3.994 entradas,
                                  1.453 seeds iniciales (entry + destinos JAL)
  Build release ................. 319/319 -> SoulBlade_Recompiled, 40 MB
  Build debug ................... 383/383 -> 167 MB (RelWithDebInfo + servidor TCP)

El binario es nativo de verdad:
  ELF 64-bit LSB pie executable, x86-64, dynamically linked, interpreter
  /lib64/ld-linux-x86-64.so.2, enlazado contra SDL3, libGLX/libOpenGL y libcrypto del
  sistema. No hay capa Wine ni interprete de PS1 ejecutando el juego.

Reproducibilidad: recompilar en incremental produce el MISMO BuildID
(3dca9176b6640e0a1de75e48d6557b264d997b25) en 0,9 s. Scripts:
  ./build.sh            -> build-release
  ./build.sh --debug    -> build-debug (servidor TCP en 127.0.0.1:4370)
  ./run.sh [--debug] [--headless] [--disc ...]


------------------------------------------------------------------------------
8. QUE ESTA PROBADO Y CON QUE EVIDENCIA
------------------------------------------------------------------------------

Marcador de niveles usado en el proyecto (para no confundir una demo con una partida):

  1 Demostracion automatica (attract)   -> CPU vs CPU, rotulo INSERT COIN, la cruceta
                                           no hace nada, vuelve sola al titulo
  2 Menu interactivo                    -> lista ARCADE/VS/TEAM/TIME/SURVIVAL con
                                           resaltado que responde a la cruceta
  3 Entrada efectiva con START          -> START saca del attract al menu
  4 Seleccion de modo                   -> Circulo (O) sobre ARCADE MODE
  5 Seleccion de personaje              -> rejilla de retratos con marca 1P
  6 Combate real cargado                -> VS STAGE 1 y luego "BATTLE 1" con HUD
  7 Control efectivo                    -> la entrada cambia el estado segun la
                                           direccion y START abre "1P PAUSE"

  T1  Compilacion reproducible ............ SUPERADA (6/6, mismo BuildID)
  T2  Binario nativo, no Wine ............ SUPERADA (file + ldd)
  T3  Arranque y detecta el disco ........ SUPERADA (serial, region NTSC-U)
  T4  BIOS LLE y ejecucion del juego ..... SUPERADA (OpenBIOS, PC=0xBFC00000,
                                            intro FMV con MDEC, menu)
  T5  Menu y navegacion .................. SUPERADA (el resaltado cambia; verificado
                                            por diff de pixeles en la zona de la lista)
  T6  Inicio de combate REAL ............. SUPERADA (secuencia completa pantalla a
                                            pantalla; prueba dura: menu "1P PAUSE")
  T7  Control del personaje .............. PARCIAL (ver 8.1)
  T8  Ritmo .............................. SUPERADA (cronometro del juego 0'20"19 ->
                                            0'30"26 en 10 s de reloj de pared)
  T9  Audio .............................. SUPERADA con experimento de control (8.2)
  T10 Guardado en memory card ............ SUPERADA (SAVE OK + entrada en la tarjeta)
  T11 Salida limpia ...................... SUPERADA (exit=0 por quit TCP y por SIGTERM)
  T12 Segundo arranque y carga ........... SUPERADA (proceso nuevo, LOAD OK)
  T13 Estabilidad en sesion larga ........ PARCIAL / POSPUESTA
  T14 Mando GameSir (uno) ................ SUPERADA
  T15 Dos mandos y partida 2P ............ SUPERADA

8.1 CONTROL DEL PERSONAJE - la parte mas delicada

  Metodo: savestate del emulador para partir exactamente del mismo frame y comparacion
  de capturas pixel a pixel. El emulador es determinista, lo que hace la medida exacta.

    neutro vs neutro (mismo estado, sin entrada) .....      0 pixeles distintos
    neutro vs mantener IZQUIERDA 3 s ................. 53.327 pixeles distintos
    neutro vs mantener DERECHA 3 s ................... 65.122 pixeles distintos
    IZQUIERDA vs DERECHA ............................. 41.321 pixeles distintos

  Control negativo en el attract: mantener IZQUIERDA y mantener DERECHA dio capturas
  IDENTICAS (0 pixeles). Es decir: en la demo la cruceta no altera nada; en partida si,
  y de forma dependiente de la direccion.

  Limitacion declarada: no se ha medido el desplazamiento en pixeles del personaje
  porque la camara sigue y zoomea a los luchadores, de modo que la posicion en pantalla
  no es una medida directa.

8.2 AUDIO - con control para descartar autoengano

  Primer registro (menu de tarjeta, 6,14 s) ............ amplitud maxima 0,000000
  Control por la misma via (tono 440 Hz, vol 0,3) ...... amplitud maxima 0,300018
  Registro en combate real ............................. amplitud maxima 0,999969
                                                         (tramos de 0,79 y 0,72)

  Es decir: la cadena de captura no enmascara silencio (el tono se registra a su
  volumen) y el juego produce audio real en partida. Los menus de opciones y memory
  card son mudos; falta determinar si es BGM desactivado por defecto o por diseno.

8.3 GUARDADO Y CARGA

  Tarjetas: source/SoulBladeRecomp/saves/card1.mcd y card2.mcd, 131.072 B, cabecera MC,
  formateadas al arrancar.
  Guardado: OPTION > MEMORY CARD > SAVE CONFIG & RECORDS > Slot 1 > START > "SAVE OK!"
            card1.mcd pasa de md5 a7b6af52... a 3bea444d... y aparece la entrada
            BASLUS-00240S_B_SAVE.
  Carga:    en un PROCESO NUEVO, LOAD CONFIG & RECORDS > Slot 1 > START > "LOAD OK!"
  Efecto colateral observado: tras la carga cambian 5 bytes en el frame de checksum del
  bloque 0 (0x1F80-0x1FFF, aparecen 4D 43 = "MC" y el checksum 0x0E). El contenido del
  save no se altera. Anotado como efecto a vigilar, no como fallo.
  El .psv original no se ha tocado ni usado.


------------------------------------------------------------------------------
9. MANDOS: CADENA COMPLETA Y LO QUE SE MIDIO
------------------------------------------------------------------------------

Arquitectura (leida en el codigo, no supuesta):
  - El runtime usa la API GameController/Gamepad de SDL3 (SDL_GameControllerGetButton,
    GetAxis, GetGamepadJoystick, GamepadButtonFromString), no joystick crudo.
  - Configuracion por input.ini junto al ejecutable:
      [controller] enabled = true, device = 0, deadzone = 3277
      [mapping] up=dpup down=dpdown left=dpleft right=dpright
                cross=a circle=b square=x triangle=y
                l1=leftshoulder r1=rightshoulder l2=lefttrigger r2=righttrigger
                l3=leftstick r3=rightstick start=start select=back
                ls_*/rs_* para los sticks analogicos
  - Dos asientos (PSX_MAX_PLAYERS=2); cada asiento acepta none | keyboard |
    auto/gamepad | GUID, configurable en game.toml [controller] p1_device..p5_device.
  - NO hay hotplug (no se maneja SDL_EVENT_GAMEPAD_ADDED): el mando debe estar
    conectado ANTES de lanzar.
  - Ruta de teclado disponible (pad_from_keyboard, keybinds.ini), sin validar en partida.

Deteccion (sondeo propio, tests/diagnostico/sdlprobe.c):
  joysticks detectados: 3
    [0] 'Ducky One 3 SF RGB'   isGamepad=0   <- el teclado expone un joystick; SDL lo
                                              descarta y no interfiere
    [1] 'Generic X-Box pad'    isGamepad=1   guid=03008665373500004010000000010000
    [2] 'Generic X-Box pad'    isGamepad=1   guid=03008665373500004010000000010000
  (los dos GameSir: mismo modelo, mismo GUID, instancias distintas)

Mapeo que SDL aplica a este receptor:
  a:b0 b:b1 x:b2 y:b3 back:b6 guide:b8 start:b7 leftstick:b9 rightstick:b10
  leftshoulder:b4 rightshoulder:b5 dpup/dpdown/dpleft/dpright como hat h0.*

Correspondencia de botones (por POSICION fisica, que es lo correcto):
  A (sur)   -> Cross (X)      -> cancelar en Soul Blade
  B (este)  -> Circle (O)     -> CONFIRMAR (Soul Blade usa O para aceptar)
  X (oeste) -> Square         -> ataque
  Y (norte) -> Triangle       -> ataque
  START     -> Start          -> menu / pausa 1P
  BACK      -> Select         -> sin funcion conocida en este juego
  La duda del usuario ("confirmo con B y no con A, es correcto?") se resolvio: si,
  es exactamente lo esperado por posicion.

Pruebas medidas:
  Un mando: el usuario jugo una partida completa (GAME OVER, Mitsurugi vs Li Long).
  Palabras PSX que llegan al juego (pad_status): 0xFFEF arriba, 0xFFDF derecha,
  0xFF7F izquierda, 0xFFBF abajo, 0xFF3F abajo+izquierda, 0xBFFF Cross, 0xDFFF Circle,
  0xEFFF Triangle, 0xFFF7 START.
  Asignacion por asiento (30 s, 661 muestras, 0 fallos):
    pulsando izquierda SOLO en el mando 1 -> slot0 0xFF7F x3
    pulsando izquierda SOLO en el mando 2 -> slot1 0xFF7F x3     (sin cruces)
  Partida 2P (55 s, 1224 muestras, 0 fallos, 73 cambios):
    slot0 34 pulsaciones no neutras (START x5, O x4, Triangulo x2, cruceta)
    slot1  6 pulsaciones (el jugador 2 se incorporo despues)
    SIMULTANEIDAD: a los 46,01 s ambos puertos marcan 0xDFFF en el MISMO instante ->
    los dos puertos se leen de forma independiente, no es un mando replicado.
  Partida 2P: VS BATTLE MODE, moneda con START en cada mando, Taki vs Voldo, modo
  versus sin rotulo STAGE.

Peculiaridad del receptor 2,4 GHz (no es un fallo del proyecto): SDL declara
start:b7, pero a nivel de evento nunca aparece "gamepad button=7"; los pares observados
son joystick 6 -> boton 4 (LB) y joystick 7 -> boton 6 (BACK). Por eso el numero de SDL
no sirve para identificar el boton fisico en este mando: hay que verificarlo jugando.


------------------------------------------------------------------------------
10. ERRORES DE METODO QUE YO MISMO COMETI (para que se valoren con contexto)
------------------------------------------------------------------------------

10.1 Confundi el modo attract con una partida jugada. En el primer informe presente
     combates CPU vs CPU como si fueran partidas del usuario. El usuario lo corrigio.
     Se reescribieron las pruebas, se creo docs/estados-de-juego.md con la escala de 7
     niveles y se anadio la prueba de "1P PAUSE" como discriminador objetivo.

10.2 Un muestreo del mando con socket persistente contra el servidor de depuracion
     produjo "Broken pipe" en casi todas las muestras y concluí (mal) que "el muestreo
     no captura pulsaciones cortas". La causa real: el servidor atiende UN COMANDO POR
     CONEXION y cierra. Corregido abriendo conexion por muestra; validado con 84, 661 y
     1224 muestras y 0 fallos.

10.3 Un "pgrep -f" coincidio con mi propia linea de comandos y mate mi shell. Ahora se
     filtra con "ps | grep -F ... | grep -v grep".

10.4 Di que el SIGTERM cerraba sin volcado ordenado; el codigo de salida real era 0.
     Corregido en docs/cierres-y-codigos.md.

10.5 El examen del frame de checksum de la tarjeta tras la carga (5 bytes) se documento
     como efecto a vigilar en lugar de presentarlo como normal.


------------------------------------------------------------------------------
11. HERRAMIENTAS DE DIAGNOSTICO PROPIAS (en tests/diagnostico/)
------------------------------------------------------------------------------

  sdlprobe.c ......... enumera joysticks/gamepads y, en modo escucha, imprime cada
                       pulsacion de SDL. Separa "el sistema no ve el mando" de "el
                       runtime no lo usa".
  pad_poll_fast.py ... muestrea pad_status a 40-60 ms (conexion por muestra:
                       obligatorio, el servidor cierra tras cada comando).
  pad_two.py ......... muestrea los DOS asientos con marca de tiempo, para atribuir
                       cada pulsacion a un mando concreto.

Ademas se usa el servidor de depuracion del runtime (TCP 4370, solo en build debug):
  press <padword> <frames>, savestate op=save|load slot=N, screenshot, pad_status,
  savestate_status, quit, dirty_ram_stats, cd_read_log, y una veintena mas.


------------------------------------------------------------------------------
12. ESTADO DE LA DOCUMENTACION Y GIT
------------------------------------------------------------------------------

Documentos (raiz del workspace):
  docs/auditoria-inicial.md .... sistema, disco, repos, licencias, incidencias
  docs/plan.md ................. fases y estado
  docs/decisiones-tecnicas.md .. D1..D10 con alternativas y motivos
  docs/bitacora.md ............. sesiones 1, 2 y 3 con comandos y resultados
  docs/estados-de-juego.md ..... escala attract/partida y marcadores
  docs/cierres-y-codigos.md .... codigos de salida y correccion del T11
  tests/PRUEBAS.md ............. T1..T15 con estado y evidencia
  tests/diagnostico/ ........... sondas y README

Git (local, sin push, sin publicar nada):
  Workspace .... e62971e -> b70f551 -> c4ac697 -> c7c661e -> 6971840 -> 2d34c84 ->
                 e6948df -> 5f5d763 -> e6e3078 -> d9deae4
  Juego ........ 04a49cd -> 58592fa -> fb03624 -> 9f74cde

  Comprobado que NO hay versionado ningun .bin/.cue/.psv/.mcd ni BIOS comercial
  (git ls-files y git check-ignore). Los .mcd estan excluidos por .gitignore.


------------------------------------------------------------------------------
13. RIESGOS Y LIMITACIONES ABIERTAS
------------------------------------------------------------------------------

  R1  Overlays ejecutandose por interprete. Funciona y va practicamente a tiempo real
      (medido con el cronometro del juego), pero es el margen de mejora grande y esta
      pendiente a proposito. Hay 10 regiones de overlay capturadas con seeds en
      build-debug/overlay_captures.json.
  R2  Sin referencia de PS1 no se puede afirmar nada sobre fidelidad grafica, de audio
      o de timing frente al original.
  R3  Dump de una sola pista: bloquea netplay y no permite verificar el disco contra
      Redump.
  R4  Las dos builds comparten directorio de tarjetas (D8): no se pueden tener dos
      instancias guardando sin pisarse.
  R5  Sin hotplug: cambiar de mando exige relanzar.
  R6  El bug del #if invertido y el del CLI siguen en el framework: cualquier proyecto
      nuevo sobre psxrecomp en Linux se los encontrara.
  R7  SELECT sin funcion conocida; teclado sin validar en partida.


------------------------------------------------------------------------------
14. COMO REPRODUCIRLO DESDE CERO
------------------------------------------------------------------------------

  cd "<project>"
  ./build.sh --debug                 # o ./build.sh para release
  ./run.sh --debug                   # abre ventana y servidor TCP 4370
  ./run.sh --headless                # sin ventana (diagnostico)

  Regenerar el codigo del juego (solo si hace falta):
  cd source/SoulBladeRecomp
  python3 psxrecomp/psxrecomp_cli.py generate --no-toolchain-download \
      --config game.toml --project-root . \
      --disc "<project>/Soul Blade V1.1/Soul Blade (v1.1).cue"

  Secuencia de juego por inyeccion (build debug, sin mando):
    press 0xFFF7 4     # START: salir del attract
    press 0xDFFF 4     # O: entrar en ARCADE MODE
    press 0xFFF7 4     # START: insertar moneda (aparece marca 1P)
    press 0xDFFF 4     # O: confirmar personaje -> VS -> BATTLE 1
    press 0xFFF7 4     # START dentro del combate -> menu "1P PAUSE"


------------------------------------------------------------------------------
15. CONCLUSION
------------------------------------------------------------------------------

Port nativo funcional y jugable con mando, con las funciones principales verificadas
por medicion: compilacion reproducible, binario ELF nativo, disco aceptado, attract ->
menu -> arcade -> combate real, control direccional causal (con control negativo en el
attract), pausa 1P, audio en partida con experimento de control, guardado y carga en
memory card en proceso nuevo, cierre ordenado con exit=0, uno y dos mandos con
asignacion por asiento y simultaneidad medida.

Lo que falta no es "que compile": es cerrar evidencia (estabilidad cronometrada y
referencia PS1) y decidir si se aborda el interprete de overlays.

==============================================================================
