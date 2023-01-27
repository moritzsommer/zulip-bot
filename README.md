# IAT Kitchen Bot

### General
This is a Zulip bot for sending messages containing kitchen duties to the IAT
(Chair of Information and Automation Systems for Process and Material Technology, RWTH Aachen) Zulip 
chat twice a week.

### Settings
There are 9 variables in ``main.py`` which adapt the functionalities of the bot.

* ``INFO_TIME (datetime.time)``: Specifies the time at which the message should be sent by.


* ``FIRST_DAY (int)``: Specifies the first day of the week at which the message should be sent. Monday is 0 and Sunday is 6.


* ``SECOND_DAY (int)``: Specifies the second day of the week at which the message should be sent. Monday is 0 and Sunday is 6.


* ``NO_KITCHEN_DUTIES ([int])``: Specifies a list containing IDs of users who do not have to do kitchen duties. 


* ``DATABASE (str)``: Specifies the name of the database. 


* ``TEST (bool)``: Specifies whether to run normal mode or test mode. In test mode, the bot sends all messages for the next weeks at once, without waiting for the actual dates.


* ``TEST_DATABASE (str)``: Specifies the name of the test database. It will be deleted automatically.


* ``TEST_STARTING_DATE (datetime.datetime)``: Specifies the day from which on the bot should be tested.


* ``TEST_WEEKS (int)``: Specifies the amount of weeks the bot should send a message for in advance.

### Configuration
In ``config.ini`` and ``test_config.ini``, all information about the bot connection must be specified. This includes the ``key``, ``email`` and ``site`` of the bot. In addition to that, the name of the ``stream`` where the messages should be sent has to be specified. This name should not include special characters like *ä*, *ö*, *ü* and *ß*.

``config.ini`` contains connection information for the normal mode and ``test_config.ini`` for the test mode.
