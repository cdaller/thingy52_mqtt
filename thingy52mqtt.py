#!/usr/bin/env python3

"""
https://github.com/IanHarvey/bluepy/blob/master/bluepy/thingy52.py
"""

from bluepy import btle, thingy52
import time

def main():

    mac_address = 'C2:9E:52:63:18:8A'
    thingy = thingy52.Thingy52(mac_address)

    try:
        # Set LED so that we know we are connected
        thingy.ui.enable()
        thingy.ui.set_led_mode_breathe(0x01, 50, 100) # 0x01 = RED
        print('LED set to breathe mode...')
        time.sleep(10)
        print('done...')


    finally:
        thingy.disconnect()
        del thingy


if __name__ == "__main__":
    main()