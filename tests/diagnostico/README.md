# Sonda de entrada SDL3

`sdlprobe.c` enumera joysticks y gamepads con la API de SDL3 y, en modo escucha,
imprime cada pulsación. Sirve para separar "el sistema/SDL no ve el mando" de
"el runtime no lo usa".

Compilar y usar:

```bash
cc -O1 -o sdlprobe sdlprobe.c $(pkg-config --cflags --libs sdl3)
./sdlprobe                                  # solo enumeración: nombres, GUID, isGamepad
PROBE_LISTEN=1 PROBE_SECS=25 ./sdlprobe      # escucha eventos 25 s
```

Salida de referencia en este equipo (GameSir T4n Lite):

```
joysticks detectados: 2
  [0] id=1 'Ducky One 3 SF RGB'  isGamepad=0     <- el teclado expone un joystick; SDL lo descarta
  [1] id=2 'Generic X-Box pad'  isGamepad=1
      abierto OK, nombre='Generic X-Box pad'
      guid=03008665373500004010000000010000
```

Botones SDL observados: 0=A, 1=B, 2=X, 3=Y, 6=START, 13/14=cruceta.
