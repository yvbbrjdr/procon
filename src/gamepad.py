#!/usr/bin/env python3

import uinput

import procon

def main():
    uinput_events = (
        uinput.BTN_EAST,
        uinput.BTN_SOUTH,
        uinput.BTN_NORTH,
        uinput.BTN_WEST,
        uinput.BTN_DPAD_UP,
        uinput.BTN_DPAD_DOWN,
        uinput.BTN_DPAD_LEFT,
        uinput.BTN_DPAD_RIGHT,
        uinput.BTN_SELECT,
        uinput.BTN_START,
        uinput.BTN_MODE,
        uinput.BTN_TL,
        uinput.BTN_TL2,
        uinput.BTN_TR,
        uinput.BTN_TR2,
        uinput.BTN_THUMBL,
        uinput.BTN_THUMBR,
        uinput.ABS_X,
        uinput.ABS_Y,
        uinput.ABS_RX,
        uinput.ABS_RY
    )
    uinput_buttons_map = {
        procon.ProCon.Button.A: uinput.BTN_EAST,
        procon.ProCon.Button.B: uinput.BTN_SOUTH,
        procon.ProCon.Button.X: uinput.BTN_NORTH,
        procon.ProCon.Button.Y: uinput.BTN_WEST,
        procon.ProCon.Button.UP: uinput.BTN_DPAD_UP,
        procon.ProCon.Button.DOWN: uinput.BTN_DPAD_DOWN,
        procon.ProCon.Button.LEFT: uinput.BTN_DPAD_LEFT,
        procon.ProCon.Button.RIGHT: uinput.BTN_DPAD_RIGHT,
        procon.ProCon.Button.MINUS: uinput.BTN_SELECT,
        procon.ProCon.Button.PLUS: uinput.BTN_START,
        procon.ProCon.Button.SCREENSHOT: None,
        procon.ProCon.Button.HOME: uinput.BTN_MODE,
        procon.ProCon.Button.L: uinput.BTN_TL,
        procon.ProCon.Button.ZL: uinput.BTN_TL2,
        procon.ProCon.Button.R: uinput.BTN_TR,
        procon.ProCon.Button.ZR: uinput.BTN_TR2,
        procon.ProCon.Button.LS: uinput.BTN_THUMBL,
        procon.ProCon.Button.RS: uinput.BTN_THUMBR
    }
    buttons_prev = {}
    with uinput.Device(uinput_events, 'Nintendo Switch Pro Controller') as uinput_dev:
        def send_to_uinput(buttons, l_stick, r_stick, _, __, ___):
            nonlocal buttons_prev
            if not buttons_prev:
                buttons_prev = buttons
                return
            for k, v in buttons.items():
                if buttons_prev[k] != v:
                    uinput_button = uinput_buttons_map[k]
                    if not uinput_button:
                        continue
                    if v:
                        uinput_dev.emit(uinput_button, 1)
                    else:
                        uinput_dev.emit(uinput_button, 0)
            buttons_prev = buttons
            uinput_dev.emit(uinput.ABS_X, l_stick[0])
            uinput_dev.emit(uinput.ABS_Y, -l_stick[1])
            uinput_dev.emit(uinput.ABS_RX, r_stick[0])
            uinput_dev.emit(uinput.ABS_RY, -r_stick[1])
        procon.ProCon().start(send_to_uinput)

if __name__ == '__main__':
    main()
