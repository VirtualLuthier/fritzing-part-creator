# fritzing-part-creator

Contains a python class lib to create 2 types of fritzing parts from scratch:

-Breadboards

-Microprocessors like Arduino

## Motivation
I have seen that it is rather complicated to create a fritzing part. 
Also the programs to create one seem to be currently not completely finished. 
As I am new to fritzing, and I did not find a breadboard, that is suited for an ESP32
board (such breadboard must be broader than a normal one). Technically it must 
be composed from 2 normal breadboards.

I needed also a model of an ArduinoMicro. I found one in fritzing, but it did not connect
to any breadboard.

## Concept
To build a part with this class library you have to write a small python program, using the library.
The library will then create the needed svg, fzp and fzpz files.

I tried to make the calls as simple as possible. For reference you can see the both example programs and their respective fzpz output

-CreateBroadBreadBoard.py

-CreateArduinoMicro.py

The only 2 dependencies are

- a python 3 installation (did not try it with python 2)

- font-family DroidSans is used. It would help, if it is installed on your PC

call: python create....py on the command line and the files are created

## Advantages:

-Simple API

-Very simple svg files

-real coordinates (no scaling or dpi voodoo), for mm or in

-readable pin names

## Restrictions
-currently no support for background images

-currently no support for vertical pin columns

-currently no support for rotated texts


