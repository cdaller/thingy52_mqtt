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
import signal

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%yyyy%m%d-%H:%M:%S')

logger = logging.getLogger(os.path.basename(__file__))
logger.debug('Starting...')


next_event_second = 0
args = None
thingy = None
notificationDelegate = None

def setupSigInt():
    '''Sets up our Ctrl + C handler'''
    signal.signal(signal.SIGINT, _sigIntHandler)
    logging.debug("Installed Ctrl+C handler.")

def _sigIntHandler(signum, frame):
    global thingy

    '''This function handles Ctrl+C for graceful shutdown of the programme'''
    logging.info("Received Ctrl+C. Exiting.")
    thingy.disconnect()
    # stopMQTT()
    exit(0)


class MQTTDelegate(btle.DefaultDelegate):

    def handleNotification(self, hnd, data):
        # global next_event_second
        # global args

        # if time.time() < next_event_second:
        #     logger.debug('Notification received, but timeout not yet reached')
        #     return
        # next_event_second = time.time() + args.sleep

        #Debug print repr(data)
        if (hnd == thingy52.e_temperature_handle):
            teptep = binascii.b2a_hex(data)
            value = self._str_to_int(teptep[:-2]) + int(teptep[-2:], 16) / 100.0
            self.mqttSend('temperature', value, '°C')
            
        elif (hnd == thingy52.e_pressure_handle):
            pressure_int, pressure_dec = self._extract_pressure_data(data)
            value = pressure_int + pressure_dec / 100.0
            self.mqttSend('pressure', value, 'hPa')

        elif (hnd == thingy52.e_humidity_handle):
            teptep = binascii.b2a_hex(data)
            value = self._str_to_int(teptep)
            self.mqttSend('humidity', value, '%')

        elif (hnd == thingy52.e_gas_handle):
            eco2, tvoc = self._extract_gas_data(data)
            self.mqttSend('eCO2', eco2, 'ppm')
            self.mqttSend('tvoc', tvoc, 'ppb')

        elif (hnd == thingy52.e_color_handle):
            teptep = binascii.b2a_hex(data)
            self.mqttSend('color', teptep, '')

        elif (hnd == thingy52.ui_button_handle):
            teptep = binascii.b2a_hex(data)
            value = int(teptep) # 1 = pressed, 0 = released
            #logger.debug('Notification: Button state [1 -> released]: {}'.format(self._str_to_int(teptep)))
            self.mqttSend('button', value, '')

        elif (hnd == thingy52.m_tap_handle):
            direction, count = self._extract_tap_data(data)
            self.mqttSend('tapdirection', direction, '')
            self.mqttSend('tapcount', count, '')

        elif (hnd == thingy52.m_orient_handle):
            teptep = binascii.b2a_hex(data)
            value = int(teptep)
            # 1 = led top left
            # 2 = led top right / left side up
            # 3 = led bottom right/bottom up
            # 0 = led bottom left/ right side up 
            self.mqttSend('orientation', value, '')

        # elif (hnd == thingy52.m_heading_handle):
        #     teptep = binascii.b2a_hex(data)
        #     #value = int (teptep)
        #     logger.debug('Notification: Heading: {}'.format(teptep))
        #     #self.mqttSend('heading', value, 'degrees')

        # elif (hnd == thingy52.m_gravity_handle):
        #     teptep = binascii.b2a_hex(data)
        #     logger.debug('Notification: Gravity: {}'.format(teptep))        

        # elif (hnd == thingy52.s_speaker_status_handle):
        #     teptep = binascii.b2a_hex(data)
        #     logger.debug('Notification: Speaker Status: {}'.format(teptep))

        # elif (hnd == thingy52.s_microphone_handle):
        #     teptep = binascii.b2a_hex(data)
        #     logger.debug('Notification: Microphone: {}'.format(teptep))

        else:
            teptep = binascii.b2a_hex(data)
            logger.debug('Notification: UNKOWN: hnd {}, data {}'.format(hnd, teptep))

    def mqttSend(self, key, value, unit):
        if isinstance(value, int):
            logger.debug('Sending MQTT messages key %s value %d%s' % (key, value, unit))
        elif isinstance(value, float) | isinstance(value, int):
            logger.debug('Sending MQTT messages key %s value %.2f%s' % (key, value, unit))
        elif isinstance(value, str):
            logger.debug('Sending MQTT messages key %s value %s%s' % (key, value, unit))
        else:
            logger.debug('Sending MQTT messages key %s value %s%s' % (key, value, unit))


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
        direction = int(teptep[0:2])
        count = int(teptep[2:4])
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
    parser.add_argument('--orientation', action='store_true', default=False)

    parser.add_argument('--host', dest='hostname', default='localhost', help='MQTT hostname')
    parser.add_argument('--port', dest='port', default=1883, type=int, help='MQTT port')
    parser.add_argument('--topicprefix', dest='topicprefix', default="/home/thingy/", help='MQTT topic prefix to post the values')
    parser.add_argument('--sleep', dest='sleep', default=60, type=int, help='Interval to publish values.')

    args = parser.parse_args()
    return args

def setNotifications(enable):
    global thingy
    global args

    if args.temperature:
        thingy.environment.set_temperature_notification(enable)
    if args.pressure:
        thingy.environment.set_humidity_notification(enable)
    if args.pressure:
        thingy.environment.set_pressure_notification(enable)
    if args.gas:
        thingy.environment.set_gas_notification(enable)
    if args.color:
        thingy.environment.set_color_notification(enable)
    if args.tap:
        thingy.motion.set_tap_notification(enable)
    if args.orientation:
        thingy.motion.set_orient_notification(enable)

def enableSensors():
    global thingy
    global args

    # Enabling selected sensors
    logger.debug('Enabling selected sensors...')

    if args.temperature:
        thingy.environment.enable()
        thingy.environment.configure(temp_int=1000)
    if args.pressure:
        thingy.environment.enable()
        thingy.environment.configure(press_int=1000)
    if args.humidity:
        thingy.environment.enable()
        thingy.environment.configure(humid_int=1000)
    if args.gas:
        thingy.environment.enable()
        thingy.environment.configure(gas_mode_int=1)
    if args.color:
        thingy.environment.enable()
        thingy.environment.configure(color_int=1000)
        thingy.environment.configure(color_sens_calib=[0,0,0])
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

def connect():
    global args
    global thingy
    global notificationDelegate

    connected = False
    while not connected:
        try:
            logger.info('Try to connect to ' + args.mac_address)
            thingy = thingy52.Thingy52(args.mac_address)
            connected = True
            logger.info('Connected...')
            thingy.setDelegate(notificationDelegate)
            notificationDelegate.mqttSend('connected', 1, '')
        except btle.BTLEException as ex:
            connected = False
            logger.debug('Could not connect, sleeping a while before retry')
            time.sleep(args.sleep) # FIXME: use different sleep value??


def main():
    global args
    global thingy
    global notificationDelegate

    args = parseArgs()

    notificationDelegate = MQTTDelegate()

    while True:
        connect()

        #print("# Setting notification handler to default handler...")
        #thingy.setDelegate(thingy52.MyDelegate())

        try:
            # Set LED so that we know we are connected
            thingy.ui.enable()
            thingy.ui.set_led_mode_breathe(0x01, 50, 100) # 0x01 = RED
            logger.debug('LED set to breathe mode...')

            enableSensors()
            
            counter = args.count
            while True:
                logger.debug('Loop start')

                # enable notifications 
                setNotifications(True)

                if args.battery:
                    value = thingy.battery.read()
                    notificationDelegate.mqttSend('battery', value, '%')

                thingy.waitForNotifications(timeout = args.timeout)

                counter -= 1
                if counter == 0:
                    logger.debug('count reached, exiting...')
                    break

                # disable notifications before sleeping time 
                # all except button press - button triggers timeout and loop starts again
                setNotifications(False)
                thingy.waitForNotifications(timeout = args.sleep)

        except btle.BTLEDisconnectError as e:
            logger.debug('BTLEDisconnectError %s' % str(e))
            logger.info("Disconnected...")
            notificationDelegate.mqttSend('connected', 0, '')
            del thingy

        # finally:
        #     logger.info('disconnecting thingy...')
        #     thingy.disconnect()
        #     del thingy

if __name__ == "__main__":
    main()