# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

import time

import adafruit_logging
from adafruit_magtag.magtag import MagTag
import adafruit_minimqtt.adafruit_minimqtt as minimqtt

# noinspection PyUnresolvedReferences
import wifi
# noinspection PyUnresolvedReferences
import socketpool

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


CURRENT_TEMP_TEXT_INDEX = 0
DESIRED_TEMP_TEXT_INDEX = 1
CURRENT_TEMP_KEY = "perupino/garrett/temperatureF/current"
DESIRED_TEMP_KEY = "perupino/garrett/temperatureF/desired"

TEMP_UNITS = "F"

SSID = secrets["ssid"]
HOSTNAME = secrets["broker"]
PORT = secrets["port"]

logger = adafruit_logging.getLogger("code.py")
logger.setLevel(adafruit_logging.DEBUG)

magtag = MagTag(
    # debug=True,
)

# try:
#     magtag.peripherals.neopixel_disable = True
# except Exception as neopixel_ex:
#     logger.error("Failed to turn off NeoPixels; skipping")
#     logger.error("%s: %s", type(neopixel_ex).__name__, neopixel_ex.args)

# MagTag display is 296 pixels wide and 128 pixels high

# Add current temperature label
magtag.add_text(
    text_position=(magtag.graphics.display.width // 2, 40),
    text_scale=4,
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)
magtag.set_text(f"-- {TEMP_UNITS}", 0, False)

# Add desired temperature label
magtag.add_text(
    text_position=(magtag.graphics.display.width // 2, 90),
    text_scale=2,
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)
magtag.set_text(f"-- {TEMP_UNITS}", 1, True)

environment = {
    CURRENT_TEMP_KEY: 0.0,
    DESIRED_TEMP_KEY: 0.0,
}


def _set_temp(temp_value: float, env_key: str, text_index: int):
    global environment
    if temp_value != environment[env_key]:
        environment[env_key] = temp_value
        magtag.set_text(f"{environment[env_key]:.1f} {TEMP_UNITS}",
                        text_index)
    else:
        logger.debug("Skipping screen redraw since temperature is the same")


def set_current_temp(current_temp: float):
    _set_temp(current_temp, CURRENT_TEMP_KEY, CURRENT_TEMP_TEXT_INDEX)


def set_desired_temp(desired_temp: float):
    _set_temp(desired_temp, DESIRED_TEMP_KEY, DESIRED_TEMP_TEXT_INDEX)


logger.info("WiFi connecting to %s", SSID)
magtag.network.connect()
logger.info("WiFi connected to %s", SSID)

# Set up a MiniMQTT Client
mqtt_client = minimqtt.MQTT(
    broker=HOSTNAME,
    port=PORT,
    is_ssl=False,
    # keep_alive=75,
    socket_pool=socketpool.SocketPool(wifi.radio),
)

# callback(client, topics, message)
mqtt_client.add_topic_callback(
    CURRENT_TEMP_KEY, lambda client, topic, message: set_current_temp(float(message)))
mqtt_client.add_topic_callback(
    DESIRED_TEMP_KEY, lambda client, topic, message: set_desired_temp(float(message)))

mqtt_client.enable_logger(adafruit_logging, log_level=adafruit_logging.DEBUG)
mqtt_client.connect()

mqtt_client.subscribe([(CURRENT_TEMP_KEY, 1), (DESIRED_TEMP_KEY, 1)])

# Start a blocking message loop...
# NOTE: NO code below this loop will execute
# NOTE: Network reconnection is handled within this loop
while True:
    try:
        mqtt_client.is_connected()
    except minimqtt.MMQTTException:
        logger.error("MQTT client is NOT connected")
        #TODO: Update the display or NeoPixels to indicate an error has occurred
        continue
    # magtag.peripherals.neopixels.fill((0xFF, 0xFF, 0xFF))
    # noinspection PyBroadException
    try:
        mqtt_client.loop()
    except Exception as loop_ex:  # catch *all* exceptions
        logger.error("Failed to get data; retrying")
        logger.error("%s: %s", type(loop_ex).__name__, loop_ex.args)
        # magtag.peripherals.neopixels[0] = (0xFF, 0, 0)
        # Don't resubscribe since the on_connect method always subscribes
        try:
            mqtt_client.reconnect(resub_topics=False)
        except Exception as reconnect_ex:
            logger.error("Failed to reconnect; resetting")
            logger.error("%s: %s", type(reconnect_ex).__name__, reconnect_ex.args)
            magtag.peripherals.deinit()
            magtag.exit_and_deep_sleep(1)
        continue

    if magtag.peripherals.button_b_pressed:
        logger.debug("UP button pressed")
        #TODO: Send an MQTT message to turn UP the thermostat
    elif magtag.peripherals.button_c_pressed:
        logger.debug("DOWN button pressed")
        #TODO: Send an MQTT message to turn DOWN the thermostat
