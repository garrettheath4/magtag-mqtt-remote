# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
from adafruit_magtag.magtag import MagTag

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = f"https://io.adafruit.com/api/v2/{secrets['aio_username']}/feeds/tasks"
DATA_LOCATION = ["last_value"]
HEADERS = { 'X-AIO-Key': secrets['aio_key'] }


def text_transform(val):
    return '\n'.join([f"Task: {t}" for t in val.split('\n')])


magtag = MagTag(
    url=DATA_SOURCE,
    headers=HEADERS,
    json_path=DATA_LOCATION,
)

magtag.network.connect()

magtag.add_text(
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        (magtag.graphics.display.height // 2) - 1,
    ),
    text_scale=2,
    text_transform=text_transform,
    text_anchor_point=(0.5, 0.5),
)

try:
    value = magtag.fetch()
    print("Response is", value)
except (ValueError, RuntimeError) as e:
    print("Some error occurred, retrying! -", e)

#TODO: Detect button presses by checking `magtag.peripherals.button_a_pressed` (or b, c, or d)

magtag.exit_and_deep_sleep(60)
