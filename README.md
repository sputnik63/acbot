# acbot
Use a Telegram bot to control your air conditioner using different devices (PC, Raspberry, IrToy, Lirc)

## Description
**__ACBot__** is a simple Telegram bot that allows to switch ON/OFF an air conditioner using the following combinations of devices:
* an [IrToy v2](http://dangerousprototypes.com/docs/USB_IR_Toy_v2) connected to a PC USB port
* an IrToy v2  connected to a Raspberry Pi USB port
* a simple infrared LED connected to a GPIO of a Raspberry Pi (it needs [pigpio library](http://abyz.me.uk/rpi/pigpio/) or [Lirc](http://www.lirc.org/))
* a simple infrared LED connected to a pin of [Arietta G25](https://www.acmesystems.it/arietta) (it needs [Lirc](http://www.lirc.org/))

All has been tested using both Python 2 and 3 on a Linux PC, on Raspberry Pi and on Arietta G25, all Linux based systems :penguin: 
I'm confident that all can work also on Windows systems.
The only (at the moment) infrared remote control decoded in **./codes/** directory is the Mitsubishi **RKS502A502A** used for air conditioners models SRK 258 CENF-R, SRK 288 CENF-R, SRK 408 CENF-R
It uses a sligth variation of infrared **__NEC protocol__** as I will describe better somewhere in the internet (coming soon).
By the way, using Lirc, **__you can drive any remote control you have__**. See [Configuration file](Readme.md/###Configuration-file) section below.
Since this is a Free Software project it's easy to modify it as you like and need. I'd like ACBot to be a unique project configurable according the needs of the users instead to have one project per infrared remote controls vendor.

## Getting Started

Just save ACBot files into a directory and edit the correct settings in **acbot.conf** file. Then run the Telegram bot typing:
```
python acbot.py
```

### Prerequisites

Some Python modules needs to be installed to run ACBot: **pyserial**, **ConfigParser**, **python-telegram-bot**. You can easily install all them using pip:
```
pip install pyserial
pip install configparser
pip install python-telegram-bot --upgrade
```
Depending on what you will use to send the infrared signal, some more modules are needed:
* if you send ir signal using a GPIO pin on Raspberry Pi, you need **[pigpio Python wrapper](http://abyz.me.uk/rpi/pigpio/python.html)**
You can see [here](http://abyz.me.uk/rpi/pigpio/download.html) how to install it. If you are using Raspbian, an easy way is
    ```
    sudo apt-get update
    sudo apt-get install pigpio python-pigpio python3-pigpio
    ```
* if you use IrToy you need Chris LeBlanc's **[PyIrToy module](https://github.com/crleblanc/PyIrToy)** To install it you can follow the instructions on its GitHub project or you can simply put the [irtoy.py](https://github.com/crleblanc/PyIrToy/blob/master/irtoy.py) file in the same directory where you saved acbot.py and the other files of this project. 

If you use Lirc on Raspberry you need to install it correctly following [this instructions by Alex Bain](http://alexba.in/blog/2013/01/06/setting-up-lirc-on-the-raspberrypi/).
To use Lirc on Arietta G25 you can follow the same guidelines, but you also need to build the related [lirc_sam.ko module](https://github.com/yuhp/lirc_sam).

## Installing
Copy the files of ACBot into a directory or, better, clone the project.
In order to have a Telegram bot working, you must [create it](https://core.telegram.org/bots#3-how-do-i-create-a-bot) and copy the token assigned to you by BotFather into the ```[common]``` section of the **acbot.conf** file as in theis example:
```
[common]
token_string=123456789:EtcetaeraEtcetaera
```
Then check the other sections of the configuration file to best fit your needs.
Each section is well described in the file. Then run:
```
python acbot.py
```
The Telegram bot will start: type ```/start``` in the bot chat and ... enjoy. Other commands managed: ```/menu``` and ```/stop``` (there is a known bug for this. See below)
The keyboards used in the bot are quite user friendly and easy to understand.
By default they reproduce all the settings present on the RKS502A502A remote control but using Lirc with a GENERIC remote control you can have a simpler keyboard. See [section about Lirc](Readme.md/#**Section-```[lirc]```**) in configuration file 

### Configuration file
**Section ```[host]```**
The keyword ```type``` has admitted values ```pc```, ```raspberry```, ```arietta``` depending if you Telegram bot is running on you PC, on a Raspberry or on Arietta G25

**Section ```[interface]```**
Admitted values: ```irtoy```, ```gpio```, ```lirc``` according the devices you use to send infrared signal

**Section ```[irtoy]```**
Used only if you set ```type=irtoy``` in ```[interface]``` section, the key ```port``` must be equal to the serial port used. Default on Linux based systems is ```/dev/ttyACM0```. On Windows systems it should be COM1 but I never tried. Plese let me know.

**Section ```[lirc]```**
If you use Lirc you must set the key ```remotename``` to the same remote __**name**__ value you configured in your lirc configuration file.
If you don't have the RKS502A502A remote control you can use whatever remote control you have, simply setting ```remotename=GENERIC``` in this section.
In this way the bot will show only a simple keyboard to switch ON or OFF the air conditioner and to schedule the switching. Moreover it will simply issue the commands ```irsed SEND_ONCE GENERIC ON``` or ```irsed SEND_ONCE GENERIC OFF```
In order to achieve this goal you must only have a ```name GENERIC``` and the ```ON``` and ```OFF``` codes in your **lirc configuration file**

**Section ```[signal]```**
It's used only if you set ```type=gpio``` in ```[interface]``` section.
Here is the description of the signal: the durations of pulse and space in microseconds, the value of the frequency of the carrier in Hz, the file name in the ***./codes*** directory where the infrared signal decodification is stored.

**Section ```[common]```**
Here you can set the bot token, the debug level, the trace destination (on file and/or standard output).
If the ```test=true``` key is set, no real device will be used and you can easily test the bot.

## Deployment
To avoid the .pyc files, you can set the environment variable ```PYTHONDONTWRITEBYTECODE``` to a non empty string:
```
export PYTHONDONTWRITEBYTECODE=true
```
Use translations setting the ``LANGUAGE`` environment variable to your language (if available) e.g.
```
export LANGUAGE=it_IT
```

## Test
In **test** directory there are files to send infrared signal using IrToy or pigpio by command line but without using the Telegram bot.

## ToDo and known issues
- [ ] Extract hardcoded parts of any particular remote control from acbot.py
- [ ] After issue /stop the bot exit definitely and it does not restart sending /start

## Contributing
Please feel free to contribute to the project with new infrared codes or devices or translating the strings in other languages.
I've no other available air conditioners :smile: and I'd like to improve the ACBot code to be more "flexible" without any dependency from a particular remote control in the code. Actually some little part of the RKS502A502A are hardcoded in acbot.py. Only using Lirc you can be almost completely remote control independent
I'd like to receive feedbacks and contribution about the use of ACBot on Windows environments.
I beg pardon to all Python gurus for my bad Python: feel free to improve source code according the "pythonic way", particularly the way to "import" modules depending on which device is used, to avoid to the users to import useless modules.

## License
This project is licensed under the GNU General Public License v2.0 License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments
* Thanks to Chris LeBlanc for its work on [HackPump](https://github.com/crleblanc/hackPump) and [PyIrToy](https://github.com/crleblanc/PyIrToy) that heavily inspired me
