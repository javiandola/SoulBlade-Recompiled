# Requisitos de empaquetado (AppImage) — verificado contra la revisión fijada

Documento de **requisitos**, no de construcción. La AppImage es la última fase; aquí se registra
lo que el código de esta revisión exige realmente, con la evidencia de dónde se comprobó.

## 1. Scripts disponibles en esta revisión

| script | contrato comprobado |
|---|---|
| `psxrecomp/tools/package_game_release.sh` | empaqueta la **release compilada** (no un kit): ejecutable, assets, catálogo de mods, OpenBIOS + aviso, `game.toml`/`game_options.toml`, avisos de terceros y la toolchain de overlays. **No** incluye fuentes, emisores, `psxrecomp/`, CLI, C generado ni volcado de BIOS. Soporta `--stage-only`. |
| `psxrecomp/tools/package_appimage.sh` | envuelve un payload ya validado. **No** compila nada. Exige que el llamante aporte `--app-run`, `--desktop-file`, `--icon` y `--payload`. |
| `psxrecomp/tools/package_setup_host.sh` | host de setup (no aplica a este proyecto). |

`package_appimage.sh` documenta en su cabecera dos condiciones duras:

> `AppRun` must use `usr/bin/<exe>` and `usr/share/<payload-name>`, preserving user
> settings/cards in writable data.
> Every run fails if the deployed executable has an unresolved library.

Es decir: el script **falla** si el binario desplegado tiene una biblioteca sin resolver, y el
AppRun es responsabilidad nuestra.

## 2. Resolución de rutas (comprobado en el código)

`recompiler/include/host_path.h:49`:

```cpp
inline std::filesystem::path host_resolve(const std::filesystem::path& root,
                                          const std::filesystem::path& path) {
    return host_absolute(host_path_is_absolute(path) ? path : root / path);
}
```

- Un valor **absoluto** se respeta tal cual.
- Un valor **relativo** se ancla al directorio del `game.toml` (`root`), no al directorio de
  trabajo actual. Esto explica lo observado en pruebas: `memcard_dir = "saves"` escribía en
  `source/SoulBladeRecomp/saves` aunque el binario se lanzara desde `build-*/`.

Consecuencia para el paquete: el `game.toml` del payload vive en una ruta **de solo lectura**
(`/tmp/.mount_*/usr/share/soulblade/`), así que un `memcard_dir` relativo apuntaría a un sitio no
escribible. El AppRun debe generar un `game.toml` en una ruta escribible con valores absolutos.

## 3. Diseño de AppRun propuesto (a implementar en la fase final)

```sh
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/soulblade"
mkdir -p "$DATA/saves"
# game.toml generado con rutas absolutas; el disco se lee del payload (solo lectura)
cat > "$DATA/game.toml" <<EOF
[game]
exe  = "$APPDIR/usr/share/soulblade/disc/SLUS_002.40"
disc = "$APPDIR/usr/share/soulblade/disc/Soul Blade (v1.1).cue"
[runtime]
memcard_dir = "$DATA/saves"
overlay_region_floor = "0x96000"
EOF
exec "$APPDIR/usr/bin/SoulBlade_Recompiled" --game "$DATA/game.toml"
```

Motivos, uno por línea:

- `disc` absoluto dentro del payload: el runtime resuelve el disco con `host_resolve`, y el punto
  de montaje de la AppImage cambia en cada ejecución (`$APPDIR` sí es estable dentro del proceso).
- `memcard_dir` absoluto bajo `$XDG_DATA_HOME`: guardados persistentes y escribibles, fuera del
  paquete de solo lectura, y separados de las tarjetas de desarrollo.
- `overlay_region_floor = "0x96000"`: viene del proyecto y es lo que hace nativa la región
  `0x96000` (ver `docs/overlays-aot.md` §19). Sin él, esa región cae al intérprete.

## 4. Contenido que debe llevar el paquete

- Ejecutable nativo x86-64 (`SoulBlade_Recompiled`).
- Bibliotecas que el binario cargue y que no vengan del sistema. `package_appimage.sh` aborta si
  queda alguna sin resolver; no hay que empaquetar Mesa ni los drivers de GPU del host.
- `bios/openbios.bin` + su aviso MIT (el proyecto ya los deposita junto al binario al enlazar).
- `game.toml` / `game_options.toml` (el generado por el AppRun manda).
- `disc/` con **copia verificada** del BIN y el CUE. El runtime valida la identidad del disco:
  `required_disc_fp = f28e869b8d0772…` en `game.toml`, así que una copia alterada se rechaza.
- Cobertura estática validada (`overlays_static*.c` enlazados) si se decide incluirla.
- Toolchain de overlays solo si se quiere autocompilación en la máquina del jugador.

## 5. Requisitos abiertos (bloquean dar el paquete por bueno)

1. **Validez de los guardados** (T18/D12): los frames del guardado histórico tienen el checksum
   interno inválido. Antes de distribuir hay que pasar `tests/diagnostico/check_mcd.py` sobre una
   tarjeta generada por el paquete.
2. **`disc` relativo vs absoluto**: hoy `game.toml` del proyecto lleva una ruta absoluta del equipo
   de desarrollo (`~/...`). El AppRun la sustituye, pero conviene además un modo
   `--disc` explícito como respaldo.
3. **Prueba real en Bazzite**: no se ha ejecutado nada en ese equipo; la compatibilidad de glibc
   está sin verificar (el equipo tiene glibc 2.43 y el de desarrollo 2.4x reciente).
4. **Tamaño**: el payload incluye el BIN (527 MB) más el ejecutable (~40 MB). Hay que decidir si se
   empaqueta el BIN completo o solo lo que el runtime lee (hoy lee por LBA, así que necesita la
   imagen completa).

## 6. Medido sobre el binario release actual (2026-10-25)

`file`: `ELF 64-bit LSB pie executable, x86-64 ... dynamically linked`.

**Suelo de glibc: `GLIBC_2.38`** (símbolos más altos: 2.33, 2.34, 2.35, 2.38).

Bibliotecas enlazadas (19 + cargador), **0 sin resolver**:

```text
ld-linux-x86-64.so.2  libc.so.6  libm.so.6  libstdc++.so.6  libgcc_s.so.1
libSDL3.so.0  libOpenGL.so.0  libGLX.so.0  libGLdispatch.so.0
libX11.so.6  libxcb.so.1  libXau.so.6  libXdmcp.so.6
libz.so.1  libzstd.so.1  libbrotlicommon.so.1  libbrotlidec.so.1  libbrotlienc.so.1
libcrypto.so.3
```

Lectura para el paquete:

- **glibc 2.38** es compatible con Bazzite documentado (glibc 2.43 en ese equipo) y con CachyOS.
  No hace falta base de compilación más antigua. *Salvedad: no probado en ese equipo.*
- `libSDL3.so.0` **debe empaquetarse**: no es una biblioteca que se pueda dar por presente en una
  distribución cualquiera. Es la única dependencia "de juego" realmente crítica.
- `libstdc++`/`libgcc_s` conviene empaquetarlas por el mismo motivo (versión del compilador).
- `libcrypto.so.3` (OpenSSL) también es de versión variable entre distribuciones.
- `libOpenGL`/`libGLX`/`libGLdispatch`/`libX11`/`libxcb` deben venir **del sistema**: son la
  interfaz con el driver de GPU del host y empaquetarlas rompería la aceleración.
- Wayland: el binario no enlaza `libwayland-*`; SDL3 resuelve Wayland en tiempo de ejecución, así
  que la sesión Wayland funciona mientras SDL3 empaquetada encuentre su backend.

## 7. La caché de shards NO viaja con el ejecutable por defecto

Comprobado: `build-release/` **no tiene directorio `cache/`**, así que la build release —la que se
distribuiría— se ejecuta con **0 shards** y todo el código de overlay que podría ser nativo cae al
intérprete. La build debug sí tiene 177 shards en `build-debug/cache/`.

Dos consecuencias:

1. **Requisito de empaquetado**: si se quiere cobertura nativa en el paquete, hay que copiar
   `cache/SLUS-00240/gcc/linux-x64/<tag>/` junto al ejecutable (el runtime la busca en
   `<exe-dir>/cache`). Alternativa: enlazar el conjunto estático (`GAME_OVERLAY_STATIC_C_PATH`).
2. **Dato de rendimiento**: la release sin ningún shard corrió 8 min 34 s a **1,00x** (T22). Es la
   confirmación más directa de que la cobertura de overlays no cambia el rendimiento percibido en
   esta máquina.

## 8. Corrección importante: el runtime exige `--disc` y resuelve el CUE junto a sí mismo

Comprobado ejecutando el binario release con distintas configuraciones:

| prueba | resultado |
|---|---|
| `game.toml` con `disc = "test.cue"`, sin `--disc` | **`no disc image selected; exiting`** (exit 1) |
| `--disc data/test.cue` con **solo** el CUE enlazado | arranca, pero `Disc Image Warning: No ISO9660 CD001 header` → **no encuentra el BIN** |
| `--disc data/test.cue` con CUE **y** BIN enlazados en el mismo directorio | **OK**: `disc region NTSC-U (serial SLUS-00240)` |

Conclusiones que corrigen lo escrito en el apartado 3:

1. **La clave `disc` de `game.toml` no la usa el runtime.** Solo la aprovecha el recompilador para
   generar. El ejecutable pide el disco por línea de comandos (o por un selector gráfico que en
   Linux, según su propio mensaje, no existe). El AppRun **debe** pasar
   `--disc "<APPDIR>/usr/share/soulblade/disc/<juego>.cue"`.
2. **El `FILE` del CUE se resuelve junto al propio CUE**, no siguiendo el enlace simbólico. Por eso
   hay que distribuir el **CUE y el BIN en el mismo directorio**; enlazar solo uno rompe la carga
   (falla en silencio con un aviso, no con un error).
3. Las rutas relativas en `--disc` funcionan (se resuelven contra el directorio de trabajo), así que
   el AppRun puede usar `cd` al payload y pasar una ruta relativa si lo prefiere.

AppRun corregido:

```sh
exec "$APPDIR/usr/bin/SoulBlade_Recompiled" \
     --game "$DATA/game.toml" \
     --disc "$APPDIR/usr/share/soulblade/disc/Soul Blade (v1.1).cue"
```
