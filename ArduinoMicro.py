import os
from fritzing.FritzingParts import FritzingMicroProcessor, MicroPin


#numPins = 18
pinDist = 2.54	# use 2.54, if you use mm; use 0.1, if you use in(ch)

width = 48
height = 18
left = pinDist

ownFolder = os.path.dirname(os.path.abspath(__file__))
fileNameRoot = 'ArduinoMicro'

if not os.path.isdir(ownFolder + '/generated'):
	os.mkdir(ownFolder + '/generated')

outFolder = ownFolder + '/generated/' + fileNameRoot

mainSvgName = fileNameRoot + 'Main.svg'
schemSvgName = fileNameRoot + 'Schem.svg'
iconSvgName = fileNameRoot + 'Icon.svg'
pcbSvgName = fileNameRoot + 'Pcb.svg'
fzpFileName = fileNameRoot + '.fzp'
fzpzFileName = fileNameRoot + '.fzpz'

miPro = FritzingMicroProcessor ('mm', outFolder, width, height, pinDist)

lowerPins = [
	MicroPin('~D13', 'r2'),
	MicroPin('+3V3', 't2'),
	MicroPin('AREF', 'l3'),
	MicroPin('A0-D18', 'l5'),
	MicroPin('A1-D19', 'l6'),
	MicroPin('A2-D20', 'l7'),
	MicroPin('A3-D21', 'l8'),
	MicroPin('A4-D22', 'l9'),
	MicroPin('A5-D23', 'l10'),
	MicroPin(None),
	MicroPin(None),
	MicroPin('+5V', 't4'),
	MicroPin('RESET', 'l2'),
	MicroPin('GND', 'b5'),
	MicroPin('VIN', 't6'),
	MicroPin('D14-CIPO', 'r19'),					# CIPO = MISO
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
	MicroPin('GND-2'),
	MicroPin('RESET-2'),
	MicroPin('D0-RX', 'r15'),
	MicroPin('D1-TX', 'r14'),
	MicroPin('D17-SS', 'r21'),
	MicroPin('D16-COPI', 'r18'),					# COPI = MOSI
]

fontSize = 4
miPro.addText(miPro.m_texts, 'ArduinoMicro', width/2, height*0.5 + fontSize*0.3, fontSize=fontSize)
miPro.addRect(miPro.m_graphics, 0, 6, 5, 5, '#eeeeee')
fontSize = 1
miPro.addText(miPro.m_graphics, 'USB', 3, height*0.5 + fontSize*0.3, fontSize=fontSize)

miPro.addPinRow('upper', pinDist*1.5, pinDist*0.5, pinDist, 0, upperPins)
miPro.addPinRow('lower', pinDist*1.5, pinDist*6.5, pinDist, 0, lowerPins)

miPro.writeSvg(mainSvgName)

miPro.writeSchematicSvg(schemSvgName, 8, 23, 8)

miPro.writePcbSvg(pcbSvgName)

iconRoot = miPro.createIconRootNode()
fontSize = 4
miPro.addText(iconRoot, 'ArduinoMicro', 16, 16 + fontSize*0.3, fontSize=fontSize)
miPro.writeOutIconFile(iconRoot, iconSvgName)

# create the fzp file
# board.m_busGroups = [['A', 'B', 'C', 'D', 'E'], ['F', 'G', 'H', 'I', 'J']]
# meta = {
# 	'version': 1,
# 	'author': 'Richard',
# 	'title': 'My broad breadboard',
# 	'date': '2023-02-16',
# 	'label': 'Breadboard',
# 	'taxonomy': 'prototyping.breadboard.breadboard.breadboard0',
# 	'description': 'a broad breadboard from 2 normal ones, suitable for esp32'
# }
# tags = ['breadboard']
# properties = [['family', 'Breadboard'], ['size', 'broad']]
# viewFiles = ['icon/' + iconSvgName, 'breadboard/' + mainSvgName]
# board.createFzp(fileNameRoot + 'ModuleID', '0.12.34', meta, tags, properties, viewFiles)
# board.writeFzp(fzpFileName)

# board.createIconSvg(iconSvgName, '--' + str(numPins) + '--')

# board.writeFzpz(fzpzFileName)
