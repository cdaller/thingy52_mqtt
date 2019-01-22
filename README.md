# thingy52_mqtt

This little project is reading values from Nordic Semiconductors Thingy:52 device and 
post them as MQTT messages to my raspberry pi MQTT broker.

## Installation

The project uses the bluepy bluetooth python library to connect to the thingy:52 device. Should work on all 
Linux systems (only tested on Raspberry Pi Raspbian):

```sh
pip3 install bluepy
pip3 install paho-mqtt
```

If you want to run the script as systemd service, use the service class as example. See systemd/systemctl documentation how to do it properly.

## Run

The MAC address of the device can be retrieved by

```sh
sudo hcitool lescan
```

Then start the script with the MAC address and the parameters to choose which sensor values you want to read.
Parameters are also used to define the MQTT broker to send the values to, if wanted:

Only print values every 5 seconds (via debug messages), do not publish them via MQTT:

```sh
thingy52mqtt.py <MAC_ADDRESS> --no-mqtt --gas --temperature --humidity --pressure \
  --battery --orientation --keypress --tap \
  --sleep 5 -v -v -v -v -v
```

Read some values and publish them via MQTT every minute, do not print debug info.
The sensor name is appended to the topic-prefix given as parameter.

```sh
thingy52mqtt.py <MAC_ADDRESS> --temperature --humidity --pressure --battery --sleep 60 \
  --host localhost --port 1883 --topic-prefix /home/thingy52/
```
