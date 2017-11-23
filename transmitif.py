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

import json
import serial
from   serial.serialutil import SerialException
import subprocess
import logging


# config the logger
logger = logging.getLogger('acbot_logger')


class TransmissionException(Exception):
    """
    Exception class
    """
    pass


class Transmitter(object):
    """
    Generic Transmitter class with methods to build the infrared signal
    """
    def __init__(self, cfg):
        """
        Initialize the pulse and space durations
        """
        #read the config file
        self.is_test = cfg.getboolean('common', 'test')
        self.interface=cfg.get('interface','type')
        self.codes = []
        self.PULSE=cfg.getint('signal','pulse')
        self.SPACE=cfg.getint('signal','space')
        self.SHORTSPACE=cfg.getint('signal','shortspace')
        self.LONGSPACE=cfg.getint('signal','longspace')
        self.LONGPULSE=cfg.getint('signal','longpulse')
        self.LONGLONGSPACE=cfg.getint('signal','longlongspace')
        # read the json file with the IR codes
        inputfile="./codes/" + cfg.get('signal','codes_file')
        with open(inputfile, 'r') as inFile:
            self.codes = json.load(inFile)
            inFile.close()


    def sbitwisenot(self, s1):
        """
        Bitwise NOT or complement
        """
        notval = 255 - int(s1,2)
        return str(bin(notval)[2:].zfill(8))


    def formatVal(self, val):
        """
        Format the value to be sent in hex format used by IrToy only
        """
        #return format((int(val/21.3333) >> 8 & 0x00FF), 'x'), format((int(val/21.3333) & 0x00FF), 'X')
        return int(val/21.3333) >> 8 & 0x00FF, int(val/21.3333) & 0x00FF


    def createHexSeq(self, s1, codesToSend):
        """
        Create the hex sequence of values used by IrToy only
        """
        for i in s1:
            logger.debug("pulse\t%3d %s" % (self.PULSE, self.formatVal(self.PULSE)))
            for j in self.formatVal(self.PULSE):
                codesToSend.append(j)
            if i == '1':
                for j in self.formatVal(self.LONGSPACE):
                    codesToSend.append(j)
                logger.debug("space\t%3d %s" % (self.LONGSPACE, self.formatVal(self.LONGSPACE)))
            else:
                for j in self.formatVal(self.SPACE):
                    codesToSend.append(j)
                logger.debug("space\t%3d %s" % (self.SPACE, self.formatVal(self.SPACE)))
        return


    def createBinarySeq(self, status, fan, mode, swing, temp):
        """
        Create the binary string corresponding to the parameters
        set on the remote control
        """
        tempStr = str(temp)
        val = [[0,0,0,0,0,0],[0,0,0,0,0,0]]
        sval = ["", ""]

        for i in [0,1]:
            for j in [0,len(val)]:
                val[i][j]= int(self.codes["DEFAULT"][i],2)

        if mode == "AUTO":
            if int(temp) < -6 or int(temp) > 6:
                logger.error(temp + " invalid parameter\n")
                return
        else:
            if temp == "CONT":
                temp = 17
            if int(temp) < 17 or int(temp) > 30:
                logger.error(temp + " invalid parameter\n")
                return

        if status not in self.codes["STATUS"]:
            logger.error(status + " invalid parameter\n")
            return
        if fan not in self.codes["FAN"]:
            logger.error(fan + " invalid parameter\n")
            return
        if mode not in self.codes["MODE"]:
            logger.error(mode + " invalid parameter\n")
            return
        if swing not in self.codes["SWING"]:
            logger.error(swing + " invalid parameter\n")
            return

        finalSeq = ''
        for i in [0,1]:
            val[i][0] |= int(self.codes["STATUS"][status][i],2)
            val[i][1] |= int(self.codes["FAN"][fan][i],2)
            val[i][2] |= int(self.codes["MODE"][mode][i],2)
            val[i][3] |= int(self.codes["SWING"][swing][i],2)

            if mode != 'AUTO':
                startTempVal = 32
            else:
                startTempVal = 8

            tempVal = startTempVal - int(temp)
            tempBin = str(bin(tempVal)[2:].zfill(4))
            tempStr = "0000" + tempBin[::-1]

            if i == 1:
                val[i][4] |= int(tempStr,2)

            val[i][5] = val[i][0] | val[i][1] | val[i][2] | val[i][3] | val[i][4]
            sval[i] = str(bin(val[i][5])[2:].zfill(8))
            finalSeq += sval[i] + self.sbitwisenot(sval[i])

        # set the last two fixed bytes
        finalSeq += "01010100" + "10101011"
        return finalSeq


class IRTOY(Transmitter):
    """
    Transmitter class to be used with IrToy device
    """
    global IrToy
    global serial

    def __init__(self, cfg):
        Transmitter.__init__(self, cfg)

        self.serialport = cfg.get('irtoy','port')
        try:
            if self.is_test:
                pass
            else:
                s = serial.Serial(self.serialport)
                s.close()
        except (OSError, SerialException):
            msg = "Port %s not available" % (self.serialport)
            logger.error(msg)
            raise TransmissionException(msg)


    def send_code(self, codesToSend):
        """
        Send the codes to the device
        """
        try:
            if (self.interface == 'irtoy'):
                from irtoy import IrToy
            device = serial.Serial(self.serialport)
            toy = IrToy(device)
            toy.transmit(codesToSend)
            print(len(codesToSend))
            print(toy.handshake)
            print(toy.byteCount)
            print(toy.complete)
            msg = "code length:%d\nhandshake:%s\nbytecount:%d\ncomplete:%s" % (len(codesToSend), toy.handshake, toy.byteCount, toy.complete)
            logger.debug(msg)
            device.close()
        except SerialException:
            msg = "Device not found"
            logger.error(msg)
            raise TransmissionException(msg)


    def activate(self, status, fan, mode, swing, temp):
        """
        Create the command sequence and send it to the device
        """

        # first generate the binary values
        binarySeq = self.createBinarySeq(status, fan, mode, swing, temp)
        logger.debug("Payload: " + binarySeq)
        logger.debug("pulse\t%3d %s" % (self.LONGPULSE, self.formatVal(self.LONGPULSE)))
        logger.debug("space\t%3d %s" % (self.LONGLONGSPACE, self.formatVal(self.LONGLONGSPACE)))
        codesToSend=[]
        for i in self.formatVal(self.LONGPULSE):
            codesToSend.append(i)
        for i in self.formatVal(self.LONGLONGSPACE):
            codesToSend.append(i)

        # then calculate hex values to send to IrToy
        self.createHexSeq(binarySeq, codesToSend)
        logger.debug("pulse\t%3d %s" % (self.PULSE, self.formatVal(self.PULSE)))
        logger.debug("space\t%3d %s" % (self.LONGLONGSPACE, self.formatVal(self.LONGLONGSPACE)))
        logger.debug("pulse\t%3d %s" % (self.PULSE, self.formatVal(self.PULSE)))
        for i in self.formatVal(self.PULSE):
            codesToSend.append(i)
        for i in self.formatVal(self.LONGLONGSPACE):
            codesToSend.append(i)
        for i in self.formatVal(self.PULSE):
            codesToSend.append(i)
        # NOTE: the following couple of 255 should be sent
        # in the protocol but sometimes it locks the IrToy
        #codesToSend.append(255)
        #codesToSend.append(255)
        #logger.debug("space\t1000000 (255, 255)")
        logger.debug("Hex sequence:" + ', '.join(str(x) for x in codesToSend))

        try:
            if self.is_test:
                logger.info("Sending codes to serial port")
            else:
                # send codes to the device
                self.send_code(codesToSend)
        except SerialException:
            logger.error("Transmission failed")
            raise SerialException("Transmission failed")

    def stop(self):
        """
        Stop the device
        """
        pass


class RASPI_GPIO(Transmitter):
    """
    Class to manage IR signal through gpio using pigpio library on the Raspberry Pi
    """
    def __init__(self, cfg):
        """
        Initialises an IR tx on a Pi's gpio with a carrier of carrier_hz.
        """
        Transmitter.__init__(self, cfg)

        if (self.interface == 'gpio'):
            import pigpio

        self.pigpio = pigpio
        self.pi = pigpio.pi()
        self.gpio = cfg.getint('gpio','pin')
        self.pi.set_mode(self.gpio, pigpio.OUTPUT)
        self.carrier_hz = cfg.getint('signal','freq')
        self.micros = int(1000000 / self.carrier_hz)
        self.on_mics = int(self.micros / 2)
        self.off_mics = int(self.micros - self.on_mics)
        self.dutycycle = 50
        self.wf = []
        self.wid = -1

    def clear_code(self):
        """
        Clear the pigpio waveform
        """
        self.wf = []
        if self.wid >= 0:
            self.pi.wave_delete(self.wid)

    def send_code(self):
        """
        Send the generated wave to pigpio
        """
        pulses = self.pi.wave_add_generic(self.wf)
        self.wid = self.pi.wave_create()
        if self.wid >= 0:
            self.pi.wave_send_once(self.wid)
            while self.pi.wave_tx_busy():
                pass

    def add_to_code(self, on, off):
        """
        Add on/off cycles on carrier
        """
        # add on cycles of carrier
        for x in range(on):
            self.wf.append(self.pigpio.pulse(1<<self.gpio, 0, self.on_mics))
            self.wf.append(self.pigpio.pulse(0, 1<<self.gpio, self.off_mics))

        # add off cycles of no carrier
        self.wf.append(self.pigpio.pulse(0, 0, off * self.micros))

    def create_code_sequence(self, binarySeq):
        """
        Generate the code sequence according the binary values
        """
        self.clear_code()

        freq = self.carrier_hz
        self.add_to_code(int(self.LONGPULSE * freq / 1000000), int(self.LONGLONGSPACE * freq / 1000000))
        for bit in binarySeq:
            if (bit == '0'):
                self.add_to_code(int(self.PULSE * freq / 1000000), int(self.SPACE * freq / 1000000))  # 0
            else:
                self.add_to_code(int(self.PULSE * freq / 1000000), int(self.LONGSPACE * freq / 1000000)) # 1

        self.add_to_code(int(self.PULSE * freq / 1000000), int(self.LONGLONGSPACE * freq / 1000000))
        self.add_to_code(int(self.PULSE * freq / 1000000), int(self.SHORTSPACE * freq / 1000000))


    def activate(self, status, fan, mode, swing, temp):
        """
        Create the command sequence and send it to the device
        """
        binarySeq = self.createBinarySeq(status, fan, mode, swing, temp)
        logger.debug("Payload: " + binarySeq)

        # use pigpio
        self.pi.set_PWM_dutycycle(self.gpio, 128) #50%
        self.create_code_sequence(binarySeq)
        self.send_code()
        self.pi.set_PWM_dutycycle(self.gpio, 0)


    def stop(self):
        """
        Reset pigpio
        """
        self.pi.stop()


class LIRC(Transmitter):
    """
    Class to manage IR signal through gpio using Lirc
    """
    def __init__(self, cfg):
        Transmitter.__init__(self, cfg)
        self.remotename = cfg.get('lirc','remotename')


    def activate(self, status, fan, mode, swing, temp):
        """
        Create the command sequence and send it to the device
        """

        # use Lirc
        seq = [status, fan, mode, swing, str(temp)]
        if (self.remotename != "GENERIC"):
            cmd = "_".join( seq )
        else:
            cmd = status
        msg = "lirc command: \"irsend SEND_ONCE %s %s\"" % (self.remotename, cmd)
        logger.info(msg)
        if self.is_test:
            ret = 0
        else:
            ret = subprocess.call(["irsend", "SEND_ONCE", self.remotename, cmd])
        if ret != 0:
            logger.error("lirc transmission error")
            raise TransmissionException("ERROR: lirc transmission error")


    def stop(self):
        pass

