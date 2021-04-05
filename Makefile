.PHONY: all prod dev clean FORCE

TARGET = /Volumes/CIRCUITPY
PROD_LIB = adafruit-circuitpython-bundle-6.x-mpy-20210314/lib
DEV_LIB = adafruit-circuitpython-bundle-py-20210321/lib

MODULE_DIRS = adafruit_bitmap_font adafruit_display_text adafruit_io adafruit_magtag adafruit_minimqtt adafruit_portalbase
MODULE_FILES = adafruit_fakerequests adafruit_requests adafruit_logging neopixel simpleio

code.py: FORCE
	cp code.py "$(TARGET)/code.py"

prod: code.py
	for dir in $(MODULE_DIRS); do \
		cp -rfv "$(PROD_LIB)/$$dir" "$(TARGET)/lib/" ; \
	done
	for file in $(MODULE_FILES); do \
		cp -fv "$(PROD_LIB)/$$file.mpy" "$(TARGET)/lib/" ; \
	done

dev: code.py
	for dir in $(MODULE_DIRS); do \
		cp -rfv "$(DEV_LIB)/$$dir" "$(TARGET)/lib/" ; \
	done
	for file in $(MODULE_FILES); do \
		cp -fv "$(DEV_LIB)/$$file.py" "$(TARGET)/lib/" ; \
	done

all: prod

clean:
	rm -rf "$(TARGET)"/lib/*
