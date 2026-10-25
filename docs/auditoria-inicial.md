# Auditoría inicial — Proyecto Soul Blade (port nativo Linux)

Fecha: 2026-10-24 (CEST)
Autor: Hermes Agent (ejecución autónoma sobre el equipo local)

---

## 1. Sistema comprobado (hechos medidos en esta sesión)

| Elemento | Valor |
|---|---|
| Distribución | CachyOS x86_64 (Arch) |
| Kernel | 7.3.0-4-cachyos (SMP PREEMPT_DYNAMIC, compilado 2026-10-23) |
| Escritorio | KDE Plasma 6.8.1, KWin sobre Wayland |
| CPU | AMD Ryzen 7 5800X, 8 núcleos / 16 hilos, hasta 4,85 GHz |
| RAM | 15,53 GiB (≈10 GiB disponibles al inicio) |
| GPU | AMD Radeon RX 7700 XT (Navi 32), 11 GiB VRAM, RADV/Mesa 26.2.5 |
| Raíz | Btrfs, 928 GB, 47 % usado (≈495 GB libres) |
| Volumen extra | ext4, 915 GB (biblioteca de juegos) |
| Shell de trabajo | Bash/Python para scripts (no fish) |

## 2. Herramientas disponibles (ya instaladas, no se instaló nada)

- git 2.56.0, cmake 4.4.4, ninja 1.13.2, meson 1.12.1, make 4.4.1
- gcc/g++ 16.2.1 y clang/clang++ 23.1.3
- python 3.14.7, python-numpy 2.5.4, ccache 4.14.1
- SDL3 3.4.18 (cumple el mínimo 3.4 del framework), sdl2-compat 2.32.74, SDL_image, SDL3_ttf
- OpenGL: Mesa 26.2.5 + glew + glfw; Vulkan ICD radv + vulkan-headers 1.4.363
- fmt 12.2.0, boost 1.92, spdlog, libpng, zlib-ng, pipewire 1.6.10
- pkg-config 3.0.10, glslangValidator 16.6.0

**Conclusión:** no hace falta instalar ningún paquete del sistema para arrancar el build del framework ni del runtime. Se evitó `pacman -S` por completo (registro de paquetes instalados: vacío).

## 3. Originales del juego (sin modificar)

Ruta: `<project>/Soul Blade V1.1/`

| Archivo | Tamaño | SHA-1 / notas |
|---|---|---|
| `Soul Blade (v1.1).bin` | 527.412.480 bytes (224.240 sectores de 2352) | SHA-1 `e1a48d3e5c3614be1a5f3fe7f1f4036dbc6c5b94` (coincide con el dato del usuario) |
| `Soul Blade (v1.1).cue` | 83 bytes, CRLF | 1 pista `MODE2/2352`, INDEX 01 00:00:00 |
| `Soul Blade.psv` | 3.809.916 bytes | Guardado de memory card; **no usado todavía** |

Huellas adicionales calculadas (para control de deriva):

- SHA-256 BIN: `e1b2931759985322b1c863c5e9adfeb12272447a4e244e2f906125bf5a05b120`
- MD5 BIN: `055175fbf6e6e48caea1fad0664f42af`
- CRC32 BIN: `aa74b3c9`

Ningún archivo original se ha renombrado, copiado dentro de Git ni modificado.

## 4. Identidad del disco (verificada por sonda propia, no por el nombre)

`psxrecomp/tools/new_project_layout/probe_disc.py` leyó la imagen y obtuvo:

- Volumen ISO9660: `SOULBLADE`
- Ejecutable de arranque: `SLUS_002.40` (1.034.240 bytes) → serial **SLUS-00240** (región USA)
- Cabecera PS-X EXE: load `0x80010000`, entry `0x80010FBC`, text `0x000FC000`, stack `0x801FFFF0`
- SHA-256 del boot EXE: `51b14b312a79f5aec13167cfc6426c97baf0ff713cfc66e9ab4d28991a8f3b6e`
- Huella TOC `psxrecomp-toc-v1`: `f28e869b8d07728a4b86cfe89a89872013f1a7331b483b1346677957205da19c`
- Seeds iniciales (entry + destinos JAL del EXE de arranque): **1453**

Contenido del sistema de archivos:

```
SYSTEM.CNF            69 B
SLUS_002.40        1.034.240 B   (código principal, 0xFC000 de texto)
SOUL.BNS          25.845.760 B   (archivo/overlay del juego)
SOULOVL.BNS        4.704.256 B   (overlays)
SOULSYS.BNS          620.544 B   (sistema)
SOULXA.XAS       398.993.408 B   (audio XA)
3MIN.DMY          27.688.960 B   (relleno/dummy)
```

El CUE declara **una sola pista**. El propio `verify-disc` acepta la pista principal y marca
`subchannel status: unknown`. La sonda avisa de que un dump de una sola pista falla las
puertas multi-pista de netplay/catálogo; **no** es un problema para jugar en local.

**Pendiente / no confirmado:** no se ha podido cotejar la huella con una base de datos
Redump en línea desde este equipo (no hay verificación remota de la ficha del disco). La
identidad (SLUS-00240 + volumen SOULBLADE + 224.240 sectores) es consistente con
*Soul Blade (USA) (v1.1)*, y el contenido del ISO es coherente con el juego, pero se
clasifica como **hipótesis fuerte, no hecho verificado contra Redump**.

## 5. Repositorios investigados

### 5.1 `fabioap-cpu/SoulBlade_Recomp` — NO DISPONIBLE

Comprobaciones realizadas:

- `git ls-remote https://github.com/fabioap-cpu/SoulBlade_Recomp.git HEAD` → pide credenciales
  (GitHub responde 404 a repos inexistentes/privados).
- `api.github.com/repos/fabioap-cpu/SoulBlade_Recomp` → **404 Not Found**.
- `api.github.com/repos/fabioap-cpu/SoulBlade_Recomp/releases` → **404**.
- La cuenta `fabioap-cpu` **sí existe** (id 68659468) y tiene repos públicos, pero
  **ninguno** se llama SoulBlade_Recomp. Sí tiene `WWF-SmackDown-2-Recomp`,
  `Forza-Horizon-2-Recomp` y `Burnout-Revenge-Recomp` con la misma técnica.
- `recomp.fyi` (índice de proyectos de recompilación) lista el proyecto con la anotación
  **“repo missing”** para SoulBlade_Recomp. Fuentes secundarias (recompendium.com,
  retro-gamer.jp, foro outerspace) siguen describiéndolo como recompilación estática de la
  versión USA hecha con PSXRecomp, **para Windows**.

**Conclusión:** el repositorio está retirado o hecho privado; no existe copia pública
legítima localizada. No se clonó ningún repositorio de nombre parecido (evitado riesgo de
suplantación). El proyecto de juego hay que construirlo nosotros.

### 5.2 `fabioap-cpu/WWF-SmackDown-2-Recomp` — plantilla pública del método

Clonado en `source/wwfref` con fines de auditoría. Contiene **solo** README, `docs/` y los
punteros de submódulos (no incluye el código del juego, que no es público). Datos útiles:

- Submódulo `psxrecomp` → `fabioap-cpu/psxrecomp` fijado en **`20ae6db9b4d62e142f6ccaaa960356dcbf65e06e`**
  (2026-08-25, “Merge pull request #232 …”)
- Submódulo `recomp-ui` → `mstan/recomp-ui` en `87bbf43c…`
- Releases orientadas a Windows (`WWF-SmackDown-2-Recomp.exe`), con `game.toml` `[disc] path`.
- Confirma el patrón: proyecto de juego = repo propio + `psxrecomp` como submódulo + `generated/` versionado.

Ese commit **es ancestro** de la HEAD actual del framework (comprobado con
`git merge-base --is-ancestor`), así que el pin del proyecto original es compatible con la
versión actual.

### 5.3 `RetroPortingToolKit/psxrecomp` — framework elegido

- Clonado completo con submódulos en `source/psxrecomp`.
- HEAD: `31df2e1e0e0a6525733e68ff70e72ecbef84bb09` (2026-10-22), `git describe` = `nightly-870-g31df2e1e`,
  `RELEASE_NOTES` v0.3.2-alpha.
- Submódulos fijados por el framework: `lib/recomp-net` `e53059306824edf4f0aec4aae5ae65151b18535f`,
  `lib/retcomm-rbengine` `2a03e73693acee0fb78076ea058642c931bef12e`.
- Licencia: **PolyForm Noncommercial 1.0.0** (Copyright 2026 Matthew Stanley). Uso no comercial;
  prohíbe redistribución comercial. OpenBIOS (PCSX-Redux) es MIT y se incluye como `bios/openbios.bin`.
  libchdr BSD-3, fmt/toml11/ELFIO/rabbitizer vendorizados.
- Soporte de build declarado y comprobado: Linux (GCC/Clang), CMake ≥3.20, Ninja, pkg-config,
  C++20 para el recompilador y C99+C++17 para el runtime, SDL3 ≥3.4.

## 6. Estado de compilación del framework (hecho real)

```
cmake -S recompiler -B recompiler/build -G Ninja -DCMAKE_BUILD_TYPE=Release   → OK
cmake --build recompiler/build -j12                                          → OK (348/348)
```

Artefactos: `psxrecomp-game`, `psxrecomp-bios`, `psxrecomp-analyze`, `psxrecomp-toml`.
Log: `logs/recompiler-configure.log`, `logs/recompiler-build.log`.

## 7. Proyecto de juego creado

Scaffolding oficial (`tools/new_project_layout/setup_project.sh`) en
`source/SoulBladeRecomp`, commit inicial `04a49cd`, con:

- `game.toml` autocompletado (serial, entry, hashes, disc → ruta absoluta al CUE original)
- `seeds/ghidra_funcs.txt` (1453 seeds)
- `disc/SLUS_002.40` (copia del boot EXE extraída del disco; **no** es el BIN completo)
- `.gitignore` del scaffold que ya excluye `*.bin`, `*.cue`, `*.psv`-equivalentes (`*.mcd`,
  `*.mcr`), `bios/`, `disc/`, `saves/`, `prepared_disc/`
- `psxrecomp` como submódulo (clon propio en `31df2e1e`), sin `recomp-ui`, sin CI, sin netplay
- Log: `logs/scaffold.log`

`verify-disc` → exit 0 (“Main track accepted; subchannel status: unknown”).

## 8. Problemas detectados

1. **El repositorio del juego no existe** → se construye proyecto propio con el scaffolding
   oficial y las seeds propias. Riesgo: el trabajo de seeds/overlays que el autor ya hubiera
   hecho hay que rehacerlo desde cero (ver `plan.md`).
2. **Bug de plataforma en `psxrecomp_cli.py` en Linux:** `_build_recompiler_targets()` llama a
   `ensure_toolchain_for_rebuild()` (que descarga el pack portable) y después comprueba
   `activate_embedded_toolchain()`, que **siempre devuelve False fuera de Windows**
   (`if sys.platform != "win32": return False`). Resultado: `generate` aborta con
   *“Toolchain ensure succeeded but bin/ is not usable for emitters”* aunque haya cmake/ninja
   del sistema. **Solución aplicada:** usar `--no-toolchain-download`, que toma la rama de
   herramientas nativas. No se ha parcheado el framework (se documenta como incidencia upstream).
3. **Dump de una sola pista**: bloquea las puertas de netplay/catálogo multi-pista. Sin efecto
   para el objetivo local. Si el disco original tuviera pistas de audio CDDA, faltarían; el
   contenido del ISO (SOULXA.XAS de 399 MB) sugiere que el audio va por XA, pero no está probado.
4. **`.psv`**: no se ha inspeccionado ni usado. El port usa su propio directorio `saves/`.
   Su compatibilidad con el formato de memory card del runtime no está demostrada.

## 9. Decisiones iniciales

- Framework: `RetroPortingToolKit/psxrecomp` en `31df2e1e` (no el pin antiguo `20ae6db9`), porque
  el soporte Linux actual está en la HEAD y el pin del proyecto original es ancestro suyo.
- Proyecto de juego propio (`SoulBladeRecomp`) en lugar de esperar a un repo inaccesible.
- Build con herramientas del sistema (gcc 16.2.1 / clang 23.1.3), release, `-j12`.
- Los originales se quedan donde están; `game.toml` apunta al CUE por ruta absoluta.
