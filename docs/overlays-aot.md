# Overlays: inventario verificado y plan AOT

Sesión de optimización. Todo lo de aquí está medido en este equipo; lo que no se pudo
verificar aparece como tal.

## 1. Corrección del dato de partida

El enunciado de la fase decía «aproximadamente diez regiones de overlay capturadas».
**No es correcto**: `build-debug/overlay_captures.json` contiene **4 regiones**. El número
diez venía de un recuento mío anterior mal expresado. El histórico `.d` sí tiene 108
ficheros sueltos (capturas antiguas acumuladas).

| # | load_addr | tamaño | seeds |
|---|---|---|---|
| 0 | `0x80002000` | 8.196 B | 2 |
| 1 | `0x80017000` | 4.100 B | 4 |
| 2 | `0x80096000` | 12.292 B | 36 |
| 3 | `0x80102000` | 12.292 B | 8 |

## 2. Línea base de ejecución (build debug, modo attract)

`overlay_loader_status` con el juego corriendo:

```
regions_checked = 3      regions = 0        loads = 0
registered      = 0      file_found = 0     last_crc = 0x00000000
dispatch_native = 0      dispatch_interp_fallback = 62272
stale_blocked   = 0      reval_attempts = 0
cache_dir = build-debug/cache
```

Es decir: **cero despachos nativos y 62.272 fallbacks al intérprete**. La afirmación «los
overlays van por intérprete» queda confirmada con contadores, no de oídas. Ojo: 62.272 es el
contador acumulado de la sesión en ese punto, no un porcentaje de cobertura; el proyecto no
tiene un denominador fiable de instrucciones y no se inventa.

## 3. Mapa de carga real (registro de DMA de CD)

`cd_read_log` completo (13.613 entradas del anillo) filtrado sin el streaming de audio XA
(LBA 832, 12.588 lecturas):

| LBA | lecturas | destino físico (RAM) | qué es |
|---|---|---|---|
| 25 | 504 | `0x010000`..`0x10B800` | texto del EXE (código estático ya recompilado) |
| 530 | 49 | `0x12CE10`..`0x144E10` | datos de SOULSYS.BNS |
| 579 | 152 | `0x153E10`..`0x19F610` | datos de SOULSYS.BNS |
| 731 | 101 | `0x153E10`..`0x185E10` | datos de SOULSYS.BNS |

Comprobación del contenido de esos orígenes (leídos del BIN):

- LBA 530: tabla de offsets de 32 bits creciente (`3A`, `F0`, `5CC`, `76C`, `9A4`, `4B20`…).
- LBA 579: contiene `pBAV` = **VAB** (banco de audio de PSX) y tablas de tamaño.
- LBA 731: contiene los textos `AUTO SAVE FAILED`, etc.

Conclusión: en arranque y attract el juego lee **datos** (tablas, banco de audio, textos) de
SOULSYS.BNS a buffers altos. No son código y no son candidatos a recompilación.

## 4. ¿Las capturas son bytes literales del disco? Sector a sector

Se buscó cada sector de 2.048 B de cada región capturada en el BIN completo:

| # | sectores localizados | contiguos | lectura |
|---|---|---|---|
| 0 `0x80002000` | 0 / 5 | — | no aparece literalmente: transformada o generada en RAM |
| 1 `0x80017000` | 1 / 3 | — | coincidencia parcial aislada; no concluyente |
| 2 `0x80096000` | **6 / 7** | **sí: LBA 293..298** | **copia literal de 12.288 B** |
| 3 `0x80102000` | 2 / 7 | no | no es copia literal |

### Hallazgo principal

La región de `0x80096000` son **6 sectores consecutivos del disco (LBA 293..298)**. El
ejecutable `SLUS_002.40` empieza en el LBA 24, así que ese contenido es el tramo del propio
EXE en el offset **0x86800** (550.912) y 12.288 bytes de longitud.

Es decir: el juego **se copia un trozo de sí mismo** a `0x80096000` y lo ejecuta (la captura
tiene 36 seeds de ejecución verificada). Esa dirección cae dentro del rango de texto estático
(`0x80010000..0x8010C000`), así que en tiempo de ejecución sobrescribe código que el
recompilador emitió de forma estática. Es un patrón de «overlay en el sitio» y explica por qué
esa zona acaba en el intérprete.

Las regiones 0 y 3 no son copias literales: hay una transformación (posible descompresión o
reubicación) que **todavía no está identificada**, y no se va a inventar.

## 5. Qué ofrece el framework en esta revisión

`31df2e1e` incluye el pipeline AOT completo:

- `tools/aot_overlay_pipeline.py {extract,release,static}` con perfiles declarativos
  `psxrecomp AOT methods v1`. **No usa capturas como entrada**: crea un directorio nuevo y lee
  el disco original.
- Métodos relevantes para este caso: `fixed_address_files`, `fixed_address_extents`
  (`{file, file_offset, base, address, size, sha256}`), `packed_sector_members`,
  `sector_extent_members`, `aligned_lzss_banks`, `indexed_lzss_members`,
  `tagged_relocated_files`.
- `tools/audit_aot_cache.py` para auditar bytes/ABI/exports y cobertura nativa.
- `tools/compile_overlays.py` para la vía de caché dinámica (la que el runtime usa en
  producción), con guards por bytes originales.

El propio contrato avisa: «destinations are explicit evidence, never inferred from a
historical RAM capture». Para declarar un perfil AOT de esta juego haría falta establecer con
evidencia de cargador la dirección de destino de cada imagen, no solo verla en una captura.

## 6. Vía elegida y por qué

**Primera vía (en curso): caché dinámica con `compile_overlays.py`.**
Es el mecanismo que el framework usa en producción, se apoya en capturas (que ya tenemos) y
genera fragmentos nativos con guards de bytes. Es medible de inmediato con
`dispatch_native` / `dispatch_interp_fallback`.

Resultado de la comprobación en seco (`--check`):

```
built OK : 39    skipped : 0    FAILED : 0    (región 0x96000 y sus variantes históricas)
PSX_SHARD_RESULT ok=39 failed=0 skipped=0
```

**Segunda vía (pendiente, más profunda): perfil AOT estático.**
Requiere: identificar el cargador que coloca las imágenes en 0x80002000 / 0x80017000 /
0x80102000, documentar la transformación de las regiones que no son copia literal, y declarar
`fixed_address_extents` con `sha256` y evidencia de la dirección. Solo entonces tiene sentido
`aot_overlay_pipeline.py release --stage` con enlace `static`.

## 7. Riesgos identificados

- La región de `0x80096000` está **por debajo** del `overlay_region_floor = 0x10C000` que el
  runtime usa para decidir qué es overlay. Si el despacho nativo no consulta la caché para
  direcciones del rango de texto, estos 39 shards no se usarán y habrá que resolverlo por AOT
  estático o por configuración del floor. Es lo primero que hay que medir.
- El histórico `.d` mezcla capturas de sesiones distintas; compilar variantes antiguas puede
  producir shards que nunca se despachen. No es un error, pero infla el recuento.
- Sin comparación con referencia PS1 no se puede afirmar fidelidad de los shards nativos; solo
  ausencia de regresiones observables.

## 8. Primer lote integrado y medido (caché dinámica)

Compilación de las regiones capturadas a la caché del runtime:

```
python3 psxrecomp/tools/compile_overlays.py \
  --captures build-debug/overlay_captures.json --game-toml game.toml \
  --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --jobs 8 --out-dir build-debug/cache
```

Inventario resultante (8 shards, 1,3 MB): región `0x00110000` (1 variante) y `0x00111000`
(7 variantes históricas). Las variantes salen del histórico `.d`, no de la captura actual.

Mediciones con `overlay_loader_status`:

| Momento | regions | loads | registered | dispatch_native | interp_fallback |
|---|---|---|---|---|---|
| Línea base, attract, sin caché | 0 | 0 | 0 | **0** | 62.272 |
| Tras compilar, attract | 0 | 0 | 0 | 0 | 1.148.690 |
| Tras compilar, entrando en partida | 1 | 1 | 11 | **4** | 1.170.499 |
| Entrando en partida con `PSX_OVERLAY_AUTOCOMPILE_OFF=1` | 1 | 1 | 11 | **599** | 77.899 |

### Prueba de atribución

El contador `last_crc` (`0x27D09AEF`, `0x67D66A7C`) **no coincide con el nombre de ningún
`.so` de la caché**, así que por sí solo no atribuye nada. La prueba que sí atribuye es la
última fila: con `PSX_OVERLAY_AUTOCOMPILE_OFF=1` el runtime **no puede compilar** shards
nuevos, y aun así registra 11 funciones y despacha 599 veces por código nativo. Esos shards
solo pueden venir de la caché en disco.

### Cifra honesta de cobertura

599 de 78.498 despachos de overlay en esa ventana = **0,76 %**. No es un porcentaje de
instrucciones nativas del juego completo (no existe denominador fiable), es la proporción de
despachos de overlay que fueron nativos en ese tramo. Es pequeña y hay que decirlo así.

### Por qué es tan baja

Las capturas cubren 4 regiones y el código de overlay del juego es mucho mayor: los combates
cargan regiones desde SOUL.BNS en direcciones que aún no están capturadas. La caché solo puede
servir lo que se ha capturado y compilado. El siguiente paso no es tocar el framework, es
**ampliar la captura**: jugar modos, escenarios y personajes hasta acumular regiones, y
recompilar. El mecanismo acumulativo ya existe (`overlay_captures.json` + histórico `.d`).

## 9. Estado de la fase y siguientes pasos

Hecho y verificado: auditoría, corrección del recuento de regiones, mapa de carga por DMA,
análisis sector a sector contra el disco, identificación del patrón «copia de sí mismo» en
`0x80096000`, comprobación del contrato AOT de la revisión fijada, primer lote compilado,
integrado y **medido con atribución**.

Pendiente, por orden:

1. Campaña de captura: recorrer Arcade con varios personajes y escenarios, y modos VS/TEAM,
   para acumular regiones; recompilar y volver a medir con el mismo escenario.
2. Perfil AOT estático (`fixed_address_extents`) para `0x80096000`: hace falta la evidencia
   del cargador que coloca la imagen, no solo la captura.
3. Identificar la transformación de las regiones `0x80002000` y `0x80102000` (no son copias
   literales).
4. AppImage: no iniciada. Depende de tener una release estable con el lote AOT elegido.

## 10. A/B controlado: 1 shard frente a 8 shards

Mismo protocolo en las dos medidas: arranque limpio, `PSX_OVERLAY_AUTOCOMPILE_OFF=1`,
build debug, ~10 s en attract, lectura de `overlay_loader_status`. La **única** variable es
el contenido de `build-debug/cache`.

| Caché | regions | registered | dispatch_native | interp_fallback | proporción nativa | log |
|---|---|---|---|---|---|---|
| 1 shard (`0x00110000`) | 1 | 11 | 599 | 77.899 | **0,76 %** | `logs/run-overlay-noauto.log` |
| 8 shards (el anterior + 7 variantes de `0x00111000`) | 2 | 47 | 3.088.229 | 58.807 | **98,13 %** | `logs/run-overlay-8shards.log` |

Procedencia verificada de las dos ejecuciones: la de 1 shard terminó con `exit=0` y **0 líneas
de error** en toda su vida; la de 8 shards se midió en marcha y sigue viva al escribir esto.
La diferencia entre ambas ejecuciones es únicamente el contenido de la caché: mismo binario,
mismo `game.toml`, misma variable de entorno, mismo tiempo de attract.

### Interpretación

La región `0x80111000` es la que concentra casi todos los despachos de overlay en attract
(rutina por frame). Al servirla desde caché nativa, el intérprete deja de ejecutarla y la
proporción se invierte. `registered` pasa de 11 a 47 funciones.

### Comprobaciones de integridad hechas

- Renderizado verificado por captura: escena de combate correcta, sin corrupción ni pantalla
  negra (`native_98.png`).
- Log de la ejecución: 0 líneas de error, 0 avisos de guard/stale/mismatch.
- El runtime sigue con los guards por bytes: con 7 variantes históricas de la misma dirección,
  solo puede despachar la que coincide con los bytes vivos.

### Salvedad importante

Las dos medidas están tomadas **en attract**, no en partida. Que la proporción sea 98 % ahí no
garantiza lo mismo en un combate, donde se cargan otras regiones (desde SOUL.BNB/SOULOVL.BNS)
que todavía no están capturadas. Falta repetir el A/B entrando en Arcade y jugando.

Además, «98 %» es proporción de **despachos de overlay**, no de instrucciones del juego: el
código estático del EXE ya era nativo y no entra en este contador.

### Cómo reproducirlo

```bash
cd source/SoulBladeRecomp
python3 psxrecomp/tools/compile_overlays.py --captures build-debug/overlay_captures.json \
  --game-toml game.toml --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . --jobs 8 \
  --out-dir build-debug/cache
PSX_OVERLAY_AUTOCOMPILE_OFF=1 ../../run.sh --debug
# consola:  python3 psxrecomp/tools/debug_client.py overlay_loader_status
```

Nota: `compile_overlays.py` escribe por defecto en `build-dev/cache`; el runtime lee
`build-debug/cache`. Si se compila sin `--out-dir`, hay que consolidar los `.so` a mano en el
directorio que usa la build, respetando el subdirectorio de tag (`cg18_...`).

## 11. El punto caliente real: región 0x80096000 (resultado principal)

> **CORREGIDO en la sección 17.** Las cifras de esta sección no son evidencia causal: las
> muestras se tomaron en fases distintas de la secuencia de attract. Léase la sección 17 antes
> de usar cualquier número de aquí.



### Perfil medido, no supuesto

`dirty_ram_stats` con el juego en attract, 8 shards en caché, agrupado por región de 4 KB:

| región | hits interpretados | % del total | instrucciones |
|---|---|---|---|
| **0x096000** | **25.677.962** | **83,8 %** | 379.479.787 |
| 0x010000 | 1.850.945 | 6,0 % | 20.463.849 |
| 0x002000 | 1.386.290 | 4,5 % | 4.126.479 |
| 0x12E000 | 752.831 | 2,5 % | 179.414.032 |
| 0x12D000 | 289.233 | 0,9 % | 154.239.460 |
| 0x12F000 | 179.387 | 0,6 % | 47.075.459 |

Una sola región de 4 KB se comía el 83,8 % de las entradas al intérprete y 379 millones de
instrucciones. Las regiones 0x12C000-0x12F000 tienen muchas menos entradas pero muchísimas
instrucciones: son bucles largos (decodificación de audio/carga), otro perfil de coste.

### Procedencia exacta de la imagen

| dato | valor |
|---|---|
| origen en el disco | LBA 293..298 (6 sectores contiguos), 12.288 B |
| offset en el BIN | `0xA8408` |
| offset dentro de `SLUS_002.40` | `0x86800` (550.912) |
| sha256 de la imagen | `3088e4359fc9ca547ae2b61566899516ea2647c184e74fa901a4db9c410f9eca` |
| dirección de carga | `0x80096000` (36 seeds de ejecución) |

Es una **copia de un tramo del propio ejecutable**, DMA'd a `0x80096000` y ejecutada allí:
un overlay «en el sitio» que sobrescribe código que el recompilador había emitido de forma
estática. Está por debajo de `overlay_region_floor = 0x10C000`, que es la razón de que la
caché dinámica no lo sirviera por sí sola.

### Compilación

```bash
python3 psxrecomp/tools/compile_overlays.py \
  --captures build-debug/overlay_captures.json.d/7D2284348E038B9D.json \
  --game-toml game.toml --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --only-region 0x80096000 --out-dir build-debug/cache --jobs 4
```

Resultado: 18 funciones + 34 fragmentos interiores aislados = **35 shards, 0 fallos**, sin
instrucciones no soportadas y sin destinos desconocidos.

### Medición antes/después (misma build, mismo protocolo, attract, autocompile OFF)

| métrica | 8 shards | 43 shards (con 0x96000) |
|---|---|---|
| hits interpretados en `0x96000-0x96FFF` | **25.677.962** | **0** |
| PCs distintos en esa región | 26 | 0 |
| hits interpretados totales | 30.632.249 | 42.788 |
| `insns_run` de la sesión | 1.025.043.005 | 171.223 |
| proporción de despachos nativos | 98,13 % | 98,95 % |

La región más caliente pasa a ejecutarse íntegramente en nativo: cero entradas al intérprete
en esa dirección. Las instrucciones interpretadas de la sesión caen de mil millones a 171 mil
en ventanas comparables.

Verificado además: renderizado correcto por captura (`native_43.png`), **0 líneas de error**
en el log y ningún aviso de guard/stale/mismatch.

Salvedad: medido en attract. Falta repetir en combate, donde se cargan otras regiones.

## 12. Aviso operativo: el almacén de capturas se reescribe

`overlay_captures.json` **no es un acumulador estable**: al arrancar una instancia nueva queda
reescrito y puede contener una sola región (comprobado: pasó de 4 regiones a 1, `0x8012F000`).
El archivo real es el histórico `overlay_captures.json.d/` con **175 ficheros**.

Consecuencia práctica: nunca compilar directamente desde el fichero principal pensando que
contiene todo. Hay que reconstruir el conjunto de trabajo desde `.d` (los ficheros del
histórico son listas de regiones) y deduplicar por `(load_addr, sha256)`.

Reparto del histórico por dirección (top): `0x8012D000` ×34, `0x8012E000` ×28, `0x8012C000` ×26,
`0x80104000` ×24, `0x8012F000` ×21, `0x80105000` ×15, `0x80130000` ×6, `0x80102000` ×6,
`0x80110000` ×5, `0x80111000` ×4, y una copia de `0x80096000`, `0x80017000`, `0x80002000`.

## 13. Inventario completo del histórico (85 regiones)

Reconstrucción deduplicada por `(load_addr, sha256)` de `overlay_captures.json.d/` (175
ficheros) más el principal:

| dirección | variantes | dirección | variantes |
|---|---|---|---|
| `0x80002000` | 1 | `0x80106000` | 1 |
| `0x80017000` | 1 | `0x80108000` | 1 |
| `0x80096000` | 1 | `0x80109000` | 1 |
| `0x80102000` | 3 | `0x80110000` | 2 |
| `0x80104000` | 3 | `0x80111000` | 1 |
| `0x80105000` | 3 | `0x8012C000` | **26** |
| | | `0x8012D000` | 13 |
| | | `0x8012E000` | 14 |
| | | `0x8012F000` | 11 |
| | | `0x80130000` | 2 |
| | | `0x80131000` | 1 |

Total: **85 regiones únicas**. Conjunto de trabajo generado en
`build-debug/captures-merged.json` (no versionado; se regenera con el script de la bitácora).

`0x8012C000` con 26 variantes distintas es el bloque más reutilizado: la misma ventana de RAM
alberga código diferente según el contexto, que es la firma clásica de overlays por escena o
por modo. Es el siguiente objetivo por volumen.

## 14. Cobertura progresiva: 8 → 43 → 172 shards

> **CORREGIDO en la sección 17.** Las cifras de esta sección no son evidencia causal: las
> muestras se tomaron en fases distintas de la secuencia de attract. Léase la sección 17 antes
> de usar cualquier número de aquí.



Mismo protocolo en las tres medidas: arranque limpio, `PSX_OVERLAY_AUTOCOMPILE_OFF=1`,
attract, ~20 s, `dirty_ram_stats` + `overlay_loader_status`.

| caché | registered | native | fallback | % nativo | hits interpretados | `insns_run` |
|---|---|---|---|---|---|---|
| 8 shards | 47 | 3.088.229 | 58.807 | 98,13 % | 30.632.249 | 1.025.043.005 |
| 43 shards (+`0x96000`) | 47 | 4.027.008 | 42.767 | 98,95 % | 42.788 | 171.223 |
| **172 shards** (histórico completo) | **86** | 4.522.786 | 10.822 | **99,76 %** | **10.822** | **54.156** |

Las instrucciones interpretadas en la ventana caen de **1.025.043.005 a 54.156**: un factor
~19.000. Renderizado verificado en cada paso por captura (`native_43.png`, `native_172.png`),
0 errores en los logs y sin rechazos de guard (`stale_blocked = 0`, `reval_crc_miss = 0`).

## 15. El último punto caliente, identificado a nivel de instrucción

Con 172 shards, lo que queda del intérprete son **4 PCs** en `0x17000-0x17FFF` y 22 hits en
`0x104000`. Detalle:

| PC | hits |
|---|---|
| `0x00017764` | **10.797** |
| `0x000178AC` | 1 |
| `0x0001787C` | 1 |
| `0x000178B8` | 1 |

Comparación con el manifiesto `.ranges` del shard `00017000_533EDB37` (39 funciones que cubren
`0x800172F8..0x80018000`): **los 4 PCs caen FUERA de todos los rangos compilados**. Es decir,
no es un fallo de despacho: son direcciones interiores que el compilador no emitió como
función. `0x17764` está en un hueco.

### Intento de cierre con fragmento interior: resultado negativo

```bash
python3 psxrecomp/tools/compile_overlays.py --captures build-debug/captures-merged.json \
  --game-toml game.toml --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --only-region 0x80017000 --force-interior 0x17764 --out-dir build-debug/cache
```

El compilador lo acepta (`1/1 exact-demand orphan interior(s) -> isolated island shards`,
shard `00017000_E5D43001.so`, 26.784 B), **pero el camino dinámico no lo despacha**:
`registered` sigue en 86 y los contadores quedan idénticos (10.822 fallbacks, el mismo
`0x17764` con 10.797 hits).

Causa probable: la isla queda en un shard con **otro CRC** (`E5D43001` frente a `533EDB37`) y
el cargador dinámico enlaza un shard por región y CRC; las islas interiores están pensadas para
el enlace estático. Comprobable en el siguiente paso, no concluido aquí.

### Siguiente paso concreto

Probar la vía estática para esa región (`compile_overlays.py --static` → `overlays_static.c` y
enlace `GAME_OVERLAY_STATIC_C`), que es el mecanismo diseñado para servir varios fragmentos de
la misma imagen con guards por bytes. Si funciona, `0x17764` debería pasar a nativo.

Queda anotado que el coste residual (10.822 hits, 54.156 instrucciones en 20 s) es ya marginal
frente al punto de partida: el objetivo de esta ronda está cumplido con margen.

## 16. Vía estática: enlazada y medida (resultado mixto)

### Cómo se enlaza (dato que no estaba documentado en el proyecto)

`GAME_OVERLAY_STATIC_C` **no es una variable de caché**: pasarlo con `-D` produce
«not used by the project». Es una palabra clave de `psxrecomp_add_game_runtime()`. Se dejó
resuelto en `CMakeLists.txt` con un bloque condicional (`GAME_OVERLAY_STATIC_C_PATH`), vacío
por defecto, de modo que release y debug no cambian.

```bash
python3 psxrecomp/tools/compile_overlays.py --captures build-debug/captures-merged.json \
  --game-toml game.toml --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --only-region 0x80017000 --force-interior 0x17764 --static
# -> overlays_static.c + overlays_static_0000.c + _0001.c (185 identidades, 145 envoltorios CPS)

cmake -S . -B build-static-debug -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DPSX_DEBUG_TOOLS=ON -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON \
  -DCMAKE_C_STANDARD=99 -DGAME_OVERLAY_STATIC_C_PATH="$PWD/static-overlays/overlays_static.c"
ninja -C build-static-debug psx-runtime -j 12   # 389/389, 168 MB
```

### Medición (sin directorio `cache/`, o sea sin proveedor dinámico)

| métrica | 172 shards (dinámico) | estático (1 región) |
|---|---|---|
| `registered` | 86 | **0** |
| `dispatch_native` | 4.522.786 | **0** |
| hits interpretados totales | 10.822 | 64.155 |
| `insns_run` | 54.156 | 24.819.254 |
| PCs en `0x17000-0x17FFF` | 4 (10.800 hits) | **0** |

### Lectura honesta

1. **Lo que sí se cumple**: el hueco de `0x17000` desaparece por completo (0 PCs, 0 hits), y el
   juego renderiza correctamente. El fragmento interior forzado sí entra por la vía estática,
   que es lo que el camino dinámico no hacía.
2. **Lo que no cuadra**: `registered = 0` y `dispatch_native = 0`. El despacho estático **no se
   contabiliza en esos contadores**, así que la mejora no es atribuible por ellos; se infiere por
   la desaparición de los PCs, que es evidencia más débil.
3. **El coste global empeora en esta build**: 24,8 M instrucciones interpretadas frente a 54 mil,
   porque el binario solo lleva **una** región enlatada y el resto (`0x96000`, `0x8012C000`…) se
   queda sin proveedor. No es una regresión del mecanismo: es que falta el conjunto completo.
4. Detalle a vigilar: aparece `0x357C` con exactamente **10.797 hits**, el mismo recuento que
   tenía `0x17764`. Puede ser el mismo bucle reportado en otro PC (envoltorio CPS) o casualidad
   de un contador fijo. **No concluido**; no se usa como prueba.

### Siguiente paso para cerrarlo

Generar el conjunto estático **completo** desde las 85 regiones del histórico y compararlo cara a
cara con la build de 172 shards. Coste alto: la documentación del framework avisa de que los
overlays de un juego entero dan un C de cientos de MB (BoF3: 309 MB); para Soul Blade habría que
medirlo antes. Si el rendimiento no mejora, la vía dinámica sigue siendo la buena y el estático se
reserva para la AppImage, donde la cobertura fija sí vale por sí misma.

## 17. CORRECCIÓN: la región 0x96000 nunca se carga por la vía dinámica

Esta sección invalida las conclusiones causales de las secciones 11 y 14. Se deja constancia del
error en vez de reescribir el historial.

### Qué estaba mal

Se afirmó que compilar `0x96000` había hecho desaparecer su punto caliente (25.677.962 hits → 0)
y que las instrucciones interpretadas habían caído de 1.025.043.005 a 54.156. **No es cierto como
efecto de los shards.**

Dos hechos lo demuestran:

1. **Control de fase inválido.** Las capturas de pantalla con que se comparaban las dos medidas
   mostraban escenas distintas de la intro. Las partículas animadas hacen que el hash de imagen
   nunca coincida, así que no servían como control. Prueba adicional: el valor `insns_run =
   54.156` aparece **idéntico** en ejecuciones sin relación entre sí; es un estado ocioso, no la
   misma carga de trabajo.
2. **El cargador ni siquiera mira esa región.** `overlay_loader_status` devuelve
   `checked = ["0x00000000", "0x00110000"]` y `overlay_region_floor = 0x10C000`. El camino
   dinámico solo sondea regiones en o por encima del suelo. `0x00096000` está por debajo:
   **sus 36 shards no se cargan nunca**. Son peso muerto en `build-debug/cache`.

### Evidencia en contra del resultado anterior

En un combate real, con esos 36 shards presentes en la caché, `dirty_ram_stats` daba
`0x096000` con **287.482 hits interpretados (93,6 % del intérprete)** y `regions = 6`,
`loads = 6`. La región se ejecutaba entera por intérprete teniendo los shards al lado.

Comprobación adicional: el volcado de `0x80096000` durante el combate es **byte a byte idéntico**
al de la captura de attract (`sha256 f22acafee66955b1…`, 0 bytes distintos). No es otra variante:
lo que cambia entre attract y combate es **qué direcciones se ejecutan**, no el contenido.

Y esas direcciones **sí están compiladas**: con la unión de los 36 manifiestos `.ranges` de
`0x96000` (96 intervalos, 62 entradas), los 25 PCs ejecutados en combate quedan cubiertos al
100 %. El problema no es cobertura de código, es que el cargador no enlaza la región.

### Qué queda en pie

- El inventario de capturas (sección 13): 85 regiones únicas en 17 direcciones. Sólido.
- La procedencia de la imagen de `0x96000` (sección 11, tabla de LBA/offset/sha256). Sólida: el
  volcado en combate coincide con el recorte del disco.
- Que el pipeline completo funciona: inventario → compilación → caché → ejecución.
- Que las regiones **por encima del suelo** sí se sirven: en combate, `regions=10, loads=10,
  registered=225`, con `dispatch_native` en millones.

### Vía correcta para 0x96000

Está **dentro de la imagen de texto**, así que no le corresponde el cargador dinámico sino el
guard de divergencia de texto: si los bytes vivos coinciden con la imagen de referencia del EXE,
se permite la entrada nativa estática; si divergen, se marca divergente y va al intérprete. Como
el volcado coincide exactamente con el recorte del EXE, es el caso favorable.

Es decir: `0x96000` se sirve por la **vía estática** (`--static` + `GAME_OVERLAY_STATIC_C_PATH`),
no por shards en `cache/`. El ensayo estático de la sección 16 solo incluía `0x17000`
justamente porque se hizo para otro fin.

### Siguiente paso definido

1. Generar el conjunto estático incluyendo `0x96000` (y las demás regiones del histórico).
2. Medir **en combate**, que es una fase estable y repetible, no en attract.
3. Criterio de éxito: `0x096000` deja de aparecer en `dirty_ram_stats` durante un combate.
4. Los 36 shards de `0x96000` en `cache/` se retiran: no se cargan nunca.

### Lección de método

Una medida en attract solo vale si se demuestra que las dos ejecuciones están en la **misma**
fase. Para este juego eso exige fijar el estado (y no hay `loadstate` en el cliente TCP), así que
las medidas válidas hay que tomarlas en estados estables y autosostenidos, como un combate, o
comparando dentro de una única sesión continua.

## 18. Vía estática con 0x96000: el vídeo se congela (resultado negativo, bloqueante)

Se generó el conjunto estático incluyendo `0x96000` y `0x17000`:

```bash
python3 psxrecomp/tools/compile_overlays.py --captures build-debug/captures-merged.json \
  --game-toml game.toml --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --only-region 0x80096000 --only-region 0x80017000 --force-interior 0x17764 \
  --static --force --out-dir static-overlays --jobs 8
# -> 2.090 identidades exactas, 5 unidades, 37 islas interiores, 0 fallos
```

`build-static-debug` recompiló 100/100 (171,7 MB) y el juego **arranca**, pero:

| síntoma | medida |
|---|---|
| CPU | avanza: `blocks_run` 5.509.756 → 5.588.319 en 3 s |
| entrada | llega: `pad_status` pasa a `0xFFF7` con `press` |
| vídeo | **congelado**: tres capturas separadas 8 s con md5 idéntico (`a12d24a1…`), fichero reescrito (mtime cambia) pero mismo contenido |

Es decir: el emulador corre, el mando responde, y la imagen no se actualiza. En la build dinámica,
en el mismo punto de la intro, el vídeo avanza con normalidad.

### Conclusión

**El despacho estático de `0x96000` no es seguro.** Compila y enlaza, pero rompe la presentación.
No se usa para nada hasta identificar la causa. Candidatos, en orden de sospecha:

1. La región está dentro de la imagen de texto y su ejecución pasa por el guard de divergencia;
   el enlace estático puede estar sirviendo bytes que no corresponden al ocupante vivo.
2. Los 145 envoltorios CPS de reanudación pueden estar devolviendo el control a un punto
   incompatible con el estado del bucle de render.
3. Interacción entre el despacho estático y el intérprete sucio en páginas marcadas divergentes.

### Estado de la vía estática

- Sirve para `0x17000` en apariencia (la región desaparece del intérprete), pero **no hay prueba
  visual de que el juego se comporte bien con ella**: en aquel ensayo solo se tomó una captura.
- Con `0x96000` está **descartada** por regresión visible.

Por tanto, para el paquete final no se puede contar todavía con la vía estática. La caché dinámica
sigue siendo la única ruta validada, y su cobertura se limita a las regiones por encima de
`overlay_region_floor`.

### Siguiente paso

Bisecar: misma build estática **solo con `0x17000`** (binario anterior) y comprobar si el vídeo
avanza. Si avanza, el culpable es `0x96000` y hay que mirar sus 37 islas interiores y el guard de
texto; si también se congela, el problema es del enlace estático en general y no de la región.

## 19. LA CAUSA REAL: el suelo del cargador (y su arreglo por configuración)

Aquí está el resultado que explica todo lo anterior.

### Mecanismo

`overlay_region_floor` (por defecto, el final del texto del juego: `0x10C000`) es el límite por
debajo del cual el cargador **no sondea regiones**. `overlay_loader_status` lo delataba con
`checked = ["0x00000000", "0x00110000"]`: `0x00096000` no aparecía nunca, así que sus 36 shards
compilados no se cargaban jamás y todo ese código caía al intérprete.

`0x80096000` cae por debajo porque el juego copia ahí un tramo **de su propio ejecutable**
(sectores LBA 293-298, offset 0x86800) y lo ejecuta en el sitio: es un solapamiento con la imagen
de texto, no un overlay clásico. Por eso el suelo, calculado como «fin del texto», lo dejaba fuera.

### Arreglo (solo configuración, sin tocar el framework)

`game.toml`:

```toml
[runtime]
overlay_region_floor = "0x96000"
```

Equivalente por entorno (más volátil): `PSX_OVERLAY_REGION_FLOOR=0x96000`. El propio código
documenta el caso: bajar el suelo hace que esas regiones pasen a ser candidatas de caché y las
cierre por bytes vivos, «en vez de thrash de despacho por instrucción».

### Medición en combate (fase estable, no attract)

| métrica | antes | con `overlay_region_floor = 0x96000` |
|---|---|---|
| `checked` | `[0x00000000, 0x00110000]` | `[0x00000000, **0x00096000**, 0x00110000]` |
| `loads` | 6 | 12 |
| `registered` | 191 | 210 |
| hits interpretados en `0x96000` | **287.482** | **0** |
| hits interpretados totales | 307.126 | **11.423** |
| `insns_run` | 4.678.073 | 63.443 |
| `stale_blocked` / `reval_crc_miss` | 0 / 0 | 0 / 0 |

Renderizado verificado por captura en combate, sin artefactos. Reducción del trabajo interpretado
en partida de **27×**, y el punto que era el 93,6 % del intérprete queda a cero.

### Lo que queda del intérprete

Solo `0x17000`, con 10.800 hits, y **la vía estática lo sirve**: `overlay_static_entries` reporta
`0x80017764` con **10.797 despachos nativos**. Pero la build estática debe llevar **solo**
`0x17000`: incluir `0x96000` congela el vídeo (sección 18). Ahora que `0x96000` lo sirve la caché
dinámica, la receta correcta es:

- dinámico (`cache/`) para todo lo que el suelo alcanza, con `overlay_region_floor` ajustado;
- estático **solo** con `0x17000` + su interior `0x17764`, y nada más.

### Lección de método (importante para futuras sesiones)

Dos instancias vivas a la vez se repartieron el puerto 4370: la estática congelada se quedó con él
y **respondió varias consultas que yo atribuía a la dinámica**. De ahí una tanda de medidas
contaminadas. Regla: antes de medir, comprobar con `ss -tlnp` qué PID escucha 4370 y que coincide
con la instancia que se quiere medir; una sola instancia por vez.

Y la otra regla, ya establecida: no comparar entre arranques en attract. Medir en estados
autosostenidos (un combate) o dentro de una misma sesión.

## 20. Hito: intérprete prácticamente eliminado en combate

Combinación de las dos vías, cada una en su terreno:

1. **Dinámica** (`cache/` + `overlay_region_floor = 0x96000`) para todo lo que el suelo alcanza,
   incluida `0x96000`.
2. **Estática** (solo `0x17000` + interior `0x17764`, binario `build-static-debug`) para la región
   que el cargador no puede servir y que no puede entrar en la estática completa sin romper el
   vídeo.

La caché de `build-debug` se copió a `build-static-debug/cache` para que el binario tenga las dos.

### Progresión medida, todo en combate (fase estable)

| configuración | hits interpretados | `insns_run` | `0x96000` | `0x17000` |
|---|---:|---:|---:|---:|
| base (caché sin tocar el suelo) | 307.126 | 4.678.073 | 287.482 | 10.800 |
| + `overlay_region_floor = 0x96000` | 11.423 | 63.443 | 0 | 10.800 |
| **+ estático `0x17000` (combinada)** | **623** | **9.446** | **0** | **0** |

Reducción total del trabajo interpretado en partida: **493×** en entradas y **495×** en
instrucciones. Lo que queda son 623 hits repartidos entre `0x12F000` (486) y `0x12C000` (137),
residuales y sin impacto perceptible.

Estado en la combinada: `checked = [0x00000000, 0x00096000, 0x00110000, 0x00111000]`,
`loads = 4`, `registered = 107`, y el despachador estático con `185` entradas y `10.799` despachos
(`0x80017764` con `10.797`). Renderizado verificado por captura en combate, sin artefactos.

### Receta reproducible

```bash
cd source/SoulBladeRecomp

# 1. dinámico: la caché de shards (regenerable desde captures-merged.json)
python3 psxrecomp/tools/compile_overlays.py \
  --captures build-debug/captures-merged.json --game-toml game.toml \
  --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --out-dir build-debug/cache --jobs 8

# 2. estático mínimo: SOLO 0x17000
python3 psxrecomp/tools/compile_overlays.py \
  --captures build-debug/captures-merged.json --game-toml game.toml \
  --recompiler build-recompiler/psxrecomp-game \
  --runtime-include psxrecomp/runtime/include --project-root . \
  --only-region 0x80017000 --force-interior 0x17764 \
  --static --force --out-dir static-overlays --jobs 8

# 3. build con las dos, y el suelo en game.toml ([runtime] overlay_region_floor = "0x96000")
cmake -S . -B build-combi -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DPSX_DEBUG_TOOLS=ON \
  -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON -DCMAKE_C_STANDARD=99 \
  -DGAME_OVERLAY_STATIC_C_PATH="$PWD/static-overlays/overlays_static.c"
ninja -C build-combi psx-runtime -j 12
cp -r build-debug/cache build-combi/cache

# 4. medir en combate (nunca en attract)
python3 psxrecomp/tools/debug_client.py dirty_ram_stats
python3 psxrecomp/tools/debug_client.py overlay_static_entries
```

### Pendiente en esta línea

- `0x12C000`/`0x12F000` (623 hits): probar si bajan con el suelo ajustado o necesitan su propia
  entrada estática. Coste bajo, ganancia pequeña.
- Confirmar la combinada en el resto de modos (VS, Team Battle, Survival, opciones, memory card):
  el suelo bajo puede afectar a otras regiones de menú, y eso aún no se ha probado.
- Regresión funcional completa con esta build: los dos mandos, guardado y carga, audio y segundo
  arranque, que ya estaban verificados con la build anterior.

## 21. Prueba funcional de la build combinada (parcial)

Build `build-static-debug` + caché copiada + `overlay_region_floor = 0x96000`.

### Verificado con evidencia

| prueba | resultado |
|---|---|
| Arranque y BIOS LLE | OK |
| Menú principal renderizado | OK: OPTION, ARCADE MODE, VS BATTLE MODE, TEAM BATTLE MODE, TIME ATTACK MODE, SURVIVAL MODE y EDGE MASTER MODE legibles, sin texto roto |
| Navegación con cruceta | OK: el resaltado sigue las pulsaciones (Arcade → VS Battle → Team Battle → VS Battle → Option) |
| Entrada al modo y arranque de combate | OK |
| Pantalla VS | OK: «STAGE 1 — SEUNG MINA VS MITSURUGI» con retratos correctos |
| Combate jugable, dos escenas distintas | OK (Mitsurugi vs Li Long y Seung Mina vs Mitsurugi) |
| Mandos | `slot0` y `slot1` con `connected = True` |
| Intérprete en combate 1 | `0x96000 = 0`, `0x17000 = 0`, total 623 hits |
| Intérprete en combate 2 | `0x96000 = 0`, `0x17000 = 0`, total 11.620 hits |

El total de la segunda medida es mayor porque esa sesión incluyó toda la navegación de menús, no
solo el combate; los dos puntos calientes siguen a cero, que es lo que se quería comprobar en una
escena distinta.

### NO verificado todavía con esta build

- **Guardado y carga en memory card.** El intento de navegar a `OPTION` acabó dentro de una
  partida (el menú expira por inactividad y es fácil salirse), así que la ruta
  `OPTION → MEMORY CARD` queda pendiente con esta build. Estaba verificada con la build anterior.
- **Segundo arranque tras cierre limpio.** Pendiente con esta build.
- **Audio.** Medido con la build anterior; no repetido aquí.
- Modos TIME ATTACK, SURVIVAL, TEAM BATTLE y EDGE MASTER: solo se ha comprobado que aparecen y se
  resaltan, no que se jueguen.

Nota práctica para la próxima sesión: el menú de Soul Blade vuelve al demo por inactividad, así que
las secuencias de pulsaciones hay que hacerlas con menos de un segundo entre pasos y capturando
cada paso, o se acaba en el attract sin saber por qué.

### Evidencia parcial de la tarjeta de memoria (sin pasar por el menú)

La navegación `OPTION → MEMORY CARD` no se pudo completar: el juego vuelve al bucle de demos del
attract y las pulsaciones acaban saltando escenas. En vez de insistir, se consultó el subsistema
por el servidor de depuración (`sio_state`) con la build combinada:

```text
mc_probes = 85   mc_acks = 85   mc_cmds = 85
mc_reads  = 83   mc_read_done = 83   mc_aborts = 0
mc_last_caller = 0x00002970        mc_max_state = 18
```

El juego sondea la tarjeta, recibe confirmación y **completa 83 lecturas sin un solo aborto**.
Es decir: el protocolo SIO/memcard funciona en esta build y el juego enumera el contenido de la
tarjeta. Lo que sigue sin probar es el ciclo completo por interfaz: guardar desde
`OPTION → MEMORY CARD → SAVE` y cargar en un proceso nuevo, que sí estaba verificado con la build
anterior.

Nota para retomarlo: el menú de Soul Blade solo se alcanza en una ventana concreta tras la intro;
la forma fiable es esperar a que termine la intro sin pulsar nada y comprobar con captura antes de
tocar el mando, en lugar de encadenar pulsaciones a ciegas.

Detalle adicional comprobado: con la build combinada, las dos tarjetas del proyecto
(`source/SoulBladeRecomp/saves/card1.mcd` y `card2.mcd`, 131.072 B cada una) reciben escritura en
el arranque (mtime actualizado con segundos de diferencia entre ambas), que es el refresco del frame
de checksum del bloque 0 ya documentado en su día. Y `memcard_dir = "saves"` se resuelve contra la
**raíz del proyecto**, no contra el directorio de build: `build-static-debug/saves` no existe y aun
así las tarjetas se leen y escriben.

### Audio en la build combinada (verificado)

Medido con `parecord` sobre el monitor del sumidero, con captura de pantalla simultánea para saber
qué se estaba oyendo:

| contexto | pico | RMS |
|---|---|---|
| demo del attract | 0,000000 | 0,000022 |
| **combate** (Li Long en pantalla) | **0,833771** | **0,140006** |

El audio funciona. El silencio de la primera medida es del demo del attract, no del juego: es un
dato a tener en cuenta para no confundirlo con una regresión en futuras comprobaciones.

### Sobre el control de fase (cerrado como imposible)

Se comprobó la lista de comandos del servidor de depuración: existen `savestate`,
`savestate_status` y `rewind_status`, pero **no hay `loadstate` ni comando de restauración**. Por
tanto no se puede fijar un estado y repetir medidas desde él: la única forma válida de comparar
sigue siendo medir dentro de una sesión continua o en un estado autosostenido como un combate.

## 22. Qué significan realmente las cifras (623 hits, 493×)

Aclaración pedida explícitamente antes de optimizar nada más.

| término | qué es | qué NO es |
|---|---|---|
| «hits» | entradas de bloque ejecutadas por el **intérprete**, sumadas del campo `per_pc` de `dirty_ram_stats` | no es un porcentaje de cobertura ni un número de funciones |
| `insns_run` | instrucciones ejecutadas por el intérprete en la sesión | no es tiempo ni FPS |
| 307.126 | hits interpretados acumulados en una sesión concreta, medida justo al entrar en combate con la caché sin tocar el suelo | no es un valor por frame |
| 623 | los mismos hits en una ventana equivalente con la build combinada | no es una tasa estable: crece con la sesión |
| 493× | cociente 307.126 / 623 sobre **ese contador** | no es una mejora de FPS ni de rendimiento global |
| 495× | cociente de `insns_run` (4.678.073 / 9.446) | igual |

Los contadores son **acumulativos por sesión**. Comprobado en esta ronda: una misma build da
0 hits en la intro (todo nativo), 1.721 al entrar en menús y 690.656 tras 17 minutos de demos y
navegación variada. Es decir: solo son comparables entre ejecuciones con el mismo recorrido, y por
eso las medidas válidas se tomaron en ventanas cortas y equivalentes dentro de un combate.

Para rendimiento real (FPS, CPU, tiempos de carga) no hay todavía medida comparable: `PSX_FPS_TELEMETRY`
existe, pero no se ha usado de forma sistemática. Queda declarado como **no medido**.

## 23. Punto caliente nuevo: 0x10D3C / 0x10D94 (bloque copiado del propio EXE)

En la sesión larga (17 min) salió un punto caliente que no estaba identificado:

| PC | hits | instrucciones |
|---|---:|---:|
| `0x80010D3C` | 231.056 | 4.852.176 |
| `0x80010D94` | 231.147 | 231.147 |

### Origen exacto, verificado byte a byte

Se volcó la RAM en `0x10D00` (8 KB) y se comparó con la imagen del EXE:

- `RAM[0x10D00..0x10FFF]` (768 B) es **idéntico a la imagen del EXE en `0x10F60`**
  (`sha256 227f606c9711c4a2…`), es decir, el juego copia 0x300 bytes de su propio código
  desplazados 0x260 hacia abajo y lo ejecuta ahí.
- Búsqueda en el disco: esos bytes aparecen una sola vez, en `SLUS_002.40`, offset interno `0x1760`.
- **No estaba en ninguna captura**: el gancho de captura solo ve DMA de CD, y esta copia la hace la
  CPU. Por eso la región nunca tuvo shard y caía entera al intérprete.

> **CORRECCIÓN (misma sesión).** Aquí escribí que `0x10D000` estaba por encima del suelo. Es falso:
> `0x10D00` = 68.864 y `0x96000` = 614.400, así que `0x10D000` está **muy por debajo**. Y también
> está dentro de la imagen de texto (`0x10000..0x10C000`). Consecuencia: el cargador dinámico no la
> indexa (`checked` nunca la incluye y `overlay_candidates` no tiene ni un candidato en ese rango,
> con los 5 shards presentes en el directorio). Para servirla por la vía dinámica habría que bajar
> el suelo a `0x10000`, lo que convertiría **todo el texto del juego** en candidato de overlay: no
> es una opción razonable.
>
> La vía correcta para este bloque es la **estática**, que despacha por dirección con
> independencia del suelo, más el guard de divergencia de texto. Y la causa de que caiga al
> intérprete ya está identificada: la copia hace que los bytes de `0x10D3C` difieran de la imagen
> de referencia en esa dirección, el guard marca la página como divergente de forma **pegajosa** y
> ya no vuelve a comparar.

### Lote generado

Captura creada a mano desde el volcado verificado (`load_addr 0x80010D00`, `size 0x300`,
4 seeds: `0x80010D3C/D94/D9C/DAC`), añadida al conjunto de trabajo (86 regiones) y compilada:

```text
built OK : 5   skipped : 0   FAILED : 0
interior fragments @0x00010D00: 4/4 exact-demand orphan interior(s) -> isolated island shards
```

Shards `00010D00_{B633B9F8,893B82B1,5B3BD1CE,A88E8A82,B786A643}.so`, copiados también a la build
combinada (177 shards en `build-debug/cache`).

### Estado del despacho: pendiente de verificación

`checked` sigue en `[0x00000000, 0x00096000, 0x00110000, 0x00111000]`. Se leyó el mecanismo en
`overlay_loader.c`: `checked` es una **memo de regiones con primer fallo de despacho**
(`mark_checked` se llama al primer fallo dentro de la región), no una lista de regiones
descubiertas al arrancar. En las sesiones cortas de esta ronda no se ha llegado a ejecutar el
bucle de `0x10D3C` (intro y pantallas nativas), así que la región no se ha sondeado y no hay
veredicto.

Tampoco basta con escribir el almacén de capturas de la build: se copió
`captures-merged.json` a `build-static-debug/overlay_captures.json` (86 regiones, incluida
`0x80010D00`) y `checked` no cambió, lo que confirma que el sondeo es perezoso y por fallo.

### Cómo cerrarlo

Ejecutar la ruta que usa ese bloque (menús y combate reales) en una sesión continua y comprobar
que `0x00010D00` aparece en `checked` y que sus hits bajan a 0. Es la misma prueba que se usó para
`0x96000`, y requiere llegar al menú, que es el punto frágil de la instrumentación actual.

## 24. Estático con 0x10D00: enlaza y NO congela (a diferencia de 0x96000)

Conjunto estático regenerado con `0x80010D00` + `0x80017000` (sin `0x96000`):

```text
recompiled: 1 functions, 1 exact identities
Static output: static-overlays/overlays_static.c (201 exact function identities, 5 TUs)
built OK : 2   FAILED : 0
```

Prueba con la build combinada:

| comprobación | resultado |
|---|---|
| Vídeo | **anima**: dos capturas separadas 7 s con md5 distinto (`629868…` vs `03619d…`) |
| Despachador estático | 197 entradas, `total_hits = 10.799` |
| Entrada más caliente | `0x80017764` con 10.797 (la de siempre) |
| Entradas de `0x10D3C` | 0 hits |
| Intérprete | 0 hits, `insns_run = 0` durante toda la sesión |

Conclusión parcial y **honesta**: añadir `0x10D00` en estático no rompe la presentación, que era el
riesgo real tras lo de `0x96000`. Pero **no se ha verificado el despacho**: en estas sesiones el
juego no ha ejecutado ese bloque (el intérprete marca 0 en todo el recorrido), así que las entradas
de `0x10D3C` siguen a cero y no hay prueba de que el shard se use.

## 25. Por qué fallaba la navegación automatizada: el asiento 2

Encontrado el motivo de buena parte de los intentos fallidos de entrar en menús y combates:

- `game.toml` tiene `p2_device = "auto"` y hay dos GameSir conectados, así que el asiento 2 coge el
  segundo mando.
- El juego entra en selección de personaje esperando **«PRESS 2P START»** y se queda ahí: la pantalla
  consume cero intérprete y no avanza con las pulsaciones del asiento 1.
- El comando `press` del servidor de depuración **no acepta asiento**: inyecta solo en el jugador 1
  (`{"cmd":"press","buttons":…,"frames":…}` y ejes `lx/ly/rx/ry`). No hay forma de mandar START al
  jugador 2 por esta vía.

Procedimiento para pruebas automatizadas (documentado, no aplicado de forma permanente porque el
usuario quiere los dos mandos):

```toml
[controller]
p2_device = "none"   # "none" es valor válido: sin mando en ese asiento
```

Valores admitidos por `main.cpp`: `"none"` (sin pad), `"keyboard"` (mapa de teclado), `"auto"` /
`"gamepad"` / `"controller"` (primer SDL libre) o un GUID de SDL.

Esto explica de forma concreta por qué las secuencias de pulsaciones acababan en demos o en pantallas
paradas: el juego no estaba atascado, estaba esperando a un segundo jugador que no podía llegar.

### Seguimiento: intento de verificación con `p2_device = "none"` (resultado incompleto)

Se probó a desactivar el asiento 2 para que la selección de personaje no esperase a «PRESS 2P
START». Resultado:

- La pantalla de selección **sigue sin confirmar** con Cruz ni con START inyectados: se queda en
  «SELECT YOUR CHARACTER» con 1P resaltado y «INSERT COIN» al lado.
- Reiniciando y pulsando una sola vez se llega a la transición al menú y de ahí a las **demos de
  combate**, con intérprete activo (11.045 hits, 111.350 instrucciones).
- **`0x10D00-0x10FFF` sigue con 0 hits** también en demos de combate reales: ese bloque no se
  ejecuta en ninguna de las rutas alcanzadas.

Es decir: no se ha reproducido la condición en la que `0x10D3C` corría (231.056 hits en la sesión
larga de 17 minutos, con dos mandos y mucha navegación). Sin esa reproducción no hay veredicto sobre
el despacho estático de `0x10D00`, y no voy a darlo por bueno.

`p2_device` se ha restaurado a `"auto"` en `game.toml` y en las tres builds: la configuración de los
dos GameSir queda como estaba.

Hipótesis para la próxima sesión: ese bloque pertenece a la ruta de **partida jugada** (no a demos ni
menús), y para alcanzarla hace falta confirmar personaje, cosa que la inyección actual no consigue.
Alternativas: (a) localizar el botón o la secuencia real de confirmación con `input_state`/`pad_status`
observando qué lee el juego; (b) instrumentar temporalmente el runtime para registrar el primer
acceso a `0x10D3C` y así saber qué pantalla lo dispara; (c) usar REA para seguir los callers de ese
bloque en el EXE y saber desde dónde se llama.

## 26. Qué es realmente el bloque de 0x10D00: un stub de retorno desplazado

Análisis estático sobre el código recompilado, sin depender de la navegación.

Como el bloque de `0x10D00` es idéntico a la imagen del EXE en `0x10F60`, el código equivalente
está recompilado en la dirección original. Localizado en `generated/SLUS_002.40_full_00.c`:

- La instrucción `0x80010F9C` pertenece a `func_80010DB4(CPUState* cpu)`, la rutina de
  inicialización del juego (arranca en `0x80010DB4`, junto al punto de entrada `0x80010FBC`).
- Las instrucciones de esa zona (`0x80010F88`–`0x80010F9C`: `0x8FB0xxxx` … `0x8FB5xxxx`) son
  **restauraciones de registros guardados y `$ra`**, es decir, el **epílogo** de la función.

Conclusión: lo que el juego copia a `0x10D00` no es una rutina completa, sino un **fragmento de
retorno desplazado 0x260 bytes** que ejecuta desde otra dirección. Eso encaja con un stub de
retorno reubicado, no con un overlay de escena.

Consecuencias prácticas:

- No tiene sentido tratarlo como «overlay con entry points de función» al estilo de `0x17000`; sus
  4 seeds son direcciones de continuación dentro de un fragmento, no cabeceras de función.
- Al estar dentro de la imagen de texto, el guard de divergencia lo marca divergente de forma
  pegajosa (los bytes no coinciden con la referencia *en esa dirección*) y lo manda al intérprete.
- La vía estática lo enlaza sin romper el vídeo (comprobado), pero sigue **sin verificarse el
  despacho** porque no se ha reproducido la ruta que lo ejecuta.

### Estado del candidato 0x10D00 (sin adornos)

| etapa | estado |
|---|---|
| Reconstrucción (bytes = origen verificado) | **hecha** (`sha256 227f606c…`, coincide con EXE 0x10F60) |
| Generación de shards | **hecha** (5 dinámicos + 1 estático, 0 fallos) |
| Enlace estático sin regresión visual | **hecho** (el vídeo anima) |
| Despacho seguro | **NO verificado** |
| Corrección semántica en juego | **NO probada** |

No se sube de estado hasta que haya evidencia de ejecución.

## 27. El bloque de 0x10D00, resuelto: biblioteca de matemáticas GTE copiada por el BIOS

Investigación estática completa, sin depender de la navegación. Todo reproducible con
`tests/diagnostico/verify_10d00.py`.

### 27.1 Coordenadas exactas (verificadas por script)

| concepto | origen | destino |
|---|---|---|
| dirección virtual MIPS | `0x80010F60` | `0x80010D00` |
| dirección física / kseg0 | `0x00010F60` | `0x00010D00` |
| clave del dispatcher (`& 0x1FFFFF`) | `0x00010F60` | `0x00010D00` |
| offset en el PS-X EXE | `0x1760` | `0x1500` |
| offset en el BIN | `0xF3F8` | `0xF198` |
| LBA del EXE / offset del fichero | LBA 24, `0xDC98` | ídem |

Cabecera del EXE confirmada: `PS-X EXE`, load `0x80010000`, entry `0x80010FBC`, text `0xFC000`,
sp `0x801FFFF0`.
Tamaño del bloque: **768 B (`0x300`)**, desplazamiento **`0x260`** hacia abajo.
`sha256` del contenido: `227f606c9711c4a245221076a0997b0f3ad0f5b75652faae9b7b70aea4f2d444`.
La imagen del EXE **en el destino** es distinta (`sha256 4d1d74e7…`), o sea que la copia cambia los
bytes de esa dirección: no es un no-op ni una restauración de la imagen original.

### 27.2 Quién lo copia: bucle de palabras del BIOS (probado con traza)

`PSX_WTRACE_BOOT_RANGES='0x00010D00-0x00011000'` armó la traza de escrituras de arranque
(`env_ranges = 1`, `env_error` vacío) y capturó el evento:

| dato | valor |
|---|---|
| escrituras de la copia | **192 palabras** (192 × 4 B) |
| direcciones | `0x10D00`..`0x10FFC`, **contiguas, sin un solo hueco** |
| PC que escribe | `0x000008B8` (rutina del BIOS) |
| `$ra` | `0xBFC03BE8` (121), `0xBFC03BFC` (66), `0x00000A48` (5) |
| `$sp` al escribir | `0x801FFCF8` → **pila del juego** |
| frame | 51 |
| valor previo en destino | `0x00000000` (BSS limpia) |

Lectura: el juego llama a la rutina de copia del kernel y ésta ejecuta un bucle con el almacén en
una sola dirección (`0x8B8`), usando la pila del juego (no una excepción). Los `$ra` observados
apuntan al trampolín del BIOS, no al llamador del juego: **el punto de llamada del lado del juego
sigue sin identificar** y se documenta como pendiente. Los intentos de localizarlo por patrón
(`lui 0x8001` + `addiu 0x0D00`, y `li $a2,0x300` antes de `jal` al vector) dieron **cero
coincidencias**: ambas direcciones se calculan en tiempo de ejecución, no están literales.

### 27.3 Qué es el bloque: biblioteca de matemáticas GTE con tres retornos

Desensamblado de las 192 palabras (`0x80010D00`..`0x80010FFF`):

| instrucción | nº | comentario |
|---|---:|---|
| `lw` / `sw` | 22 / 15 | carga y almacenamiento de operandos |
| `lwc2` / `swc2` | 15 / 10 | **transferencias a/desde los registros de datos de la GTE** |
| `ctc2` / `mtc2` | 5 / 4 | carga de registros de control/datos de la GTE |
| `div` | 2 | divisiones enteras (`0x00E2001A` = `div $a3,$v0`) |
| `addu` / `sll` / `srl` / `addiu` | 20 / 16 / 9 / 22 | aritmética y desplazamientos |
| `jr $ra` | **3** | en `+0x0AC`, `+0x2AC`, `+0x2B4` |

Conclusión: no es un overlay de escena ni un stub de retorno simple, sino un **trocito de código de
matemáticas 3D con la GTE** —tres rutinas contiguas dentro de 0x300 bytes— copiado a una dirección
fija. Eso encaja con una copia «caliente» de código de transformación/proyección.

### 27.4 Las cuatro seeds son continuaciones interiores, no funciones

| seed | offset | palabra | qué es |
|---|---|---|---|
| `0x80010D3C` | +0x03C | `0x00E2001A` | `div $a3,$v0` (mitad de una rutina de división) |
| `0x80010D94` | +0x094 | `0x0721FFE9` | `bgez $t9, -23` → **bucle hacia atrás** |
| `0x80010D9C` | +0x09C | `0x00E2001A` | otra `div` |
| `0x80010DAC` | +0x0AC | `0x03E00008` | `jr $ra` → **cierre de la primera rutina** |

Confirmado: son puntos interiores de continuación (una `div`, un bucle y el retorno), no cabeceras.
Tratarlas como funciones independientes truncaría la rutina propietaria y alteraría el camino de
retorno, exactamente el riesgo que había que evitar.

### 27.5 Mecanismo correcto según esta revisión del framework

`docs/COMPILING_OVERLAYS.md` (revisión fijada) describe el mecanismo previsto:

> «Isolated interior fragments are per (entry, image).» — cada `dispatch_entry_pc` capturado que
> ningún huésped compilado sirve recibe su propio «isolated `dispatch_root` shard», uno por captura
> que lo observó, **porque el gate CRC del despachador solo acepta una variante frente a los bytes
> con los que se compiló**.

Herramienta: `compile_overlays.py --force-interior <pc>`. Es lo que se usó y produjo los 4
fragmentos interiores (`4/4 exact-demand orphan interior(s) -> isolated island shards`). Por tanto
**no hace falta tocar el framework**: el soporte de entradas interiores existe y está documentado en
esta revisión.

### 27.6 Estado del candidato

| etapa | estado | evidencia |
|---|---|---|
| Reconstrucción | **hecha** | `verify_10d00.py`: sha256 del origen, comparación con la RAM |
| Quién y cómo se copia | **probado** | traza de arranque: 192 palabras contiguas, PC `0x8B8`, frame 51 |
| Naturaleza del bloque | **identificada** | desensamblado: GTE + divisiones, 3 `jr $ra` |
| Seeds como continuaciones | **confirmado** | tabla 27.4 |
| Mecanismo de entradas interiores | **identificado** | `--force-interior` + islas por (entrada, imagen) |
| Punto de llamada del juego | **NO identificado** | los `$ra` son del BIOS; los patrones literales no aparecen |
| Despacho seguro | **NO verificado** | no se ha reproducido la ruta que ejecuta el bloque |
| Corrección semántica | **NO probada** | requiere ejercitar la entrada |

### 27.7 Búsqueda del llamador del lado del juego: negativo, con motivo

Intentos hechos y resultado, para no repetirlos:

| búsqueda en el texto del EXE | resultado |
|---|---|
| `lui 0x8001` + `addiu/ori 0x0D00` (destino literal) | **0 coincidencias** |
| `lui 0x8001` + `addiu/ori 0x0F60` (origen literal) | **0 coincidencias** (de hecho no hay ningún inmediato `0x0F60`) |
| `li $a2,0x300` seguido de `jal` a vector `A0/B0/C0` | **0 coincidencias** |
| `jal 0x0000A0` (memcpy del kernel) en todo el texto | **0 coincidencias** |
| `jal` a cualquier dirección `< 0x1000` (zona baja del BIOS) | 1, y su contexto es **datos** (`0x06000020`, `0x00001000`…), no código |

Conclusión: el disparo de la copia **no es una llamada directa con direcciones literales**. O bien
el juego salta por registro (`jalr`) a una entrada del vector del kernel, o la copia la ejecuta el
BIOS por su cuenta durante el arranque. Ambas cosas son coherentes con que el `$ra` observado esté
en `0xBFC03BE8`/`0xBFC03BFC` y con que `$sp` sea la pila del juego.

Siguiente paso para cerrarlo (próxima sesión, con REA ya cargado): descompilar `func_80010DB4` y sus
vecinas, y listar los `jalr` con el registro que se carga justo antes; y si hace falta, añadir una
traza temporal que registre el primer `jalr` cuyo destino caiga en `[0x80000000, 0x80001000)`.

Nada de esto bloquea el candidato: lo que falta para subirlo de estado es **despacho** y
**corrección semántica**, no el llamador.

## 28. Rendimiento real medido: el intérprete NO es el cuello de botella

Por primera vez hay medida de FPS, que hasta ahora estaba declarada como no medida.

`PSX_FPS_TELEMETRY=1` con la build **release** durante 55 s (3.302 frames):

```text
[FPS] game: 59.9 fps (1.00x) | frames: 2881
[FPS] game: 60.0 fps (1.00x) | frames: 3001
[FPS] game: 59.6 fps (0.99x) | frames: 3121
[FPS] game: 60.4 fps (1.01x) | frames: 3302
```

**59,9–60,4 fps, ratio 1,00x sostenido.** El juego corre a velocidad completa; el runtime usa un
pacer de reloj de pared a 16,68 ms por frame.

### La cuenta que reordena las prioridades

Sesión larga: **41.156.498 instrucciones interpretadas** en ~17 minutos ≈ **40.000 instrucciones
por segundo**. Un Ryzen 7 5800X ejecuta del orden de miles de millones por segundo: el intérprete
consume del orden de **una milésima del 1 %** de la capacidad de un núcleo.

De ahí se sigue, con números:

| candidato | instrucciones interpretadas | % de la interpretación | valor real |
|---|---:|---:|---|
| bloque GTE `0x10D00` | 27,7 M | 67,4 % | ~0,01 % de un núcleo; **no se nota** |
| `0x12D000` | 8,9 M | 21,6 % | ídem |
| `0x12E000` | 2,3 M | 5,5 % | ídem |
| `0x12F000` | 1,0 M | 2,5 % | ídem |
| `0x12C000` | 0,19 M | **0,5 %** | despreciable |

**Conclusión honesta:** ni `0x12C000`, ni `0x12F000`, ni siquiera el bloque GTE son cuellos de
botella. Perseguir cobertura nativa por rendimiento no tiene recorrido: el juego ya va a 1,00x. El
valor de la cobertura nativa es otro: robustez ante rutas no visitadas, y reducir dependencia de un
intérprete que es correcto pero más frágil de validar.

Lo que un 1,00x **no** revela es el margen: el pacer fija la cadencia, así que mide «llega a 60»,
no «cuánto sobra». Para saber el margen real haría falta medir el tiempo de CPU por frame, que
queda como pendiente si alguna vez se quiere justificar una optimización.

### Respuesta a los dos puntos calientes anteriores

- `0x12C000`: 16 shards, 234 intervalos, 120 entradas; **todos** los PCs interpretados de la región
  caen dentro de rangos compilados (0 fuera). Es un tema de **despacho**, no de cobertura, y con
  0,5 % de la interpretación no compensa investigarlo.
- `0x12F000`: 6 shards, 84 intervalos, 60 entradas; 1–3 PCs fuera de rango en la base de la región
  (`0x8012F000/F00C/F010`), 2,5 % de la interpretación. Tampoco compensa.

Quedan documentados como **no prioritarios con motivo medido**, que es lo que pedía el plan si no
resultaban ser cuellos de botella.
