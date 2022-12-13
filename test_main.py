import datetime

from main import calculate_sleep_time

MON = datetime.datetime(hour=9, day=3, month=1, year=2022)
TUE = datetime.datetime(hour=9, day=4, month=1, year=2022)
WED = datetime.datetime(hour=9, day=5, month=1, year=2022)
THU = datetime.datetime(hour=9, day=6, month=1, year=2022)
FRI = datetime.datetime(hour=9, day=7, month=1, year=2022)
SAT = datetime.datetime(hour=9, day=8, month=1, year=2022)
SUN = datetime.datetime(hour=9, day=9, month=1, year=2022)

FRI_BEFORE = datetime.datetime(hour=9, day=30, month=12, year=2022)
SAT_BEFORE = datetime.datetime(hour=9, day=31, month=12, year=2022)
SUN_NEXT = datetime.datetime(hour=9, day=1, month=1, year=2023)
MON_NEXT = datetime.datetime(hour=9, day=2, month=1, year=2023)


def test_1():
    assert calculate_sleep_time(MON, 1, 2) == datetime.datetime(minute=30, hour=8, day=4, month=1, year=2022)


def test_2():
    assert calculate_sleep_time(SUN, 5, 6) == datetime.datetime(minute=30, hour=8, day=15, month=1, year=2022)


def test_3():
    assert calculate_sleep_time(FRI, 4, 6) == datetime.datetime(minute=30, hour=8, day=9, month=1, year=2022)


def test_4():
    assert calculate_sleep_time(FRI_BEFORE, 0, 2) == datetime.datetime(minute=30, hour=8, day=2, month=1, year=2023)


def test_5():
    assert calculate_sleep_time(SAT_BEFORE, 6, 1) == datetime.datetime(minute=30, hour=8, day=1, month=1, year=2023)
