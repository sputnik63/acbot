#!/usr/bin/env python

import argparse
import numpy
import json
import sys
import serial
from irtoy import IrToy


#PULSE=500
#SPACE=1500
#LONGSPACE=3500
#ONE=PULSE,LONGSPACE
#ZERO=PULSE,LONGSPACE
#LONGPULSE=6000
#LONGLONGSPACE=7500
#DEBUG=True

PULSE=490
SPACE=1450
LONGSPACE=3455
ONE=PULSE,LONGSPACE
ZERO=PULSE,LONGSPACE
LONGPULSE=5951
LONGLONGSPACE=7466
DEBUG=True

def getCommandLineArgs():
    parser = argparse.ArgumentParser(description='Test')
    parser.add_argument('-d', '--device', dest='device', action='store',
                    default='/dev/ttyACM0',
                    help='Device a cui inviare i codici IR: deve essere collegato un IRToy con firmware rev. 22 o superiore.')
    parser.add_argument('-i', '--inputfile', dest='inputfile', action='store', required=True,
                    help='Nome del file json con i comandi')
    parser.add_argument('-s', '--status', dest='status', required=True,
                    help='[ON|OFF]')
    parser.add_argument('-f', '--fan', dest='fan', required=False, default="AUTO",
                    help='[AUTO|LOW|HI|MED] (default AUTO)')
    parser.add_argument('-m', '--mode', dest='mode', required=False, default="AUTO",
                    help='[AUTO|FAN|DRY|COOL] (default AUTO)')
    parser.add_argument('-w', '--swing', dest='swing', required=False, default="AUTO",
                    help='[AUTO|STOPPED|SWING] (default AUTO)')
    parser.add_argument('-t', '--temp', dest='temp', required=False, default="0",
                    help='[-6 .. 6 | 18 .. 30 | CONT] (default 0 | 25 secondo il MODE scelto)')

    return parser.parse_args()

def sbitwisenot(s1):
    notval = 255 - int(s1,2)
    return str(bin(notval)[2:].zfill(8))

def createHexSeq(s1, codesToSend):
    if DEBUG:
        print "createHexSeq: " + s1

    for i in s1:
        if DEBUG:
            print "pulse\t",PULSE,formatVal(PULSE)
        for j in formatVal(PULSE):
            codesToSend.append(j)
        if i == '1':
            for j in formatVal(LONGSPACE):
                codesToSend.append(j)
            if DEBUG:
                print "space\t",LONGSPACE,formatVal(LONGSPACE)
        else:
            for j in formatVal(SPACE):
                codesToSend.append(j)
            if DEBUG:
                print "space\t",SPACE,formatVal(SPACE)
    return

def formatVal(val):
    #return format((int(val/21.3333) >> 8 & 0x00FF), 'x'), format((int(val/21.3333) & 0x00FF), 'X')
    return int(val/21.3333) >> 8 & 0x00FF, int(val/21.3333) & 0x00FF

def main():
    args = getCommandLineArgs()
    filename = args.inputfile
    val = [[0,0,0,0,0,0],[0,0,0,0,0,0]]
    sval = ["", ""]

    with open(filename, 'r') as inFile:
        codes = json.load(inFile)
        inFile.close()

    for i in [0,1]:
        for j in [0,len(val)]:
            val[i][j]= int(codes["DEFAULT"][i],2)

    if args.mode == "AUTO":
        if int(args.temp) < -6 or int(args.temp) > 6:
            print "ERR: parametro", args.temp, "non valido\n"
            sys.exit(1)
    else:
        if args.temp == "CONT":
            args.temp = 17
        if int(args.temp) < 17 or int(args.temp) > 30:
            print "ERR: parametro", args.temp, "non valido\n"
            sys.exit(1)

    if args.status not in json.dumps(codes["STATUS"]):
        print "ERR: parametro", args.status, "non valido\n"
        print "Valori previsti: ", json.keys(), "\n"
        sys.exit(1)
    if args.fan not in json.dumps(codes["FAN"]):
        print "ERR: parametro", args.fan, "non valido\n"
        sys.exit(1)
    if args.mode not in json.dumps(codes["MODE"]):
        print "ERR: parametro", args.mode, "non valido\n"
        sys.exit(1)
    if args.swing not in json.dumps(codes["SWING"]):
        print "ERR: parametro", args.swing, "non valido\n"
        sys.exit(1)

    finalSeq = ''
    for i in [0,1]:
        val[i][0] |= int(codes["STATUS"][args.status][i],2)
        val[i][1] |= int(codes["FAN"][args.fan][i],2)
        val[i][2] |= int(codes["MODE"][args.mode][i],2)
        val[i][3] |= int(codes["SWING"][args.swing][i],2)

        if args.mode != 'AUTO':
            sottraendo = 32
        else:
            sottraendo = 8

        tempVal = sottraendo - int(args.temp)
        tempBin = str(bin(tempVal)[2:].zfill(4))
        tempStr = "0000" + tempBin[::-1]

        if i == 1:
            val[i][4] |= int(tempStr,2)
            
        val[i][5] = val[i][0] | val[i][1] | val[i][2] | val[i][3] | val[i][4]
        sval[i] = str(bin(val[i][5])[2:].zfill(8))
        if DEBUG:
            print val[i][5], bin(val[i][5])[2:].zfill(8), sbitwisenot(sval[i])
        finalSeq += sval[i] + sbitwisenot(sval[i])

    finalSeq += "01010100" + "10101011"
    if DEBUG:
        print "space\t1000000"
        print "pulse\t",LONGPULSE, formatVal(LONGPULSE)
        print "space\t",LONGLONGSPACE, formatVal(LONGLONGSPACE)
    codesToSend=[]
    for i in formatVal(LONGPULSE):
         codesToSend.append(i)
    for i in formatVal(LONGLONGSPACE):
         codesToSend.append(i)

    createHexSeq(finalSeq, codesToSend)
    if DEBUG:
        print "pulse\t",PULSE, formatVal(PULSE)
        print "space\t",LONGLONGSPACE, formatVal(LONGLONGSPACE)
        print "pulse\t",PULSE, formatVal(PULSE)
    for i in formatVal(PULSE):
         codesToSend.append(i)
    for i in formatVal(LONGLONGSPACE):
         codesToSend.append(i)
    for i in formatVal(PULSE):
         codesToSend.append(i)
    codesToSend.append(255)
    codesToSend.append(255)
    if DEBUG:
        print "space\t1000000", (255, 255)
    print codesToSend

    device = serial.Serial(args.device)
    toy = IrToy(device)
    toy.transmit(codesToSend)
    print('code length:', len(codesToSend), 'handshake:', toy.handshake, 'bytecount:', toy.byteCount, 'complete:', toy.complete)

    device.close()


if __name__ == "__main__":
    main()
