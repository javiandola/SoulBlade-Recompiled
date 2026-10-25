# Estados de juego y cómo distinguirlos

Documento de apoyo para no volver a confundir una demostración automática con una partida.

El modo attract de Soul Blade reproduce peleas completas (CPU vs CPU) con HUD, barras de vida,
temporizador y nombres. Por eso «ver un combate» no demuestra nada por sí solo. Esta es la
escala que se usa en los informes, de menos a más:

| # | Estado | Cómo se reconoce |
|---|---|---|
| 1 | Demostración automática (attract) | Combate o VS sin marcador 1P; el rótulo dice INSERT COIN; la cruceta no altera nada; la pantalla vuelve sola al título |
| 2 | Menú interactivo | Lista EDGE MASTER/OPTION/ARCADE… con una opción resaltada que responde a Arriba/Abajo |
| 3 | Entrada efectiva con START | START saca del attract al menú; en la selección de personaje inserta la moneda |
| 4 | Selección de modo | Círculo sobre ARCADE MODE lleva a la pantalla de personaje |
| 5 | Selección de personaje | Rejilla de retratos con el marcador **1P** sobre uno de ellos y «PRESS START+SELECT TO EXIT» |
| 6 | Combate real cargado | Pantalla VS (STAGE 1) y luego «BATTLE 1» con HUD y temporizador |
| 7 | Control efectivo del personaje | La entrada del usuario cambia el estado de forma **dependiente de la dirección**, y START abre el menú **1P PAUSE** |

## Marcadores que delatan una partida del jugador

- Marcador **1P** sobre el retrato elegido en la selección de personaje.
- Menú **1P PAUSE** (CANCEL / COMMAND / VOL / RESET) al pulsar START durante el combate.
- Textos en segunda persona: **YOU WIN / YOU LOSE** al final del asalto.

## Marcadores que delatan una demostración

- Rótulo **INSERT COIN** sin marcador 1P.
- START devuelve al título en lugar de pausar.
- Mantener IZQUIERDA y mantener DERECHA produce capturas idénticas (la entrada se ignora).

## Banco de pruebas determinista

El emulador es determinista: desde el mismo savestate y sin entrada, dos ejecuciones dan
**capturas idénticas byte a byte** (0 píxeles distintos). Eso permite usar la diferencia de
píxeles como medida fiable:

```
python3 $D savestate op=save slot=1     # congela el estado
python3 $D savestate op=load slot=1     # vuelve a él
python3 $D press 0xFF7F 180             # IZQUIERDA durante 3 s (180 frames)
python3 $D screenshot                   # captura y compara con la pasada neutra
```

Comparaciones ya hechas (ver `tests/PRUEBAS.md`, T7): neutro vs neutro = 0 píxeles;
neutro vs izquierda = 53.327; neutro vs derecha = 65.122; izquierda vs derecha = 41.321.
