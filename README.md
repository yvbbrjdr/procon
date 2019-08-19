# procon

A Nintendo Switch Pro Controller Linux device driver (wired) in Python.

This driver emits the controller events to a `uinput` device. Only buttons and
sticks are supported, but the test program can read accelerometer and gyroscope
data. Setting home light intensity, player lights, and rumbling are supported by
the driver API.

## Quickstart

1. Clone this repository and enter the directory:
    ```bash
    git clone https://github.com/yvbbrjdr/procon
    cd procon
    ```
1. Copy the udev rules and insert the `uinput` kernel module:
    ```bash
    sudo cp udev/* /etc/udev/rules.d
    sudo modprobe uinput
    ```
1. Install the required dependencies:
    ```bash
    pip install --user -r requirements.txt
    ```
1. Plug in the Nintendo Switch Pro Controller to your computer.
1. Run the test program to check if the device and the driver work:
    ```bash
    src/procon.py
    ```
1. Run the device driver:
    ```bash
    src/gamepad.py
    ```
