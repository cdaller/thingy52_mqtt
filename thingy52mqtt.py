#!/usr/bin/env python3

"""
Reading values from thingy device and send them as mqtt messages.
Handles automatic reconnection if bluetooth connection is lost.

Source is derived from the bluepy library from Ian Harvey and Nordic Semiconductor

Bluepy repository: https://github.com/IanHarvey/bluepy/blob/master/bluepy/thingy52.py
Nordic Semiconductor Python: https://devzone.nordicsemi.com/b/blog/posts/nordic-thingy52-raspberry-pi-python-interface
Nordic Semiconductor NodeJS: https://github.com/NordicPlayground/Nordic-Thingy52-Thingyjs

dependencies installation on raspberry pi:
pip3 install bluepy
pip3 install paho-mqtt

to find the MAC address: 
sudo hcitool lescan

Usage:
thingy52mqtt.py C2:9E:52:63:18:8A  --no-mqtt --gas --temperature --humidity --pressure --battery --orientation --keypress --tap --sleep 5 -v -v -v -v -v

"""

import paho.mqtt.publish as publish
from bluepy import btle, thingy52
import time
import os
import argparse
import binascii
import logging
import signal, sys

next_event_second = 0
args = None
thingy = None

# last values from received from notification:
temperature = None
pressure = None
humidity = None
eco2 = None
tvoc = None
color = None
button = None
tapDirection = None
tapCount = None
orientation = None
battery = None


def setupSignalHandler():
    signal.signal(signal.SIGINT, _sigIntHandler)
    signal.signal(signal.SIGTERM, _sigIntHandler)
    logging.debug('Installed signal handlers')

def _sigIntHandler(signum, frame):
    global thingy

    logging.info('Received signal to exit')
    if thingy:
        thingy.disconnect()
        mqttSend('connected', 0, '')
    exit(0)

def setupLogging():
    '''Sets up logging'''
    global args
    if args.v > 5:
        verbosityLevel = 5
    else:
        verbosityLevel = args.v
    # https://docs.python.org/2/library/logging.html#logging-levels
    verbosityLevel = (5 - verbosityLevel)*10

    # print('loglevel %d v:%d' % (verbosityLevel, args.v))

    format = '%(asctime)s %(levelname)-8s %(message)s'
    if args.logfile is not None:
        logging.basicConfig(filename=args.logfile, level=verbosityLevel, format=format)
    else:
        logging.basicConfig(level=verbosityLevel, format=format)

    #logging.debug('debug') # 10
    #logging.info('info') # 20
    #logging.warn('warn') # 30
    #logging.error('error') # 40
    #logging.critical('critical') # 50

    # logger = logging.getLogger(os.path.basename(__file__))

    # logging.basicConfig(level=logging.DEBUG,
    #                 format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    #                 datefmt='%yyyy%m%d-%H:%M:%S')


def mqttSendValues(notificationDelegate):
    global temperature
    global pressure
    global humidity
    global eco2
    global tvoc
    global color
    global button
    global tapDirection
    global tapCount
    global orientation
    global battery

    if args.temperature:
        mqttSend('temperature', temperature, '°C')
        temperature = None
    if args.pressure:
        mqttSend('pressure', pressure, 'hPa')
        pressure = None
    if args.humidity:
        mqttSend('humidity', humidity, '%')
        humidity = None
    if args.gas:
        mqttSend('eco2', eco2, 'bbm')
        mqttSend('tvoc', tvoc, 'ppb')
        eco2 = None
        tvoc = None
    if args.color:
        mqttSend('color', color, '')
        color = None
    if args.tap:
        mqttSend('tapdirection', tapDirection, '')
        mqttSend('tapcount', tapCount, '')
        tapDirection = None
        tapCount = None
    if args.orientation:
        mqttSend('orientation', orientation, '')
        orientation = None
    if args.battery:
        mqttSend('battery', battery, '%')
        battery = None

def mqttSend(key, value, unit):
    global args

    if value is None:
        logging.debug('no value given, do nothing for key %s' % key)
        return

    if isinstance(value, int):
        logging.debug('Sending MQTT messages key %s value %d%s' % (key, value, unit))
    elif isinstance(value, float) | isinstance(value, int):
        logging.debug('Sending MQTT messages key %s value %.2f%s' % (key, value, unit))
    elif isinstance(value, str):
        logging.debug('Sending MQTT messages key %s value %s%s' % (key, value, unit))
    else:
        logging.debug('Sending MQTT messages key %s value %s%s' % (key, value, unit))

    if args.mqttdisabled:
        logging.debug('MQTT disabled, not sending message')
    else:
        try:
            topic = args.topicprefix + key
            payload = value
            logging.debug('MQTT message topic %s, payload %s' % (topic, str(payload)))
            publish.single(topic, 
                        payload = payload,
                        hostname = args.hostname, 
                        port = args.port, 
                        retain = True)
        except:
            logging.error("Failed to publish message, details follow")
            logging.error("hostname=%s topic=%s payload=%s" % (args.hostname, topic, payload))
            logging.error(sys.exc_info()[0])

class MQTTDelegate(btle.DefaultDelegate):

    def handleNotification(self, hnd, data):
        global temperature
        global pressure
        global humidity
        global eco2
        global tvoc
        global color
        global button
        global tapDirection
        global tapCount
        global orientation

        #Debug print repr(data)
        if (hnd == thingy52.e_temperature_handle):
            teptep = binascii.b2a_hex(data)
            value = self._str_to_int(teptep[:-2]) + int(teptep[-2:], 16) / 100.0
            temperature = value
            
        elif (hnd == thingy52.e_pressure_handle):
            pressure_int, pressure_dec = self._extract_pressure_data(data)
            value = pressure_int + pressure_dec / 100.0
            pressure = value

        elif (hnd == thingy52.e_humidity_handle):
            teptep = binascii.b2a_hex(data)
            value = self._str_to_int(teptep)
            humidity = value

        elif (hnd == thingy52.e_gas_handle):
            eco2, tvoc = self._extract_gas_data(data)
            eco2 = eco2
            tvoc = tvoc

        elif (hnd == thingy52.e_color_handle):
            teptep = binascii.b2a_hex(data)
            red, green, blue, clear = self._extract_color_data(data)
            color = "0x%0.2X%0.2X%0.2X" %(red, green, blue)
            # logging.debug('color %s red %d, green %d, blue %d, clear %d' % (color, red, green, blue, clear))

        elif (hnd == thingy52.ui_button_handle):
            teptep = binascii.b2a_hex(data)
            value = int(teptep) # 1 = pressed, 0 = released
            button = value
            # send button press instantly without waiting for timeout:
            mqttSend('button', button, '')

        elif (hnd == thingy52.m_tap_handle):
            direction, count = self._extract_tap_data(data)
            tapDirection = direction
            tapCount = direction

        elif (hnd == thingy52.m_orient_handle):
            teptep = binascii.b2a_hex(data)
            value = int(teptep)
            # 1 = led top left
            # 2 = led top right / left side up
            # 3 = led bottom right/bottom up
            # 0 = led bottom left/ right side up 
            orientation = value

        # elif (hnd == thingy52.m_heading_handle):
        #     teptep = binascii.b2a_hex(data)
        #     #value = int (teptep)
        #     logging.debug('Notification: Heading: {}'.format(teptep))
        #     #self.mqttSend('heading', value, 'degrees')

        # elif (hnd == thingy52.m_gravity_handle):
        #     teptep = binascii.b2a_hex(data)
        #     logging.debug('Notification: Gravity: {}'.format(teptep))        

        # elif (hnd == thingy52.s_speaker_status_handle):
        #     teptep = binascii.b2a_hex(data)
        #     logging.debug('Notification: Speaker Status: {}'.format(teptep))

        # elif (hnd == thingy52.s_microphone_handle):
        #     teptep = binascii.b2a_hex(data)
        #     logging.debug('Notification: Microphone: {}'.format(teptep))

        else:
            teptep = binascii.b2a_hex(data)
            logging.debug('Notification: UNKOWN: hnd {}, data {}'.format(hnd, teptep))

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
        eco2 = int(teptep[:2], 16) + (int(teptep[2:4], 16) << 8)
        tvoc = int(teptep[4:6], 16) + (int(teptep[6:8], 16) << 8)
        return eco2, tvoc

    def _extract_color_data(self, data):
        """ Extract color data from data string. """
        teptep = binascii.b2a_hex(data)
        red = int(teptep[:2], 16)
        green = int(teptep[2:4], 16)
        blue = int(teptep[4:6], 16)
        clear = int(teptep[6:8], 16)
        return red, green, blue, clear

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

    # mqtt arguments
    parser.add_argument('--no-mqtt', dest='mqttdisabled', action='store_true', default=False)
    parser.add_argument('--host', dest='hostname', default='localhost', help='MQTT hostname')
    parser.add_argument('--port', dest='port', default=1883, type=int, help='MQTT port')
    parser.add_argument('--topic-prefix', dest='topicprefix', default="/home/thingy/", help='MQTT topic prefix to post the values, prefix + key is used as topic')

    parser.add_argument('--sleep', dest='sleep', default=60, type=int, help='Interval to publish values.')

    parser.add_argument("--logfile", help="If specified, will log messages to the given file (default log to terminal)", default=None)
    parser.add_argument("-v", help="Increase logging verbosity (can be used up to 5 times)", action="count", default=0)

    args = parser.parse_args()
    return args

def setNotifications(enable):
    global thingy
    global args

    if args.temperature:
        thingy.environment.set_temperature_notification(enable)
    if args.pressure:
        thingy.environment.set_pressure_notification(enable)
    if args.humidity:
        thingy.environment.set_humidity_notification(enable)
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
    logging.debug('Enabling selected sensors...')

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

def connect(notificationDelegate):
    global args
    global thingy

    connected = False
    while not connected:
        try:
            logging.info('Try to connect to ' + args.mac_address)
            thingy = thingy52.Thingy52(args.mac_address)
            connected = True
            logging.info('Connected...')
            thingy.setDelegate(notificationDelegate)
            mqttSend('connected', 1, '')
        except btle.BTLEException as ex:
            connected = False
            logging.debug('Could not connect, sleeping a while before retry')
            time.sleep(args.sleep) # FIXME: use different sleep value??


def main():
    global args
    global thingy
    global battery

    args = parseArgs()

    setupLogging()

    setupSignalHandler()

    notificationDelegate = MQTTDelegate()

    connectAndReadValues = True
    while connectAndReadValues:
        connect(notificationDelegate)

        #print("# Setting notification handler to default handler...")
        #thingy.setDelegate(thingy52.MyDelegate())

        try:
            # Set LED so that we know we are connected
            thingy.ui.enable()
            thingy.ui.set_led_mode_breathe(0x01, 50, 3000) # color 0x01 = RED, intensity, delay between breathes
            logging.debug('LED set to breathe mode...')

            enableSensors()
            setNotifications(True)
            
            counter = args.count
            timeNextSend = time.time()
            while connectAndReadValues:
                # logging.debug('Loop start')

                if args.battery:
                    value = thingy.battery.read()
                    battery = value

                thingy.waitForNotifications(timeout = args.timeout)

                counter -= 1
                if counter == 0:
                    logging.debug('count reached, exiting...')
                    connectAndReadValues = False

                if time.time() > timeNextSend:
                    mqttSendValues(notificationDelegate)
                    timeNextSend = time.time() + args.sleep

        except btle.BTLEDisconnectError as e:
            logging.debug('BTLEDisconnectError %s' % str(e))
            logging.info('Disconnected...')
            mqttSend('connected', 0, '')
            thingy = None
    
    if thingy:
        try:
            thingy.disconnect()
            #del thingy
        finally:
            mqttSend('connected', 0, '')

if __name__ == "__main__":
    main()