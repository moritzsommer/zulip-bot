#!/usr/bin/env python3

# Copyright 2020 by Michael Thies <mail@mhthies.de>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Zulip bot for sending Mensa Academica Aachen's menu to the PLT Zulip chat every workday at 11:25.
"""
import configparser
import datetime
import logging

import time
import os.path

import pytz
import zulip

__author__ = "Moritz Sommer"
__version__ = "1.0"

INFO_TIME = datetime.time(8, 30, 00, tzinfo=pytz.timezone('Europe/Berlin'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main_loop():
    logger.info("Initializing client ...")
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    config = configparser.ConfigParser()
    config.read(config_file)
    zulip_client = zulip.Client(config_file=config_file)
    stream_name = config['message']['stream']
    logger.info("Starting into main loop ...")
    while True:
        try:
            # Calculate time until message and sleep
            sleep_time = calculate_sleep_time(datetime.datetime.now(tz=INFO_TIME.tzinfo), 0, 2)
            logger.info("Scheduling next message for {}.".format(sleep_time))
            logarithmic_sleep(sleep_time)

            # Send messages
            # ToDO Plan
            send_plan(zulip_client, stream_name)

            # Prevent fast retriggering
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received KeyobardInterrupt. Exiting …")
            return
        except Exception as e:
            logger.error("Exception in main loop:", exc_info=e)


def calculate_sleep_time(day_init: datetime.datetime, day_a: int, day_b: int) -> datetime.datetime:
    """
    Calculate the waiting time from an initial date to the next of two given days of the week.

    :param day_init: initial date
    :param day_a: weekday one, can be a number 0-6
    :param day_b: weekday two, can be a number 0-6
    """

    res = day_init.replace(hour=INFO_TIME.hour, minute=INFO_TIME.minute, second=INFO_TIME.second,
                           microsecond=INFO_TIME.microsecond)

    if res <= day_init:
        res += datetime.timedelta(days=1)
        delta_a = datetime.timedelta(days=(day_a - res.weekday()) % 7)
        delta_b = datetime.timedelta(days=(day_b - res.weekday()) % 7)
        res += delta_a if delta_a < delta_b else delta_b

    return res


def logarithmic_sleep(target: datetime.datetime):
    """
    Halve the waiting time until the given threshold.

    :param target: waiting time
    """
    while True:
        diff = (target - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds()
        if diff < 0.2:
            time.sleep(diff)
            return
        else:
            time.sleep(diff / 2)


def send_plan(client: zulip.Client, stream: str):
    logger.info("Fetching menu data ...")

    logger.info("Fetching menu data finished.")

    logger.info("Sending messages ...")

    logger.info("Sending messages finished.")


if __name__ == "__main__":
    main_loop()
