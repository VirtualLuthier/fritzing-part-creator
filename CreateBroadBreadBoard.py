'''
	This file tries to create a fritzing part representing an breadboard which 
	is combined by 2 normal breadboards. Such a breadboard is needed e.g.
	for a ESP32 board, which needs more space between the both row clusters

	It does it by using the functionality inside of fritzing.FritzingParts
	It creates the necessary .svg files, the .fzp file and the combination of those,
	the .fzpz file
'''


import os
from fritzing.FritzingParts import FritzingBreadBoard

# folder handling

ownFolder = os.path.dirname(os.path.abspath(__file__))

if not os.path.isdir(ownFolder + '/generated'):
	os.mkdir(ownFolder + '/generated')

fileNameRoot = 'BroadBreadBoard'		# very important
outFolder = ownFolder + '/generated/' + fileNameRoot
if not os.path.isdir(outFolder):
	os.mkdir(outFolder)


# creating the breadboard

numPins = 63
pinDist = 0.1	# use 2.54, if you use mm; use 0.1, if you use in(ch)

width = (numPins + 3) * pinDist
height = 27 * pinDist
left = pinDist

board = FritzingBreadBoard ('in', outFolder, fileNameRoot, width, height, numPins, pinDist)

y = pinDist
y = board.add2OuterRows('ZY', left, y)
y = board.addInnerRows('JIHGF', left, y, True, True)
y = board.add2OuterRows('XW', left, y)
y = board.addInnerRows('EDCBA', left, y, True, True)
board.add2OuterRows('VU', left, y)

board.writeMainSvg()

board.createIconSvg('--' + str(numPins) + '--')

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
board.createFzp(fileNameRoot + 'ModuleID', '0.12.34', meta, tags, properties)

board.writeFzpz()
