#!/usr/bin/env python3

import math
import time

import hid

def to_int16(uint16):
    return -((uint16 ^ 0xFFFF) + 1) if uint16 & 0x8000 else uint16

class ProCon:
    VENDOR_ID = 0x057E
    PRODUCT_ID = 0x2009
    PACKET_SIZE = 64
    CALIBRATION_OFFSET = 0x603D
    CALIBRATION_LENGTH = 0x12
    COMMAND_RETRIES = 10
    RUMBLE_NEUTRAL = (0x00, 0x01, 0x40, 0x40)
    RUMBLE = (0x74, 0xBE, 0xBD, 0x6F)
    DEFAULT_IMU_SENSITIVITY = (0x03, 0x00, 0x00, 0x01)

    class OutputReportID:
        RUMBLE_SUBCOMMAND = 0x01
        RUMBLE = 0x10
        COMMAND = 0x80

    class InputReportID:
        SUBCOMMAND_REPLY = 0x21
        CONTROLLER_STATE = 0x30
        COMMAND_ACK = 0x81

    class CommandID:
        HANDSHAKE = 0x02
        HIGH_SPEED = 0x03
        FORCE_USB = 0x04

    class SubcommandID:
        SET_INPUT_REPORT_MODE = 0x03
        SPI_FLASH_READ = 0x10
        SET_PLAYER_LIGHTS = 0x30
        SET_HOME_LIGHT = 0x38
        ENABLE_IMU = 0x40
        SET_IMU_SENSITIVITY = 0x41
        ENABLE_VIBRATION = 0x48

    def __init__(self):
        self.subcommand_counter = 0
        self.dev = hid.device()
        self.dev.open(ProCon.VENDOR_ID, ProCon.PRODUCT_ID)
        self.handshake()
        self.high_speed()
        self.handshake()
        self.rumble_low = self.rumble_high = ProCon.RUMBLE_NEUTRAL
        self.rumble_expire = 0
        self.load_stick_calibration()
        self.enable_vibration(True)
        self.set_input_report_mode(ProCon.InputReportID.CONTROLLER_STATE)
        self.force_usb()
        self.set_player_lights(True, False, False, False)
        self.enable_imu(True)
        self.set_imu_sensitivity(ProCon.DEFAULT_IMU_SENSITIVITY)

    def start(self, callback):
        while True:
            state = self.recv()
            if state[0] != ProCon.InputReportID.CONTROLLER_STATE:
                continue
            buttons = {
                'A': state[3] & 0x08 > 0,
                'B': state[3] & 0x04 > 0,
                'X': state[3] & 0x02 > 0,
                'Y': state[3] & 0x01 > 0,
                'Up': state[5] & 0x02 > 0,
                'Down': state[5] & 0x01 > 0,
                'Left': state[5] & 0x08 > 0,
                'Right': state[5] & 0x04 > 0,
                '-': state[4] & 0x01 > 0,
                '+': state[4] & 0x02 > 0,
                'Screenshot': state[4] & 0x20 > 0,
                'Home': state[4] & 0x10 > 0,
                'L': state[5] & 0x40 > 0,
                'ZL': state[5] & 0x80 > 0,
                'R': state[3] & 0x40 > 0,
                'ZR': state[3] & 0x80 > 0,
                'LS': state[4] & 0x08 > 0,
                'RS': state[4] & 0x04 > 0
            }
            l_x = state[6] | ((state[7] & 0xF) << 8)
            l_y = (state[7] >> 4) | (state[8] << 4)
            r_x = state[9] | ((state[10] & 0xF) << 8)
            r_y = (state[10] >> 4) | (state[11] << 4)
            l_x = self.apply_stick_calibration(l_x, 0, 0)
            l_y = self.apply_stick_calibration(l_y, 0, 1)
            r_x = self.apply_stick_calibration(r_x, 1, 0)
            r_y = self.apply_stick_calibration(r_y, 1, 1)
            l_stick = (l_x, l_y)
            r_stick = (r_x, r_y)
            accel = (state[13] | state[14] << 8, state[15] | state[16] << 8, state[17] | state[18] << 8)
            gyro = (state[19] | state[20] << 8, state[21] | state[22] << 8, state[23] | state[24] << 8)
            accel = tuple(map(to_int16, accel))
            gyro = tuple(map(to_int16, gyro))
            battery = (state[2] & 0xF0) >> 4
            callback(buttons, l_stick, r_stick, accel, gyro, battery)
            if self.rumble_expire and int(time.time() * 1000) >= self.rumble_expire:
                self.send_rumble(False, False, 0)

    def load_stick_calibration(self):
        ok, reply = self.spi_flash_read(ProCon.CALIBRATION_OFFSET, ProCon.CALIBRATION_LENGTH)
        if not ok:
            raise RuntimeError('cannot load stick calibration')
        self.stick_calibration = [
            [
                [
                    ((reply[27] & 0xF) << 8) | reply[26],
                    ((reply[24] & 0xF) << 8) | reply[23],
                    ((reply[21] & 0xF) << 8) | reply[20]
                ],
                [
                    (reply[28] << 4) | (reply[27] >> 4),
                    (reply[25] << 4) | (reply[24] >> 4),
                    (reply[22] << 4) | (reply[21] >> 4)
                ]
            ],
            [
                [
                    ((reply[33] & 0xF) << 8) | reply[32],
                    ((reply[30] & 0xF) << 8) | reply[29],
                    ((reply[36] & 0xF) << 8) | reply[35]
                ],
                [
                    (reply[34] << 4) | (reply[33] >> 4),
                    (reply[31] << 4) | (reply[30] >> 4),
                    (reply[37] << 4) | (reply[36] >> 4)
                ]
            ]
        ]
        for i in range(len(self.stick_calibration)):
            for j in range(len(self.stick_calibration[i])):
                for k in range(len(self.stick_calibration[i][j])):
                    if self.stick_calibration[i][j][k] == 0xFFF:
                        self.stick_calibration[i][j][k] = 0
        self.stick_extends = [
            [
                [
                    -int(self.stick_calibration[0][0][0] * 0.7),
                    int(self.stick_calibration[0][0][2] * 0.7)
                ],
                [
                    -int(self.stick_calibration[0][1][0] * 0.7),
                    int(self.stick_calibration[0][1][2] * 0.7)
                ]
            ],
            [
                [
                    -int(self.stick_calibration[1][0][0] * 0.7),
                    int(self.stick_calibration[1][0][2] * 0.7)
                ],
                [
                    -int(self.stick_calibration[1][1][0] * 0.7),
                    int(self.stick_calibration[1][1][2] * 0.7)
                ]
            ]
        ]

    def apply_stick_calibration(self, value, stick, axis):
        value -= self.stick_calibration[stick][axis][1]
        if value < self.stick_extends[stick][axis][0]:
            self.stick_extends[stick][axis][0] = value
        if value > self.stick_extends[stick][axis][1]:
            self.stick_extends[stick][axis][1] = value
        if value > 0:
            return int(value * 0x7FFF / self.stick_extends[stick][axis][1])
        return int(value * -0x7FFF / self.stick_extends[stick][axis][0])

    def send(self, data):
        return self.dev.write(data) == len(data)

    def recv(self):
        return self.dev.read(ProCon.PACKET_SIZE)

    def send_command(self, id, wait_for_reply=True):
        data = (ProCon.OutputReportID.COMMAND, id)
        for _ in range(ProCon.COMMAND_RETRIES):
            if not self.send(data):
                continue
            if not wait_for_reply:
                return True
            reply = self.recv()
            if reply[0] == ProCon.InputReportID.COMMAND_ACK and reply[1] == id:
                return True
        return False

    def send_subcommand(self, id, param, wait_for_reply=True):
        data = (ProCon.OutputReportID.RUMBLE_SUBCOMMAND, self.subcommand_counter) + self.rumble_low + self.rumble_high + (id,) + param
        self.subcommand_counter = (self.subcommand_counter + 1) & 0xFF
        for _ in range(ProCon.COMMAND_RETRIES):
            if not self.send(data):
                continue
            if not wait_for_reply:
                return True, []
            reply = self.recv()
            if reply[0] == ProCon.InputReportID.SUBCOMMAND_REPLY and reply[14] == id:
                return True, reply
        return False, []

    def send_rumble(self, low, high, duration):
        self.rumble_low = ProCon.RUMBLE if low else ProCon.RUMBLE_NEUTRAL
        self.rumble_high = ProCon.RUMBLE if high else ProCon.RUMBLE_NEUTRAL
        self.rumble_expire = int(time.time() * 1000) + duration if (low or high) and duration else 0
        data = (ProCon.OutputReportID.RUMBLE, self.subcommand_counter) + self.rumble_low + self.rumble_high
        self.subcommand_counter = (self.subcommand_counter + 1) & 0xFF
        for _ in range(ProCon.COMMAND_RETRIES):
            if self.send(data):
                return True
        return False

    def handshake(self):
        return self.send_command(ProCon.CommandID.HANDSHAKE)

    def high_speed(self):
        return self.send_command(ProCon.CommandID.HIGH_SPEED)

    def force_usb(self):
        return self.send_command(ProCon.CommandID.FORCE_USB, False)

    def set_input_report_mode(self, mode):
        return self.send_subcommand(ProCon.SubcommandID.SET_INPUT_REPORT_MODE, (mode,))

    def spi_flash_read(self, addr, l):
        param = (addr & 0x000000FF, (addr & 0x0000FF00) >> 8, (addr & 0x00FF0000) >> 16, (addr & 0xFF000000) >> 24, l)
        return self.send_subcommand(ProCon.SubcommandID.SPI_FLASH_READ, param)

    def set_player_lights(self, one, two, three, four):
        param = (one << 0) | (two << 1) | (three << 2) | (four << 3)
        return self.send_subcommand(ProCon.SubcommandID.SET_PLAYER_LIGHTS, (param,))

    def set_home_light(self, brightness):
        intensity = 0
        if brightness > 0:
            if brightness < 65:
                intensity = (brightness + 5) // 10
            else:
                intensity = math.ceil(0xF * ((brightness / 100) ** 2.13))
        intensity = (intensity & 0xF) << 4
        param = (0x01, intensity, intensity, 0x00)
        return self.send_subcommand(ProCon.SubcommandID.SET_HOME_LIGHT, param)

    def enable_imu(self, enable):
        return self.send_subcommand(ProCon.SubcommandID.ENABLE_IMU, (int(enable),))

    def set_imu_sensitivity(self, sensitivity):
        return self.send_subcommand(ProCon.SubcommandID.SET_IMU_SENSITIVITY, sensitivity)

    def enable_vibration(self, enable):
        return self.send_subcommand(ProCon.SubcommandID.ENABLE_VIBRATION, (int(enable),))

def print_state(buttons, l_stick, r_stick, accel, gyro, battery):
    print('\33[2JButtons:')
    for k, v in buttons.items():
        if v:
            print('[{}]'.format(k), end=' ')
        else:
            print(' {} '.format(k), end=' ')
    print()
    print('L Stick: ({:6}, {:6})'.format(l_stick[0], l_stick[1]))
    print('R Stick: ({:6}, {:6})'.format(r_stick[0], r_stick[1]))
    print('Accelerometer: ({:6}, {:6}, {:6})'.format(accel[0], accel[1], accel[2]))
    print('Gyroscope: ({:6}, {:6}, {:6})'.format(gyro[0], gyro[1], gyro[2]))
    print('Battery: {}/9'.format(battery))

if __name__ == '__main__':
    ProCon().start(print_state)
