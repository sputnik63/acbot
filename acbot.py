#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#acbot - control your air conditioner (or other IR remote controlled equipment through a Telegram bot
#Copyright (C) 2017 by Francesco Rotondella

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from transmitif import (IRTOY, RASPI_GPIO, LIRC, TransmissionException)

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
import telegram #Wrapper Bot API Telegram

import logging
import logging.handlers as lh
import sys
from datetime import datetime
from datetime import timedelta
from threading import Timer
import re
import gettext
import configparser


STBY_ST     =  0
STARTING_ST =  1
STARTED_ST  =  2
STOPPING_ST =  3
STOPPED_ST  =  4
SCHEDULING_START_ST =  5
SCHEDULING_STOP_ST  =  6
FAN_SETTING_ST   =  7
MODE_SETTING_ST  =  8
SWING_SETTING_ST =  9
TEMP_SETTING_ST  = 10

cmd_status = STBY_ST
fan = 'AUTO'
mode = 'AUTO'
swing = 'AUTO'
temp = 0

status_str = ['STBY_ST','STARTING_ST', 'STARTED_ST','STOPPING_ST',
              'STOPPED_ST','SCHEDULING_START_ST', 'SCHEDULING_STOP_ST',
              'FAN_SETTING_ST','MODE_SETTING_ST','SWING_SETTING_ST',
              'TEMP_SETTING_ST'
             ]

# We use this var to save the last chat id, so we can reply to it
last_chat_id = 0

def start(bot, update):
    bot.sendMessage(update.message.chat_id, _("Hello %s ! I am ACBot") % ( update.message.from_user.first_name))
    main_menu(bot,update)


def stop(bot, update):
    bot.sendMessage(update.message.chat_id, _("See you soon %s ") % ( update.message.from_user.first_name))
    transmitter.stop()
    updater.stop()


def main_menu(bot, update):
    global cmd_status
    cmd_status=STBY_ST
    bot.sendMessage(update.message.chat_id, _("Select a command from below"), reply_markup=menu_keyboard)


def any_message(bot, update):
    # Save last chat_id to use in reply handler
    global last_chat_id

    last_chat_id = update.message.chat_id
    msg = "Unmanaged command\nFrom: %(user)s\nchat_id: %(id)d\nText: %(text)s" % ({
                'user': update.message.from_user,
                'id': update.message.chat_id,
                'text': update.message.text})
    logger.warn(_(msg))
    bot.sendMessage(update.message.chat_id, _(msg))


def echo(bot, update):
    global cmd_status
    global fan
    global mode
    global swing
    global temp

    logger.debug("old command status: " + status_str[cmd_status])
    logger.debug("----> Sender : [" + update.message.from_user.username + "]")
    logger.debug("      Text   : [" + update.message.text + "]")

    if update.message.text:
        if update.message.text=="ON":
            msg = _("Start now or schedule start")
            bot.sendMessage(update.message.chat_id, msg, reply_markup=onoff_keyboard)
            cmd_status=STARTING_ST
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="OFF":
            msg = _("Stop now or schedule stop")
            bot.sendMessage(update.message.chat_id, msg, reply_markup=onoff_keyboard)
            cmd_status=STOPPING_ST
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="SETTINGS":
            reply_markup = telegram.ReplyKeyboardRemove()
            bot.sendMessage(update.message.chat_id, _("Set mode:"), reply_markup=settings_keyboard)
            cmd_status=STBY_ST
            return

        if update.message.text=="NOW":
            reply_markup = telegram.ReplyKeyboardRemove()
            if (cmd_status == STARTING_ST):
                msg = _("Starting now")
                if not IS_TEST:
                    msg = msg + "\nFAN:" + fan + ", MODE: " + mode + "\nSWING: " + swing + ", TEMP: " + str(temp)
                else:
                    msg = msg
                cmd = "ON"
            else:
                msg = _("Stopping now")
                cmd = "OFF"

            cmd_status = STBY_ST
            bot.sendMessage(update.message.chat_id, msg, reply_markup=reply_markup)
            try:
                transmitter.activate(cmd, fan, mode, swing, temp)
            except TransmissionException as e:
                logger.error(e)

            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="SCHEDULE":
            reply_markup = telegram.ReplyKeyboardRemove()
            if (cmd_status == STARTING_ST):
                msg = _("Input start time in format  HH:MM")
                cmd = "ON"
                cmd_status = SCHEDULING_START_ST
            else:
                msg = _("Input stop time in format  HH:MM")
                cmd = "OFF"
                cmd_status = SCHEDULING_STOP_ST

            bot.sendMessage(update.message.chat_id, msg, reply_markup=reply_markup)
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="FAN SPEED":
            bot.sendMessage(update.message.chat_id, _("Set fan speed"), reply_markup=fan_keyboard)
            cmd_status = FAN_SETTING_ST
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="TEMP":
            bot.sendMessage(update.message.chat_id, _("Set temperature"), reply_markup=temp_keyboard)
            cmd_status = TEMP_SETTING_ST
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="MODE":
            bot.sendMessage(update.message.chat_id, _("Set mode"), reply_markup=mode_keyboard)
            cmd_status = MODE_SETTING_ST
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if update.message.text=="SWING":
            reply_markup = telegram.ReplyKeyboardRemove()
            bot.sendMessage(update.message.chat_id, _("Set fan mode"), reply_markup=swing_keyboard)
            cmd_status = SWING_SETTING_ST
            logger.debug("new command status: " + status_str[cmd_status])
            return

        if (cmd_status==SCHEDULING_START_ST or cmd_status==SCHEDULING_STOP_ST):
            now = datetime.now()
            sched_time = update.message.text
            m = re.search('[0-9]{2}:[0-9]{2}', sched_time)
            if m == None:
                bot.sendMessage(update.message.chat_id, _("Wrong format: input time in format HH:MM"))
                logger.debug("new command status: " + status_str[cmd_status])
                return

            sched_time_ary = sched_time.split(":")
            try:
                time_set = datetime(now.year, now.month, now.day, int(sched_time_ary[0]), int(sched_time_ary[1]), 0)
            except ValueError as e:
                msg = _("ERROR: ") + str(e)
                bot.sendMessage(update.message.chat_id, msg)
                logger.error(e)
                return

            elapsedTime = (time_set-now)
            delay = int(elapsedTime.total_seconds())
            if (delay < 0):
                delay += 86400

            if (cmd_status==SCHEDULING_START_ST):
                msg= "STARTING AT: "
                cmd = "ON"
            else:
                msg = "STOPPING AT: "
                cmd = "OFF"

            cmd_status = STBY_ST
            logger.debug(msg + time_set.strftime("%H:%M del %d/%m/%Y"))
            logger.debug("DELAY: " + str(delay))
            schedule_op(delay, cmd, bot, update)

        if update.message.text=="AUTO":
            if cmd_status==FAN_SETTING_ST:
                fan = 'AUTO'
            if cmd_status==MODE_SETTING_ST:
                mode = 'AUTO'
            if cmd_status==SWING_SETTING_ST:
                swing = 'AUTO'
            if cmd_status==TEMP_SETTING_ST:
                temp = 0
            cmd_status = STBY_ST

        if update.message.text=="LOW" or update.message.text=="HI" or update.message.text=="MED":
            fan = update.message.text
            bot.sendMessage(update.message.chat_id, "FAN: " + fan, reply_markup=settings_keyboard)
            cmd_status = STBY_ST

        if update.message.text=="DRY" or update.message.text=="COOL" or update.message.text=="FAN":
            mode = update.message.text
            bot.sendMessage(update.message.chat_id, "MODE: " + mode, reply_markup=settings_keyboard)
            cmd_status = STBY_ST

        if update.message.text=="STOPPED" or update.message.text=="SWING":
            swing = update.message.text
            bot.sendMessage(update.message.chat_id, "SWING: " + swing, reply_markup=settings_keyboard)
            cmd_status = STBY_ST

        if update.message.text=="DEFAULT":
            fan = 'AUTO'
            mode = 'AUTO'
            swing = 'AUTO'
            temp = 0
            msg = "FAN:" + fan + ", MODE: " + mode + "\nSWING: " + swing + ", TEMP: " + str(temp)
            bot.sendMessage(update.message.chat_id, msg, reply_markup=menu_keyboard)
            cmd_status = STBY_ST

        if update.message.text=="+":
            if (temp < 6 or temp < 30):
                temp += 1
            bot.sendMessage(update.message.chat_id, "TEMP: " + str(temp))

        if update.message.text=="-":
            if (temp > -6 or temp > 18):
                temp -= 1
            bot.sendMessage(update.message.chat_id, "TEMP: " + str(temp))

        logger.debug("new command status: " + status_str[cmd_status])


def error_callback(bot, update, error):
    logger.error('Update "%s" caused error "%s"' % (update, error))
    try:
        raise error
    except Unauthorized:
        logger.error("Unauthorized")
    except BadRequest:
        logger.error("BadRequest")
    except TimedOut:
        logger.error("TimedOut")
    except NetworkError:
        logger.error("NetworkError")
    except ChatMigrated:
        logger.error("ChatMigrated")
    except TelegramError:
        logger.error("TelegramError")


def execute_scheduled_op(bot, update, op):
    # here we add 1 second just to round seconds
    msg = op + ": " + (datetime.now()+timedelta(seconds=1)).strftime("%H:%M %d/%m/%Y")
    if (op == "ON"):
        msg = msg + "\nFAN:" + fan + ", MODE:" + mode + "\nSWING:" + swing + ", TEMP:" + str(temp)
    bot.sendMessage(update.message.chat_id, msg)
    try:
        transmitter.activate(op, fan, mode, swing, temp)
    except TransmissionException as e:
        logger.error(e)


def schedule_op(delay, op, bot, update):
    reply_markup = telegram.ReplyKeyboardRemove()
    msg = _("Scheduled ") + op + _(" at ") + (datetime.now() + timedelta(seconds=delay+1)).strftime("%H:%M del %d/%m/%Y")
    bot.sendMessage(update.message.chat_id, msg, reply_markup=reply_markup)
    Timer(delay, execute_scheduled_op, [bot, update, op]).start()


######### Main Program Starts Here

if __name__ == '__main__':
    global update_queue
    global transmitter
    global IS_TEST

    cfg = configparser.RawConfigParser()
    cfg.read("./acbot.conf")
    if (len(cfg.sections()) == 0):
        # Set default values
        cfg.add_section('common')
        cfg.set('common', 'loglev', 'WARN')

    HOST=cfg.get('host','type')
    IF=cfg.get('interface','type')
    IS_TEST=cfg.get('common','test')

    # Enable and config logger
    logger = logging.getLogger('acbot_logger')

    if ('stdout' in cfg.get('common', 'logdest')):
        logging.basicConfig(stream=sys.stdout,
                            filemode='w', level=cfg.get('common', 'loglev'),
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%d/%m/%Y %H:%M:%S')
        #consoleHandler = logging.StreamHandler()
        #logger.addHandler(consoleHandler)

    if ('file' in cfg.get('common', 'logdest')):
        LOG_FILENAME="./acbot.log"
        logging.basicConfig(filename=LOG_FILENAME,
                            filemode='w', level=cfg.get('common', 'loglev'),
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%d/%m/%Y %H:%M:%S')
        handler = lh.RotatingFileHandler(LOG_FILENAME, maxBytes=2000000, backupCount=2)
        logger.addHandler(handler)

    # Enable i18n
    t = gettext.translation('acbot', 'locale', fallback=True)
    _ = t.gettext

    # initialize the bot keyboards
    if (cfg.get('interface', 'type') == "lirc" and cfg.get('lirc', 'remotename') == "GENERIC") :
        menu_keyboard = telegram.ReplyKeyboardMarkup([['ON','OFF','/help']])
    else:
        menu_keyboard = telegram.ReplyKeyboardMarkup([['ON','OFF'],['SETTINGS','/help']])

    menu_keyboard.one_time_keyboard=False
    menu_keyboard.resize_keyboard=True

    onoff_keyboard = telegram.ReplyKeyboardMarkup([['NOW','SCHEDULE','/menu']])
    onoff_keyboard.one_time_keyboard=False
    onoff_keyboard.resize_keyboard=True

    settings_keyboard = telegram.ReplyKeyboardMarkup([['FAN SPEED','TEMP','MODE' ], ['SWING','DEFAULT','/menu']])
    settings_keyboard.one_time_keyboard=False
    settings_keyboard.resize_keyboard=True

    fan_keyboard = telegram.ReplyKeyboardMarkup([['AUTO','LOW'], ['HI','MED'], ['SETTINGS', '/menu']])
    fan_keyboard.one_time_keyboard=False
    fan_keyboard.resize_keyboard=True

    temp_keyboard = telegram.ReplyKeyboardMarkup([['+','-'], ['SETTINGS','/menu']])
    temp_keyboard.one_time_keyboard=False
    temp_keyboard.resize_keyboard=True

    mode_keyboard = telegram.ReplyKeyboardMarkup([['AUTO', 'DRY'], ['COOL','FAN'], ['SETTINGS','/menu']])
    mode_keyboard.one_time_keyboard=False
    mode_keyboard.resize_keyboard=True

    swing_keyboard = telegram.ReplyKeyboardMarkup([['AUTO', 'STOPPED','SWING'], ['SETTINGS','/menu']])
    swing_keyboard.one_time_keyboard=False
    swing_keyboard.resize_keyboard=True

    updater = Updater(cfg.get('common', 'token_string'))

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # handlers to manage commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("menu", main_menu))
    dp.add_handler(CommandHandler("help", main_menu))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # Regex handlers will receive all updates on which their regex matches
    # this should be the last handler
    dp.add_handler(RegexHandler('.*', any_message))

    # manage bot exceptions
    dp.add_error_handler(error_callback)

    # the bot is running on a PC using IrToy as device
    if (HOST == 'pc'):
        # parameters: serial port
        try:
            transmitter = IRTOY(cfg)
        except TransmissionException as e:
            logger.error(e)
            sys.exit(1)

    if (HOST == 'raspberry'):
        # the bot is running on a Raspberry
        if (IF == 'gpio'):
            # pigpio library is used to send IR signal
            # parameters: GPIO number, carrier frequency, LIRC disabled
            transmitter = RASPI_GPIO(cfg)
        if (IF == 'lirc'):
            # lirc is used to send IR signal
            # parameters: GPIO number is configured in Lirc, carrier frequency, LIRC enabled
            transmitter = LIRC(cfg)
        if (IF == 'irtoy'):
            # IrToy is used to send IR signal
            # parameters: serial port
            try:
                transmitter = IRTOY(cfg)
            except TransmissionException as e:
                logger.error(e)
                sys.exit(1)

    if (HOST == 'arietta'):
        # the bot is running on Arietta G25 by Acmesystems
        # parameters: pin kernel id, carrier frequency
        transmitter = LIRC(cfg)

    # Start the Bot
    update_queue = updater.start_polling()

    try:
        # Run the bot until you presses Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT.
        updater.idle()
    except KeyboardInterrupt:
        logger.warn("Exit")
        updater.stop()
        sys.exit(0)

