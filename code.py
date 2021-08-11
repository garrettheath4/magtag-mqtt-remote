# SPDX-FileCopyrightText: 2021 Garrett Heath Koller, based on code by Scott Shawcroft, written for Adafruit Industries
# SPDX-License-Identifier: MIT

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
    # noinspection PyProtectedMember
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py; please add them there!")
    raise


CURRENT_TEMP_TEXT_INDEX = 0
DESIRED_TEMP_TEXT_INDEX = 1
CURRENT_TEMP_KEY = "perupino/garrett/fan_thermostat/current"
DESIRED_TEMP_KEY = "perupino/garrett/fan_thermostat/desired"
REQUEST_TEMP_TOPIC = "perupino/garrett/temperatureF/magtag/desired"

TEMP_UNITS = "F"
TEMP_INCREMENT = 0.2

SSID = secrets["ssid"]
HOSTNAME = secrets["broker"]
PORT = secrets["port"]

logger = adafruit_logging.getLogger("code.py")
logger.setLevel(adafruit_logging.INFO)

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


def _set_temp_and_text(temp_value: float, env_key: str, text_index: int):
    global environment
    if temp_value != environment[env_key]:
        environment[env_key] = temp_value
        magtag.set_text(f"{environment[env_key]:.1f} {TEMP_UNITS}",
                        text_index)
    else:
        logger.debug("Skipping screen redraw since temperature is the same")


def set_current_temp_and_text(current_temp: float):
    _set_temp_and_text(current_temp, CURRENT_TEMP_KEY, CURRENT_TEMP_TEXT_INDEX)


def set_desired_temp_and_text(desired_temp: float):
    _set_temp_and_text(desired_temp, DESIRED_TEMP_KEY, DESIRED_TEMP_TEXT_INDEX)


def increase_desired_temp():
    global environment
    set_desired_temp_and_text(environment[DESIRED_TEMP_KEY] + TEMP_INCREMENT)


def decrease_desired_temp():
    global environment
    set_desired_temp_and_text(environment[DESIRED_TEMP_KEY] - TEMP_INCREMENT)


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
    CURRENT_TEMP_KEY,
    lambda client, topic, message: set_current_temp_and_text(float(message)))
mqtt_client.add_topic_callback(
    DESIRED_TEMP_KEY,
    lambda client, topic, message: set_desired_temp_and_text(float(message)))

mqtt_client.enable_logger(adafruit_logging, log_level=adafruit_logging.INFO)
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
        # TODO: Update the display or NeoPixels to indicate an error has occurred
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
        # TODO: Keep incrementing temp (slowly) until button is released
        logger.debug("UP button pressed")
        increase_desired_temp()
        mqtt_client.publish(REQUEST_TEMP_TOPIC, environment[DESIRED_TEMP_KEY], qos=0)
        logger.info(f"Requested new desired temperature: {environment[DESIRED_TEMP_KEY]}")
    elif magtag.peripherals.button_c_pressed:
        logger.debug("DOWN button pressed")
        decrease_desired_temp()
        mqtt_client.publish(REQUEST_TEMP_TOPIC, environment[DESIRED_TEMP_KEY], qos=0)
        logger.info(f"Requested new desired temperature: {environment[DESIRED_TEMP_KEY]}")
