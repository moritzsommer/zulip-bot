#!/usr/bin/env python3

# Copyright (c) 2023 Moritz Sommer <moritz.sommer@rwth-aachen.de>
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
Zulip bot for sending messages containing kitchen duties to the IAT Zulip chat twice a week.
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
FIRST_DAY = 0
SECOND_DAY = 3
# Zulip UIDs of people to skip when planning the kitchen duty
NO_KITCHEN_DUTIES = [
    17,  # torben 
    31,  # tobias
    54  # moritz
]
DATABASE = "database.json"

TEST = False
TEST_DATABASE = "test_database.json"
TEST_STARTING_DATE = datetime.datetime.strptime("01.01.23 08:00:00", '%d.%m.%y %H:%M:%S')
TEST_WEEKS = 3

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
    update_database(zulip_client, stream_name, DATABASE)
    logger.info("Starting into main loop ...")
    while True:
        try:
            logger.info("Updating database ...")
            set_first_user(DATABASE)
            update_database(zulip_client, stream_name, DATABASE)
            # Calculate time until message and sleep
            sleep_time = calculate_sleep_time(datetime.datetime.now(tz=INFO_TIME.tzinfo), FIRST_DAY, SECOND_DAY)
            logger.info(f"Scheduling next message for {sleep_time}.")
            logarithmic_sleep(sleep_time)
            # Send messages
            send_plan(zulip_client, stream_name, sleep_time, DATABASE)
            # Set next user on Thursday
            if datetime.date.isocalendar(sleep_time)[2] - 1 == SECOND_DAY:
                set_next_user(DATABASE)
            # Prevent fast retriggering
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Exiting ...")
            return
        except Exception as e:
            logger.error("Exception in main loop:", exc_info=e)


def test_main_loop():
    """
    While true loop for testing all functions.
    """
    logger.warning("Running in test mode ...")
    logger.info("Initializing test client ...")
    config_file = os.path.join(os.path.dirname(__file__), "test_config.ini")
    config = configparser.ConfigParser()
    config.read(config_file)
    zulip_client = zulip.Client(config_file=config_file)
    stream_name = config['message']['stream']
    simulated_time = TEST_STARTING_DATE

    logger.info("Initialising test database ...")
    update_database(zulip_client, stream_name, TEST_DATABASE)
    logger.info("Starting into test main loop ...")
    for i in range(TEST_WEEKS * 2):
        try:
            logger.info("Updating test database ...")
            set_first_user(TEST_DATABASE)
            update_database(zulip_client, stream_name, TEST_DATABASE)
            # Calculate time until message and sleep
            sleep_time = calculate_sleep_time(simulated_time, FIRST_DAY, SECOND_DAY)
            logger.info(f"Scheduling next message for {sleep_time}.")
            logger.info("Simulating sleep time ...")
            simulated_time = sleep_time
            # Send messages
            send_plan(zulip_client, stream_name, sleep_time, TEST_DATABASE)
            # Set next user on Thursday
            if datetime.date.isocalendar(sleep_time)[2] - 1 == SECOND_DAY:
                set_next_user(TEST_DATABASE)
            # Prevent fast retriggering
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Exiting ...")
            return
        except Exception as e:
            logger.error("Exception in main loop:", exc_info=e)
    os.remove(TEST_DATABASE)
    logger.warning("Exiting test mode ...")


def calculate_sleep_time(day_init: datetime.datetime, day_a: int, day_b: int) -> datetime.datetime:
    """
    Calculate the waiting time from an initial date to the next of two given days of the week.

    :param day_init: initial date
    :param day_a: weekday one, can be a number 0-6
    :param day_b: weekday two, can be a number 0-6
    """
    res = day_init.replace(hour=INFO_TIME.hour, minute=INFO_TIME.minute, second=INFO_TIME.second,
                           microsecond=INFO_TIME.microsecond)
    day_iso = datetime.date.isocalendar(day_init)[2] - 1
    # Clause decides whether to send the message today or search for closest day to send the message
    if res <= day_init or (day_iso != FIRST_DAY and day_iso != SECOND_DAY):
        res += datetime.timedelta(days=1)
        # Time interval to both dates
        delta_a = datetime.timedelta(days=(day_a - res.weekday()) % 7)
        delta_b = datetime.timedelta(days=(day_b - res.weekday()) % 7)
        # Choose date which is closer
        res += delta_a if delta_a < delta_b else delta_b
    # If the clause was skipped, its before the INFO_TIME at FIRST_DAY or SECOND_DAY
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


def send_plan(client: zulip.Client, stream: str, initial: datetime.date, database: str):
    """
    Format and send the message containing kitchen duties.

    :param client: Zulip client
    :param stream: Zulip stream
    :param initial: initial date to choose one of the two formats for the message
    :param database: database name
    """
    logger.info("Fetching plan data ...")
    users = get_user(database)
    dates = get_dates(initial)
    logger.info("Fetching plan data finished.")
    formatted_plan = (
            "# Küchenplan {:%d.%m.%Y}\n\n"
            "| Mitarbeiter | Woche | Montag | Freitag |\n|---|---|---|---|\n".format(initial)
            + "\n".join(
                "| {} | {} | {} | {} |".format(
                    user["name"],
                    date[0],
                    date[1],
                    date[2])
                for user, date in zip(users, dates))
    )
    formatted_plan = formatted_plan + "\n\n @**" + users[0]["name"] + "** ist diese Woche mit dem Küchendienst dran."

    subject = f"Küchenplan {dates[0][1]} - {dates[0][2]}"
    if datetime.date.isocalendar(initial)[2] - 1 == FIRST_DAY:
        formatted_plan = formatted_plan + "\n\n Küchendienstaufgaben:\n\n* {} \n* {} \n* {} \n* {} \n* {}".format(
            "Getränke im Kühlschrank nachfüllen (mindestens 50% Wasser, Rest Club Mate und Cola)",
            "Leergut ins Archiv bringen und leere Kästen in die Küche stellen",
            "Wenn Getränke sich dem Ende neigen, Justin zwecks Bestellung Bescheid geben",
            "Wenn Spülmaschine voll, starten und ausräumen (spätestens Freitag, auch wenn nicht voll)",
            "Handtücher auswechseln, benutzte Handtücher bei Martina abgeben")

        logger.info("Sending message ...")
        client.send_message({
            "type": "stream",
            "to": [stream],
            "topic": subject,
            "content": formatted_plan,
        })
        logger.info("Sending message finished.")
    elif datetime.date.isocalendar(initial)[2] - 1 == SECOND_DAY:
        checklist = "/poll Küchendienstaufgaben" \
                    "\n Getränke im Kühlschrank nachfüllen (mindestens 50% Wasser, Rest Club Mate und Cola)" \
                    "\n Leergut ins Archiv bringen und leere Kästen in die Küche stellen" \
                    "\n Wenn Getränke sich dem Ende neigen, Justin zwecks Bestellung Bescheid geben" \
                    "\n Wenn Spülmaschine voll, starten und ausräumen (spätestens Freitag, auch wenn nicht voll)" \
                    "\n Handtücher auswechseln, benutzte Handtücher bei Martina abgeben"

        logger.info("Sending messages ...")
        client.send_message({
            "type": "stream",
            "to": [stream],
            "topic": subject,
            "content": formatted_plan,
        })
        # Sleep to prevent second message from not being sent
        time.sleep(1)
        client.send_message({
            "type": "stream",
            "to": [stream],
            "topic": subject,
            "content": checklist,
        })
        logger.info("Sending messages finished.")


def update_database(client: zulip.Client, stream: str, database: str):
    """
    Synchronise the database with all users in the Zulip stream.

    :param client: Zulip client
    :param stream: Zulip stream
    :param database: database name
    """
    subscribers: list[int] = client.get_subscribers(stream=stream)["subscribers"]
    db = TinyDB(database)
    # Add new users in Zulip stream to database, ignore bots
    for subscribers_id in subscribers:
        if (not client.get_user_by_id(subscribers_id)["user"]["is_bot"]) and (subscribers_id not in NO_KITCHEN_DUTIES):
            if not db.contains(Query().id == subscribers_id):
                user = client.get_user_by_id(subscribers_id)["user"]
                order = 1
                list_all = db.all()
                if len(list_all) == 0:
                    pass
                else:
                    # Get order of the latest added user and add one
                    order = db.get(doc_id=db.all()[-1].doc_id)["order"] + 1
                db.insert({"id": user["user_id"], "name": user["full_name"], "order": order, "active": False})
    # Remove users who are not in Zulip stream anymore from database
    for user in db:
        user_id_in_db: int = user["id"]
        if (user_id_in_db not in subscribers) or (user_id_in_db in NO_KITCHEN_DUTIES):
            # Edge case, when active user removed, define next user
            if user["active"]:
                set_next_user(database)
            update_orders(user_id_in_db, database)


def update_orders(id_remove: int, database: str):
    """
    Remove a user and update all orders.

    :param id_remove: id of user to be removed
    :param database: database name
    """
    db = TinyDB(database)
    order: int = db.get(Query().id == id_remove)["order"]
    dec_order = db.search(Query().order > order)
    db.remove(Query().id == id_remove)
    # This solution is not elegant but rather simple, a doubly linked list will be added in the future
    if dec_order is not None:
        for i in dec_order:
            db.update({"order": i["order"] - 1}, doc_ids=[i.doc_id])


def set_first_user(database: str):
    """
    Define the first user who should start with kitchen duties.

    :param database: database name
    """
    db = TinyDB(database)
    if not db.all() == []:
        if not db.contains(Query().active == True):
            db.update({"active": True}, Query().order == 1)


def get_user(database: str) -> list:
    """
    Return the next eight users for kitchen duties.

    :param database: database name
    :return: list of Zulip users
    """
    res = []
    db = TinyDB(database)
    current_user = db.get(Query().active == True)
    if current_user is not None:
        current_order = current_user["order"]
        for i in range(current_order, current_order + 8):
            # Mod operator starting from 1 and not 0
            mod_order = ((i - 1) % len(db)) + 1
            res.append(db.get(Query().order == mod_order))
    return res


def get_dates(initial: datetime.date) -> list:
    """
    Return the next eight dates for kitchen duties from an initial date.

    :param initial: initial date
    :return: list of dates
    """
    res = []
    for i in range(8):
        cur_week = datetime.date.isocalendar(initial)[1]
        cur_year = datetime.date.isocalendar(initial)[0]
        monday = datetime.datetime.strptime(f"{cur_year}-W{cur_week}-1", "%Y-W%W-%w").strftime('%d.%m.%Y')
        friday = datetime.datetime.strptime(f"{cur_year}-W{cur_week}-5", "%Y-W%W-%w").strftime('%d.%m.%Y')
        res.append([cur_week, monday, friday])
        initial += datetime.timedelta(days=7)
    return res


def set_next_user(database: str):
    """
    Define the next user for kitchen duties.

    :param database: database name
    """
    db = TinyDB(database)
    current_user = db.get(Query().active == True)
    if current_user is not None:
        db.update({"active": False}, doc_ids=[current_user.doc_id])
        # Mod operator starting from 1 and not 0, increasing by one
        mod_order = (((current_user["order"] + 1) - 1) % len(db)) + 1
        db.update({"active": True}, Query().order == mod_order)


if __name__ == "__main__":
    if not TEST:
        main_loop()
    else:
        test_main_loop()
