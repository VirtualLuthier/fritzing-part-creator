import os
from fritzing.FritzingParts import FritzingBreadBoard


numPins = 63
pinDist = 9.0	# 7.2
centerDist = 7 * pinDist
width = (numPins + 3) * pinDist
height = 21 * pinDist + centerDist
left = pinDist

ownFolder = os.path.dirname(os.path.abspath(__file__))
fileNameRoot = 'BroadBreadBoard'
outFolder = ownFolder + '/' + fileNameRoot

mainSvgName = fileNameRoot + 'Main.svg'
iconSvgName = fileNameRoot + 'Icon.svg'
fzpFileName = fileNameRoot + '.fzp'


board = FritzingBreadBoard (outFolder, width, height, numPins, pinDist)

electrodes = []
numberingHeights = []

y = pinDist

electrodes.append([y, '#0000ff'])

y += pinDist

for name in 'ZY':
	board.addOuterRow(name, left,  y)
	y += pinDist

electrodes.append([y, '#ff0000'])

numberingHeights.append(y + pinDist)
y += 2 * pinDist

for name in 'JIHGF':
	board.addInnerRow(name, left,  y)
	y += pinDist
numberingHeights.append(y)

y += centerDist

for name in 'EDCBA':
	board.addInnerRow(name, left, y)
	y += pinDist

numberingHeights.append(y)

y += pinDist

electrodes.append([y, '#0000ff'])

y += pinDist

for name in 'XW':
	board.addOuterRow(name, left,  y)
	y += pinDist

electrodes.append([y, '#ff0000'])

board.m_electrodes = electrodes
board.m_numberingHeights = numberingHeights


#ownSvgFileName = 'testBroadBreadboard.svg'
#fName = ownFolder + '/' + ownSvgFileName

board.writeSvg(mainSvgName)

board.m_busGroups = [['A', 'B', 'C', 'D', 'E'], ['F', 'G', 'H', 'I', 'J']]
fName = '/testBroadBreadboard.fzp.xml'
meta = {
	'version': 1,
	'author': 'Rüchörd',
	'title': 'My broad breadboard',
	'date': '2023-02-16',
	'label': 'Breadboard',
	'taxonomy': 'prototyping.breadboard.breadboard.breadboard0',
	'description': 'a broad breadboard from 2 slim ones'
}
tags = ['breadboard']
properties = [['family', 'Breadboard'], ['size', 'broad']]
viewFiles = ['icon/' + iconSvgName, 'breadboard/' + mainSvgName]
board.createFzp('BreadBoardBroadModuleID', '0.12.34', meta, tags, properties, viewFiles)
board.writeFzp(fzpFileName)

board.createIconSvg(iconSvgName)
