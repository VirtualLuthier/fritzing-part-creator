
'''
	This file tries to create a fritzing part representing an Arduino Micro according to 
	https://docs.arduino.cc/hardware/micro

	It does it by using the functionality inside of fritzing.FritzingParts
	It creates the necessary .svg files, the .fzp file and the combination of those,
	the .fzpz file.

	I chose ArduinoMIcro, because I could not make the integrated one work on any breadboard.
'''




import os
from fritzing.FritzingParts import FritzingMicroProcessor, MicroPin

# prepare the output folder:

fileNameRoot = 'ArduinoMicro_00'				# very important for all the file names!

ownFolder = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(ownFolder + '/generated'):
	os.mkdir(ownFolder + '/generated')

outFolder = ownFolder + '/generated/' + fileNameRoot

if not os.path.isdir(outFolder):
	os.mkdir(outFolder)

# the board itself:

pinDist = 2.54	# use 2.54, if you use mm; use 0.1, if you use in(ch)
width = 48
height = 18

miPro = FritzingMicroProcessor ('mm', outFolder, fileNameRoot, width, height, pinDist)

lowerPins = [
	MicroPin('~D13', 'r2'),				# r: right on schematic
	MicroPin('+3V3', 't2'),				# t: top on schematic
	MicroPin('AREF', 'l3'),				# l: left on schematic
	MicroPin('A0-D18', 'l5'),
	MicroPin('A1-D19', 'l6'),
	MicroPin('A2-D20', 'l7'),
	MicroPin('A3-D21', 'l8'),
	MicroPin('A4-D22', 'l9'),
	MicroPin('A5-D23', 'l10'),
	MicroPin(None, None),				# not used
	MicroPin(None, None),
	MicroPin('+5V', 't4'),
	MicroPin('RESET', 'l2'),
	MicroPin('GND', 'b5'),				# b: bottom on schematic'
	MicroPin('VIN', 't6'),
	MicroPin('D14-CIPO', 'r19'),		# CIPO = MISO
	MicroPin('D15-SCK', 'r20'),
]

upperPins = [
	MicroPin('D12-A11', 'r3'),
	MicroPin('~D11', 'r4'),
	MicroPin('~D10-A10', 'r5'),
	MicroPin('~D9-A9', 'r6'),
	MicroPin('D8-A8', 'r7'),
	MicroPin('D7', 'r8'),
	MicroPin('~D6-A7', 'r9'),
	MicroPin('~D5', 'r10'),
	MicroPin('D4-A6', 'r11'),
	MicroPin('~D3-SCL', 'r12'),
	MicroPin('D2-SDA', 'r13'),
	MicroPin('GND-2', 'oGND'),			# another GND
	MicroPin('RESET-2', 'oRESET'),		# another RESET
	MicroPin('D0-RX', 'r15'),
	MicroPin('D1-TX', 'r14'),
	MicroPin('D17-SS', 'r21'),
	MicroPin('D16-COPI', 'r18'),		# COPI = MOSI
]

fontSize = 4
miPro.addText(miPro.m_texts, 'ArduinoMicro', width/2, height*0.5 + fontSize*0.3, fontSize=fontSize)

miPro.setMainColors('#000000', '#ffffff')	# optional, as you like (background, foreground)

# the usb connector symbolically
miPro.addRect(miPro.m_graphics, 0, 6, 5, 5, '#999999')
fontSize = 1
miPro.addText(miPro.m_graphics, 'USB', 3, height*0.5 + fontSize*0.3, fontSize=fontSize) # svg parent, text, x, y, fontSize

# the 2 pin rows:
miPro.addPinRow('upper', pinDist*1.5, pinDist*0.5, pinDist, 0, upperPins) # name, left, top, pinDistX, pinDistY, pins
miPro.addPinRow('lower', pinDist*1.5, pinDist*6.5, pinDist, 0, lowerPins)

miPro.writeMainSvg()

miPro.writeSchematicSvg(8, 23, 3)		# width, height, outer - in pin steps

miPro.writePcbSvg()

# create the icon svg file:
iconRoot = miPro.createIconRootNode()
fontSize = 4
miPro.addText(iconRoot, 'ArduinoMicro', 16, 16 + fontSize*0.3, fontSize=fontSize) # svg parent, text, x, y, fontSize
miPro.writeOutIconFile()

# create the fzp file:

meta = {
	'version': 1,
	'author': 'Richard',
	'title': 'Arduino Micro',
	'date': '2023-03-04',
	'label': 'ArduinoMicro',
	'description': 'a simple arduino micro according to https://docs.arduino.cc/hardware/micro'
}
tags = ['ArduinoMicro']
properties = [['family', 'ArduinoMicro'], ['level', 'simple']]

miPro.createFzp(fileNameRoot + 'ModuleID', '0.12.34', meta, tags, properties)

# create the combined .fzpz file:
miPro.writeFzpz()
