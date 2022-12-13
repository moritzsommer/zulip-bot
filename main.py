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
from typing import Iterable

import time
import os.path

import pytz
import zulip

__author__ = "Moritz Sommer"
__version__ = "1.0"

INFO_TIME = datetime.time(11, 25, 00, tzinfo=pytz.timezone('Europe/Berlin'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main_loop():
    logger.info("Initializing client ...")
    config_file = os.path.join(os.path.dirname(__file__), "sample-config.ini")
    config = configparser.ConfigParser()
    config.read(config_file)
    zulip_client = zulip.Client(config_file=config_file)
    stream_name = config['message']['stream']
    logger.info("Starting into main loop ...")
    while True:
        try:
            # Calculate time until message and sleep
            sleep_time = calculate_sleep_time()
            logger.info("Scheduling next message for {}.".format(sleep_time))
            logarithmic_sleep(sleep_time)

            # Send messages
            send_plan(zulip_client, stream_name)

            # Prevent fast retriggering
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received KeyobardInterrupt. Exiting …")
            return
        except Exception as e:
            logger.error("Exception in main loop:", exc_info=e)


# Calculate waiting time
def calculate_sleep_time() -> datetime.datetime:
    now = datetime.datetime.now(tz=INFO_TIME.tzinfo)
    res = now.replace(hour=INFO_TIME.hour, minute=INFO_TIME.minute, second=INFO_TIME.second,
                      microsecond=INFO_TIME.microsecond)
    if res <= now:
        res += datetime.timedelta(days=1)

    # Skip the weekend
    if res.weekday() >= 5:
        res += datetime.timedelta(days=7 - res.weekday())

    return res


# Halve the waiting time up to a defined threshold
def logarithmic_sleep(target: datetime.datetime):
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
