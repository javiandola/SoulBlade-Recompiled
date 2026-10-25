/* Sonda de diagnóstico SDL3 (API 3.4: Gamepad): qué dispositivos ve, cuáles son
 * gamepads, qué GUID tienen y si reportan botones. Solo lectura. */
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    if (!SDL_Init(SDL_INIT_GAMEPAD | SDL_INIT_JOYSTICK | SDL_INIT_EVENTS)) {
        printf("SDL_Init falló: %s\n", SDL_GetError());
        return 1;
    }
    int n = 0;
    SDL_JoystickID *ids = SDL_GetJoysticks(&n);
    printf("joysticks detectados: %d\n", n);
    for (int i = 0; i < n; i++) {
        SDL_JoystickID id = ids[i];
        const char *name = SDL_GetJoystickNameForID(id);
        int isgp = SDL_IsGamepad(id);
        printf("  [%d] id=%u '%s'  isGamepad=%d\n", i, (unsigned)id,
               name ? name : "(sin nombre)", isgp);
        if (isgp) {
            SDL_Gamepad *gp = SDL_OpenGamepad(id);
            if (!gp) { printf("      open FALLÓ: %s\n", SDL_GetError()); continue; }
            SDL_Joystick *j = SDL_GetGamepadJoystick(gp);
            SDL_GUID g = SDL_GetJoystickGUID(j);
            char buf[64] = {0};
            SDL_GUIDToString(g, buf, sizeof buf);
            printf("      abierto OK, nombre='%s'\n      guid=%s\n",
                   SDL_GetGamepadName(gp), buf);
            SDL_CloseGamepad(gp);
        }
    }

    const char *listen = SDL_getenv("PROBE_LISTEN");
    if (listen && listen[0] == '1') {
        printf("escuchando 6 s: pulsa botones del mando...\n");
        fflush(stdout);
        SDL_Gamepad *pads[8] = {0};
        for (int i = 0; i < n && i < 8; i++)
            if (SDL_IsGamepad(ids[i])) pads[i] = SDL_OpenGamepad(ids[i]);
        const char *secs = SDL_getenv("PROBE_SECS");
        Uint64 dur = (Uint64)(secs ? atoi(secs) : 6) * 1000u;
        Uint64 t0 = SDL_GetTicks();
        while (SDL_GetTicks() - t0 < dur) {
            SDL_Event e;
            while (SDL_PollEvent(&e)) {
                if (e.type == SDL_EVENT_GAMEPAD_BUTTON_DOWN) {
                    printf("  GAMEPAD_BUTTON_DOWN which=%u button=%d\n",
                           (unsigned)e.gbutton.which, (int)e.gbutton.button);
                    fflush(stdout);
                } else if (e.type == SDL_EVENT_JOYSTICK_BUTTON_DOWN) {
                    printf("  JOYSTICK_BUTTON_DOWN which=%u button=%d\n",
                           (unsigned)e.jbutton.which, (int)e.jbutton.button);
                    fflush(stdout);
                }
            }
            SDL_Delay(10);
        }
        for (int i = 0; i < n && i < 8; i++) if (pads[i]) SDL_CloseGamepad(pads[i]);
    }
    SDL_free(ids);
    SDL_Quit();
    return 0;
}
