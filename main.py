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

# This version of the bot was developed by Moritz Sommer <moritz.sommer@rwth-aachen.de>.
"""
Zulip bot for sending a message containing kitchen duties to the IAT Zulip chat every Monday and Wednesday at 08:30.
"""
import configparser
import datetime
import logging

import time
import os.path

import pytz
import zulip

from tinydb import TinyDB, Query

__author__ = "Moritz Sommer"
__version__ = "1.0"

INFO_TIME = datetime.time(8, 30, 00, tzinfo=pytz.timezone('Europe/Berlin'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main_loop():
    """
    While true loop for sending the plan twice a week. The script is robust and can be restarted without problems.
    """
    logger.info("Initializing client ...")
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    config = configparser.ConfigParser()
    config.read(config_file)
    zulip_client = zulip.Client(config_file=config_file)
    stream_name = config['message']['stream']
    logger.info("Initialising database ...")
    update_database(zulip_client, stream_name)
    set_first_user()
    logger.info("Starting into main loop ...")
    while True:
        try:
            logger.info("Updating database ...")
            update_database(zulip_client, stream_name)
            # Calculate time until message and sleep
            sleep_time = calculate_sleep_time(datetime.datetime.now(tz=INFO_TIME.tzinfo), 0, 2)
            logger.info("Scheduling next message for {}.".format(sleep_time))
            logarithmic_sleep(sleep_time)
            # Send messages
            send_plan(zulip_client, stream_name)
            # Set next user on Wednesday
            if datetime.date.today().isocalendar().weekday == 3:
                set_next_user()
            # Prevent fast retriggering
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Exiting …")
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
    # Check whether send today
    if res <= day_init:
        res += datetime.timedelta(days=1)
        # Time interval to both dates
        delta_a = datetime.timedelta(days=(day_a - res.weekday()) % 7)
        delta_b = datetime.timedelta(days=(day_b - res.weekday()) % 7)
        # Chose date which is closer
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
    """
    Format and send the message containing kitchen duties.

    :param client: Zulip client
    :param stream: Zulip stream
    """
    logger.info("Fetching plan data ...")
    users = get_user()
    dates = get_dates()
    logger.info("Fetching plan data finished.")
    formatted_plan = (
            "# Küchenplan {:%d.%m.%Y}\n\n"
            "| Mitarbeiter | Woche | Montag | Freitag |\n|---|---|---|---|\n".format(datetime.date.today())
            + "\n".join(
                "| {} | {} | {} | {} |".format(
                    user["name"],
                    date[0],
                    date[1],
                    date[2])
                for user, date in zip(users, dates))
            + "\n\n Küchendienstaufgaben:\n\n* {} \n* {} \n* {} \n* {} \n* {}".format(
                "Getränke im Kühlschrank nachfüllen (mindestens 50% Wasser, Rest Club Mate und Cola)",
                "Leergut ins Archiv bringen und leere Kästen in die Küche stellen",
                "Wenn Getränke sich dem Ende neigen, Justin zwecks Bestellung Bescheid geben",
                "Wenn Spülmaschine voll, anstellen und ausräumen (spätestens Freitag, auch wenn nicht voll)",
                "Handtücher auswechseln, benutzte Handtücher bei Martina abgeben")
    )
    subject = "Küchenplan {:%d.%m.%Y}".format(datetime.date.today())
    logger.info("Sending message ...")
    client.send_message({
        "type": "stream",
        "to": [stream],
        "subject": subject,
        "content": formatted_plan,
    })
    logger.info("Sending message finished.")


def update_database(client: zulip.Client, stream: str):
    """
    Synchronise the database with all users in the Zulip stream.

    :param client: Zulip client
    :param stream: Zulip stream
    """
    subscribers: list[int] = client.get_subscribers(stream=stream)["subscribers"]
    db = TinyDB("database.json")
    # Add new users in Zulip stream to database
    for subscribers_id in subscribers:
        if not db.contains(Query().id == subscribers_id):
            user = client.get_user_by_id(subscribers_id)["user"]
            db.insert({"id": user["user_id"], "name": user["full_name"], "active": False})
    # Remove users who are not in Zulip stream anymore from database
    for user in db:
        user_id_in_db: int = user["id"]
        if user_id_in_db not in subscribers:
            # Edge case, when active user removed, define next user
            if user["active"]:
                set_next_user()
            db.remove(Query().id == user_id_in_db)


def set_first_user():
    """
    Define the first user who should start with kitchen duties.
    """
    db = TinyDB("database.json")
    if not db.all() == []:
        if not db.contains(Query().active == True):
            db.update({"active": True}, doc_ids=[1])


def get_user() -> list:
    """
    Return the next eight users for kitchen duties.

    :return: list of Zulip users
    """
    res = []
    db = TinyDB("database.json")
    current_user = db.get(Query().active == True)
    for i in range(current_user.doc_id, current_user.doc_id + 8):
        # Mod operator starting from 1 and not 0
        mod_doc_id = ((i - 1) % len(db)) + 1
        res.append(db.get(doc_id=mod_doc_id))
    return res


def get_dates() -> list[list]:
    """
    Return the next eight dates for kitchen duties.

    :return: list of dates
    """
    res = []
    cur_date = datetime.date.today()
    for i in range(8):
        cur_week = datetime.date.isocalendar(cur_date).week
        cur_year = datetime.date.isocalendar(cur_date).year
        monday = datetime.date.fromisocalendar(cur_year, cur_week, 1).strftime('%d.%m.%Y')
        friday = datetime.date.fromisocalendar(cur_year, cur_week, 5).strftime('%d.%m.%Y')
        res.append([cur_week, monday, friday])
        cur_date = cur_date + datetime.timedelta(days=7)
    return res


def set_next_user():
    """
    Define the next user for kitchen duties.
    """
    db = TinyDB("database.json")
    current_user = db.get(Query().active == True)
    db.update({"active": False}, doc_ids=[current_user.doc_id])
    mod_doc_id = ((current_user.doc_id - 1) % len(db)) + 1
    db.update({"active": True}, doc_ids=[mod_doc_id])


if __name__ == "__main__":
    main_loop()
