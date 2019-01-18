#!/usr/bin/env python3

"""
https://github.com/IanHarvey/bluepy/blob/master/bluepy/thingy52.py

dependencies installation on raspberry pi:
pip3 install bluepy

to find the MAC address: 
sudo hcitool lescan

thingy52mqtt C2:9E:52:63:18:8A 

"""

from bluepy import btle, thingy52
# from bluepy.btle import UUID, Peripheral, ADDR_TYPE_RANDOM, DefaultDelegate
import time
import os
import argparse
import binascii
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

logger = logging.getLogger(os.path.basename(__file__))
logger.debug('Starting...')


next_event_second = 0

class MQTTDelegate(btle.DefaultDelegate):
    global next_event_second

    def mqttSend(self, key, value):
        logger.debug('Sending MQTT messages key %s value %s' % (key, value))
    
    def handleNotification(self, hnd, data):
        # if time.time() < next_event_second:
        #     logger.debug('Notification received, but timeout not yet reached')
        #     return

        #Debug print repr(data)
        if (hnd == thingy52.e_temperature_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Temp received:  {}.{} degCelcius'.format(
                        self._str_to_int(teptep[:-2]), int(teptep[-2:], 16)))
            # mqttSend(self, 'temperature', )
            
        elif (hnd == thingy52.e_pressure_handle):
            pressure_int, pressure_dec = self._extract_pressure_data(data)
            logger.debug('Notification: Press received: {}.{} hPa'.format(
                        pressure_int, pressure_dec))

        elif (hnd == thingy52.e_humidity_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Humidity received: {} %'.format(self._str_to_int(teptep)))

        elif (hnd == thingy52.e_gas_handle):
            eco2, tvoc = self._extract_gas_data(data)
            logger.debug('Notification: Gas received: eCO2 ppm: {}, TVOC ppb: {} %'.format(eco2, tvoc))

        elif (hnd == thingy52.e_color_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Color: {}'.format(teptep))            

        elif (hnd == thingy52.ui_button_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Button state [1 -> released]: {}'.format(self._str_to_int(teptep)))

        elif (hnd == thingy52.m_tap_handle):
            direction, count = self._extract_tap_data(data)
            logger.debug('Notification: Tap: direction: {}, count: {}'.format(direction, self._str_to_int(count)))

        elif (hnd == thingy52.m_orient_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Orient: {}'.format(teptep))

        elif (hnd == thingy52.m_quaternion_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Quaternion: {}'.format(teptep))

        elif (hnd == thingy52.m_stepcnt_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Step Count: {}'.format(teptep))

        elif (hnd == thingy52.m_rawdata_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Raw data: {}'.format(teptep))

        elif (hnd == thingy52.m_euler_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Euler: {}'.format(teptep))

        elif (hnd == thingy52.m_rotation_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Rotation matrix: {}'.format(teptep))

        elif (hnd == thingy52.m_heading_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Heading: {}'.format(teptep))

        elif (hnd == thingy52.m_gravity_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Gravity: {}'.format(teptep))        

        elif (hnd == thingy52.s_speaker_status_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Speaker Status: {}'.format(teptep))

        elif (hnd == thingy52.s_microphone_handle):
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: Microphone: {}'.format(teptep))

        else:
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: UNKOWN: hnd {}, data {}'.format(hnd, teptep))
            

    def _str_to_int(self, s):
        """ Transform hex str into int. """
        i = int(s, 16)
        if i >= 2**7:
            i -= 2**8
        return i    

    def _extract_pressure_data(self, data):
        """ Extract pressure data from data string. """
        teptep = binascii.b2a_hex(data)
        pressure_int = 0
        for i in range(0, 4):
                pressure_int += (int(teptep[i*2:(i*2)+2], 16) << 8*i)
        pressure_dec = int(teptep[-2:], 16)
        return (pressure_int, pressure_dec)

    def _extract_gas_data(self, data):
        """ Extract gas data from data string. """
        teptep = binascii.b2a_hex(data)
        eco2 = int(teptep[:2]) + (int(teptep[2:4]) << 8)
        tvoc = int(teptep[4:6]) + (int(teptep[6:8]) << 8)
        return eco2, tvoc

    def _extract_tap_data(self, data):
        """ Extract tap data from data string. """
        teptep = binascii.b2a_hex(data)
        direction = teptep[0:2]
        count = teptep[2:4]
        return (direction, count)


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('mac_address', action='store', help='MAC address of BLE peripheral')
    parser.add_argument('-n', action='store', dest='count', default=0,
                            type=int, help="Number of times to loop data, if set to 0, loop endlessly")
    parser.add_argument('-t', action='store', dest='timeout', type=float, default=2.0, help='time between polling')
    parser.add_argument('--temperature', action="store_true",default=False)
    parser.add_argument('--pressure', action="store_true",default=False)
    parser.add_argument('--humidity', action="store_true",default=False)
    parser.add_argument('--gas', action="store_true",default=False)
    parser.add_argument('--color', action="store_true",default=False)
    parser.add_argument('--keypress', action='store_true', default=False)
    parser.add_argument('--battery', action='store_true', default=False)
    parser.add_argument('--tap', action='store_true', default=False)

    parser.add_argument('--host', dest='hostname', default='localhost', help='MQTT hostname')
    parser.add_argument('--port', dest='port', default=1883, type=int, help='MQTT port')
    parser.add_argument('--topicprefix', dest='topicprefix', default="/home/thingy/", help='MQTT topic prefix to post the values')
    parser.add_argument('--sleep', dest='sleep', default=60, type=int, help='Interval to publish values.')

    args = parser.parse_args()
    return args


def main():

    args = parseArgs()

    logger.info('Connecting to ' + args.mac_address)
    thingy = thingy52.Thingy52(args.mac_address)
    logger.info('Connected...')

    #print("# Setting notification handler to default handler...")
    #thingy.setDelegate(thingy52.MyDelegate())
    logger.debug("# Setting notification handler to new handler...")
    thingy.setDelegate(MQTTDelegate())

    try:
        # Set LED so that we know we are connected
        thingy.ui.enable()
        thingy.ui.set_led_mode_breathe(0x01, 50, 100) # 0x01 = RED
        logger.debug('LED set to breathe mode...')

        # Enabling selected sensors
        logger.debug('Enabling selected sensors...')
        # Environment Service
        if args.temperature:
            thingy.environment.enable()
            thingy.environment.configure(temp_int=1000)
            thingy.environment.set_temperature_notification(True)
        if args.pressure:
            thingy.environment.enable()
            thingy.environment.configure(press_int=1000)
            thingy.environment.set_pressure_notification(True)
        if args.humidity:
            thingy.environment.enable()
            thingy.environment.configure(humid_int=1000)
            thingy.environment.set_humidity_notification(True)
        if args.gas:
            thingy.environment.enable()
            thingy.environment.configure(gas_mode_int=1)
            thingy.environment.set_gas_notification(True)
        if args.color:
            thingy.environment.enable()
            thingy.environment.configure(color_int=1000)
            thingy.environment.configure(color_sens_calib=[0,0,0])
            thingy.environment.set_color_notification(True)
        # User Interface Service
        if args.keypress:
            thingy.ui.enable()
            thingy.ui.set_btn_notification(True)
        if args.battery:
            thingy.battery.enable()
        # Motion Service
        if args.tap:
            thingy.motion.enable()
            thingy.motion.configure(motion_freq=200)
            thingy.motion.set_tap_notification(True)

        counter = args.count
        while True:
            logger.debug('Loop start')

            if args.battery:
                logger.info('Battery: %i %%' % thingy.battery.read())

            thingy.waitForNotifications(timeout = args.timeout)

            counter -= 1
            if counter == 0:
                logger.debug('count reached, exiting...')
                break

    finally:
        logger.info('disconnecting thingy...')
        thingy.disconnect()
        del thingy


if __name__ == "__main__":
    main()