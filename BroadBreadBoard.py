import os
from fritzing.FritzingParts import FritzingBreadBoard


numPins = 63
pinDist = 0.1	# use 2.54, if you use mm; use 0.1, if you use in(ch)

width = (numPins + 3) * pinDist
height = 27 * pinDist
left = pinDist

ownFolder = os.path.dirname(os.path.abspath(__file__))
fileNameRoot = 'BroadBreadBoard'

if not os.path.isdir(ownFolder + '/generated'):
	os.mkdir(ownFolder + '/generated')

outFolder = ownFolder + '/generated/' + fileNameRoot

mainSvgName = fileNameRoot + 'Main.svg'
iconSvgName = fileNameRoot + 'Icon.svg'
fzpFileName = fileNameRoot + '.fzp'
fzpzFileName = fileNameRoot + '.fzpz'

board = FritzingBreadBoard ('in', outFolder, width, height, numPins, pinDist)

y = pinDist
y = board.add2OuterRows('ZY', left, y)
y = board.addInnerRows('JIHGF', left, y, True, True)
y = board.add2OuterRows('XW', left, y)
y = board.addInnerRows('EDCBA', left, y, True, True)
board.add2OuterRows('VU', left, y)

board.writeSvg(mainSvgName)

# create the fzp file
board.m_busGroups = [['A', 'B', 'C', 'D', 'E'], ['F', 'G', 'H', 'I', 'J']]
meta = {
	'version': 1,
	'author': 'Richard',
	'title': 'My broad breadboard',
	'date': '2023-02-16',
	'label': 'Breadboard',
	'taxonomy': 'prototyping.breadboard.breadboard.breadboard0',
	'description': 'a broad breadboard from 2 normal ones, suitable for esp32'
}
tags = ['breadboard']
properties = [['family', 'Breadboard'], ['size', 'broad']]
viewFiles = ['icon/' + iconSvgName, 'breadboard/' + mainSvgName]
board.createFzp(fileNameRoot + 'ModuleID', '0.12.34', meta, tags, properties, viewFiles)
board.writeFzp(fzpFileName)

board.createIconSvg(iconSvgName, '--' + str(numPins) + '--')

board.writeFzpz(fzpzFileName)
