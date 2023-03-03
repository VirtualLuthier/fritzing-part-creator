'''
	Can create a fritzing breadboard via api.
	Creates
	- breadboard svg
	- breadboard icon svg
	- breadboard fzp


'''
'''
	For pinouts see e.g. https://docs.arduino.cc/hardware/micro
'''


import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from zipfile import ZipFile, ZIP_DEFLATED



class Location:
	def __init__(self, x, y, name):
		self.m_x = self.round(x)
		self.m_y = self.round(y)
		self.m_name = name


	def dump(self):
		#print(str(round(self.m_x, 3)) + ', ' + str(round(self.m_y, 3)))
		print(str(self.m_x) + ', ' + str(self.m_y))



	def round(self, num):
		return round(num, FritzingPart.s_roundingSize)
	

##########################################################################
##########################################################################


class MicroPin(Location):
	def __init__(self, name, position=None):
		super().__init__(-1, -1, name)
		self.m_schemLoc = None
		self.m_schemPos = None
		if position is not None:
			self.m_schemLoc = position[0]
			numString = position[1:]
			self.m_schemPos = int(numString)



##############################################################
##############################################################

class LocationList:


	def __init__(self, name, x, y, dx, dy, num):
		self.m_name = name
		self.m_x = self.round(x)
		self.m_y = self.round(y)
		self.m_dx = dx
		self.m_dy = dy
		self.m_num = num


	def round(self, num):
		return round(num, FritzingPart.s_roundingSize)


	def getLocations(self):
		ret = []
		curX = self.m_x
		curY = self.m_y
		for ii in range(self.m_num):
			locName = self.m_name + str(ii)
			ret.append(Location(curX, curY, locName))
			curX += self.m_dx
			curY += self.m_dy
		return ret


	def dump(self):
		print(self.m_name)
		for loc in self.getLocations():
			loc.dump()


##############################################################
##############################################################


class FritzingPart:
	s_roundingSize = 3
	s_fontFamily = 'DroidSans'
	s_fontSize = 1.62	# for mm
	s_usedFontSize = 0
	s_textFill = '#202020'
	s_scaleFactor = 1	# for mm

	# describes the first socket svg path for mm(usage c<3 points>c<3 points>)
	# will be recalculated for in
	s_socketRestPartMM1 = [
		-0.844, 0,											# first m
		0, -0.466,    0.377, -0.844,    0.844, -0.844,		# first c
		0.466, 0,     0.844, 0.377,     0.844, 0.844 		# 2nd c
	]

	# describes the 2nd socket svg path for mm (usage c<3 points>c<3 points>)
	# will be recalculated for in
	s_socketRestPartMM2 = [
		0.844, 0,											# first m
		0, 0.466,     -0.377, 0.844,    -0.844, 0.844,		# first c
		-0.466, 0,    -0.844, -0.377,   -0.844, -0.844 		# 2nd c
	]


	s_femaleSocketRestPath1 = ''		# will be set according to mm or in
	s_femaleSocketRestPath2 = ''		# will be set according to mm or in

	def __init__(self, m_mmOrInch, folder, width, height, distX, distY=None):
		m_mmOrInch = 'in' if m_mmOrInch == 'inch' else m_mmOrInch
		if not m_mmOrInch in ['mm', 'in']:
			raise Exception('first Argument must be mm or in')
		self.m_mmOrInch = m_mmOrInch
		self.adaptm_mmOrInch(m_mmOrInch)

		self.m_outFolder = folder
		if not os.path.exists(folder):
			os.mkdir(folder)

		self.m_locationLists = dict()		# name => LocationList
		self.m_width = self.round(width)	# in mm
		self.m_height = self.round(height)	# in mm
		self.m_distX = distX				# distance horizontally
		if distY is None:
			distY = distX
		self.m_distY = distY
		self.m_svgRoot = None				# xml node
		self.m_mainNode = None				# main group in svg root

		# the fpz stuff
		
		self.m_fzpRoot = None
		self.m_fzpConnectors = None
		self.m_fzpBuses = None

		# other file names
		self.m_fzpFileName = None
		self.m_mainSvgFileName = None
		self.m_iconFileName = None


	@classmethod
	def round(cls, num):
		return round(num, FritzingPart.s_roundingSize)


	@classmethod
	def adaptm_mmOrInch(cls, m_mmOrInch):
		scale = 1.0 if m_mmOrInch == 'mm' else 1 / 25.4
		#print('using wrong scaling factor !!!')
		cls.s_scaleFactor = scale
		cls.s_usedFontSize = cls.round(cls.s_fontSize * scale)
		cls.s_femaleSocketRestPath1 = cls.adaptPath(cls.s_socketRestPartMM1, 'mcc', scale)
		cls.s_femaleSocketRestPath2 = cls.adaptPath(cls.s_socketRestPartMM2, 'mcc', scale)


	@classmethod
	def adaptPath(cls, numbers, types, scale):
		'''
			scale the coodinates in numbers, scale them and combine them to a path, using types
		'''
		newNumbers = [cls.round(x * scale) for x in numbers]
		ret = ''
		start = 0
		for theType in types:
			if theType == 'c':
				ret += 'c'
				ret += cls.getCoordsString(newNumbers, start, 6)
				start += 6
			elif theType == 'm':
				ret += 'm'
				ret += cls.getCoordsString(newNumbers, start, 2)
				start += 2
			else:
				raise Exception('Unhandled path type found: ' + theType)
		ret = ret.replace('0.0,', '0,')
		ret = ret.replace('0.0c', '0c')
		ret = ret.replace('0.0m', '0m')
		ret = ret.replace(',-', '-')
		return ret


	@classmethod
	def getCoordsString(cls, numbers, start, numOfCoords):
		ret = ''
		
		for ii in range(numOfCoords):
			#print('start + ii = ' + str(start + ii))
			ret += str(numbers[start + ii]) + ','
		ret = ret[:-1]
		return ret



	def addLocationList(self, name, x, y, dx, dy, num):
		theList = LocationList(name, x, y, dx, dy, num)
		self.m_locationLists[name] = theList


	def getAllLocationsOf(self, name):
		theList = self.m_locationLists[name]
		return theList.getLocations()


	def dumpLocations(self):
		for locList in self.m_locationLists.values():
			locList.dump()


	def initSvg(self):
		root = self.createSvgRootNode(self.m_width, self.m_height)
		self.m_svgRoot = root
		root.set('enable-background', 'new 0 0 ' + str(self.m_width) + ' ' + str(self.m_height))


	def createSvgRootNode(self, width, height):
		size = self.m_mmOrInch
		ret = ET.Element('svg')
		ret.set('version', '1.1')
		ret.set('id', 'Layer_1')
		ret.set('xmlns', 'http://www.w3.org/2000/svg')
		ret.set('xmlns:xlink', 'http://www.w3.org/1999/xlink')
		ret.set('x', '0' + size)
		ret.set('y', '0' + size)
		ret.set('width', str(width) + size)		# fails to show corect buses: width*1.25
		ret.set('height', str(height) + size)
		ret.set('viewBox', '0 0 ' + str(width) + ' ' + str(height))

		return ret


	def fillBackground(self, color):
		sub = self.addGroup(self.m_mainNode, name='background')
		self.addRect(sub, 0, 0, self.m_width, self.m_height, color)


	def addRect(self, parent, x, y, w, h, color, usePrefix=False):
		prefix = 'svg:' if usePrefix else ''
		rect = ET.SubElement(parent, prefix + 'rect')
		rect.set('x', str(x))
		rect.set('y', str(y))
		rect.set('width', str(w))
		rect.set('height', str(h))
		rect.set('fill', color)
		return rect
	

	def addCircle(self, parent, cx, cy, r, strokeWidth, fill, stroke):
		c = ET.SubElement(parent, 'circle')
		c.set('cx', str(self.round(cx)))
		c.set('cy', str(self.round(cy)))
		c.set('r', str(self.round((r))))
		c.set('stroke-width', str(self.round(strokeWidth)))		# seems to be very necessary!!
		if fill:
			c.set('fill', fill)
		else:
			c.set('fill', '#383838')
		if stroke:
			c.set('stroke', stroke)
		return c


	def addPath(self, parent, color, d):
		path = ET.SubElement(parent, 'path')
		path.set('fill', color)
		path.set('d', d)


	def addGroup(self, parent=None, name=None):
		group = ET.SubElement(parent, 'g')
		if name is not None:
			group.set('id', name)
		return group


	def addText(self, parent, text, x, y, fill=None, rotation=0, fontSize=0, fontFamily=None, anchor=None):
		svgText = ET.SubElement(parent, 'text')
		svgText.set('x', str(self.round(x)))
		svgText.set('y', str(self.round(y)))

		fill = self.s_textFill if not fill else fill
		svgText.set('fill', fill)

		fontFamily = fontFamily if fontFamily else self.s_fontFamily
		svgText.set('font-family', fontFamily)

		fontSize = fontSize if fontSize > 0 else self.s_usedFontSize
		svgText.set('font-size', str(fontSize))

		if anchor is None:
			anchor = 'middle'
		svgText.set('text-anchor', anchor)
		svgText.text = text
		return text
	

	def addLine(self, parent, x1, y1, x2, y2, stroke, strokeWidth, id=None):
		svgLine = ET.SubElement(parent, 'line')
		svgLine.set('x1', str(self.round(x1)))
		svgLine.set('y1', str(self.round(y1)))
		svgLine.set('x2', str(self.round(x2)))
		svgLine.set('y2', str(self.round(y2)))
		svgLine.set('stroke', stroke)
		svgLine.set('stroke-width', str(self.round(strokeWidth)))
		if id is not None:
			svgLine.set('id', id)
		return svgLine


	def createFzp(self, moduleId, fritzingVersion, metaDict, tags, properties, viewFiles):
		module = ET.Element('module')
		module.set('moduleId', moduleId)
		module.set('fritzingVersion', fritzingVersion)
		for key, value in metaDict.items():
			self.addSimpleNode(module, key, value)

		tagsNode = ET.SubElement(module, 'tags')
		for tag in tags:
			self.addSimpleNode(tagsNode, 'tag', tag)

		propertiesNode = ET.SubElement(module, 'properties', )
		for property in properties:
			nd = self.addSimpleNode(propertiesNode, 'property', property[1])
			nd.set('name', property[0])

		self.fzpInitViews(module, viewFiles)

		self.m_fzpConnectors = ET.SubElement(module, 'connectors')
		self.m_fzpBuses = ET.SubElement(module, 'buses')
		self.m_fzpRoot = module
		self.createFzpConnectors()
		self.createFzpBuses()


	def writePrettyXml(self, root, fName):
		rough_string = ET.tostring(root, 'utf-8')
		reparsed = minidom.parseString(rough_string)
		pretty = reparsed.toprettyxml(indent="	", newl='\n', encoding='utf-8')
		
		with open(fName, 'wb') as xmlFile:
			xmlFile.write(pretty)


	def writeFzp(self, fNameRoot):
		'''
			Write a pretty-printed XML string for self.m_fzpRoot
		'''
		fName = self.m_outFolder + '/' + fNameRoot
		self.m_fzpFileName = fNameRoot
		self.writePrettyXml(self.m_fzpRoot, fName)


	def addBus(self, id, connectors):
		bus = ET.SubElement(self.m_fzpBuses, 'bus')
		bus.set('id', id)
		for conn in connectors:
			nodeMember = ET.SubElement(bus, 'nodeMember')
			nodeMember.set('connectorId', conn)


	def addSimpleNode(self, parent, tag, text):
		ret = ET.SubElement(parent, tag)
		ret.text = str(text)
		return ret


	@classmethod
	def getFzpViews(cls):
		return ['breadboardView', 'schematicView', 'pcbView']


	def fzpInitView(self, parent, name, image, layerId):
		view = ET.SubElement(parent, name)
		layers = ET.SubElement(view, 'layers')
		layers.set('image', image)
		layer = ET.SubElement(layers, 'layer')
		layer.set('layerId', layerId)


	def writeFzpz(self, fNameRoot):
		folder = self.m_outFolder + '/'
		fName = folder + fNameRoot
		#if os.path.isfile(fName):
		#	os.remove(fName)
		with ZipFile(fName, 'w') as myZip:
			self.writeZippedFile(myZip, 'svg.breadboard', self.m_mainSvgFileName)
			self.writeZippedFile(myZip, 'svg.icon', self.m_iconFileName)
			self.writeZippedFile(myZip, 'part', self.m_fzpFileName)


	def writeZippedFile(self, zipFile, prolog, fileToZip):
		if not fileToZip:
			return
		fullName = self.m_outFolder + '/' + fileToZip
		destName = prolog + '.' + fileToZip
		zipFile.write(fullName, arcname=destName, compress_type= ZIP_DEFLATED)


	def createIconRootNode(self):
		ret = self.createSvgRootNode(32, 32)
		
		return ret
	

	def writeOutIconFile(self, rootNode, fNameRoot):
		self.m_iconFileName = self.m_outFolder + '/' + fNameRoot
		self.writePrettyXml(rootNode, self.m_iconFileName)


	def showOneSvgSocket(self, parent, loc):
		id = loc.m_name + 'pin'
		group = self.addGroup(parent, id)

		startX = str(loc.m_x)
		startY = str(loc.m_y)

		d = 'M'+startX + ',' + startY + self.s_femaleSocketRestPath1
		self.addPath(group, '#e6e6e6', d)

		d = 'M'+startX + ',' + startY + self.s_femaleSocketRestPath2
		self.addPath(group, '#bfbfbf', d)

		self.addCircle(group, loc.m_x, loc.m_y, self.m_pinRadius, self.m_pinRadius/ 5, '#383838', None)
		#c = ET.SubElement(group, 'circle')
		#c.set('cx', startX)
		#c.set('cy', startY)
		#c.set('r', str(self.m_pinRadius))
		#c.set('stroke-width', str(self.round(self.m_pinRadius/ 5)))		# seems to be very necessary!!
		#c.set('fill', '#383838')

###############################################################
###############################################################


class FritzingBreadBoard (FritzingPart):

	#s_socketRestPath1 = 'c0-0.466,0.377-0.844,0.844-0.844c0.466,0,0.844,0.377,0.844,0.844'

	#dEnd = 'c0,1.322-1.072,2.394-2.394,2.394c-1.322,0-2.394-1.071-2.394-2.394l0,0'
	#s_socketRestPath2 = 'c0,0.466-0.377,0.844-0.844,0.844c-0.466,0-0.844-0.377-0.844-0.844l0,0'

	def __init__(self, m_mmOrInch, folder, width, height, numPins, distX, distY=None):

		super().__init__(m_mmOrInch, folder, width, height, distX, distY)
		self.m_numPinsPerLine = numPins
		self.m_pinRadius = self.round(distX * 0.15)	# recommended
		#self.m_usedPinRadius = self.m_pinRadius
		self.m_innerRowNames = []		# the names of my non-electrode names
		self.m_outerRowNames = []		# the names of my elctrode rows
		self.m_outerPinGroupsSize = 6	# denotes the gaps in the outer pin rows
		self.m_numberingDiff = 5		# the grid of wanted numbers
		self.m_numberingYValues = []	# the y values of the numbering lines
		self.m_svgTextsGroup = None		# the svg node holding all texts
		self.m_electrodeLines = []		# array of red or blue electrode lines (set by application)
		self.m_busGroups = []			# array denoting the lines which are bussed together (set by application)



	def doAllPins(self, theLambda):
		'''
			Iterate over all pins
		'''
		self.doAllOuterPins(theLambda)
		self.doAllInnerPins(theLambda)


	def doAllOuterPins(self, theLambda):
		'''
			Iterate over all outer row pins
		'''
		indexList = self.getOuterRowIndices()
		for nm in self.m_outerRowNames:
			locs = self.getAllLocationsOf(nm)
			for idx in indexList:
				loc = locs[idx]
				theLambda(loc)


	def doAllInnerPins(self, theLambda):
		'''
			Iterate over all inner row pins
		'''
		indexList = self.getInnerRowIndices()
		for nm in self.m_innerRowNames:
			locs = self.getAllLocationsOf(nm)
			for idx in indexList:
				loc = locs[idx]
				theLambda(loc)


	def addInnerRow(self, name, x, y):
		self.m_innerRowNames.append(name)
		self.addLocationList(name, x, y, self.m_distX, 0, self.m_numPinsPerLine+2)


	def addInnerRows(self, names, x, y, numbersBefore, numbersAfter):
		runningY = y
		if numbersBefore:
			self.m_numberingYValues.append(runningY)
			runningY += self.m_distY
		for name in names:
			self.addInnerRow(name, x, runningY)
			runningY += self.m_distY
		if numbersAfter:
			self.m_numberingYValues.append(runningY)
			runningY += self.m_distY
		return runningY


	def addOuterRow(self, name, x, y):
		self.m_outerRowNames.append(name)
		self.addLocationList(name, x, y, self.m_distX, 0, self.m_numPinsPerLine+2)


	def add2OuterRows(self, names, left, y):
		runningY = y
		self.m_electrodeLines.append([runningY, '#0000ff'])
		runningY += self.m_distY
		self.addOuterRow(names[0], left, runningY)
		runningY += self.m_distY
		self.addOuterRow(names[1], left, runningY)
		runningY += self.m_distY
		self.m_electrodeLines.append([runningY, '#ff0000'])
		runningY += self.m_distY
		return runningY


	def getOuterRowIndices(self):
		'''
			get all indices of the pins in outer rows (not including name locations)
		'''
		ret = []
		for ii in range(1, self.m_numPinsPerLine + 1):
			if ii % self.m_outerPinGroupsSize != 0:
				ret.append(ii)
		return ret


	def getInnerRowIndices(self):
		'''
			Get the indices of all pins in an inner row (not including name locations)
		'''
		return range(1, self.m_numPinsPerLine + 1)


	def writeSvg(self, fNameRoot):
		self.m_innerRowNames = sorted(self.m_innerRowNames)
		self.m_outerRowNames = sorted(self.m_outerRowNames)
		fName = self.m_outFolder + '/' + fNameRoot
		self.initSvg()
		self.m_mainNode = self.addGroup(self.m_svgRoot, name='breadboardbreadboard')
		#self.m_mainNode.set('transform', 'matrix(1000,0,0,1000,0,0)')
		self.fillBackground('#d9d9d9')

		self.showTexts(self.m_innerRowNames)
		self.showTexts(self.m_outerRowNames)
		self.showSvgSockets()
		self.showNumbering()
		self.showElectrodes()

		self.writePrettyXml(self.m_svgRoot, fName)
		self.m_mainSvgFileName = fNameRoot


	def showElectrodes(self):
		group = self.addGroup(self.m_mainNode, 'electrodes')
		thickness = 0.3 * self.s_scaleFactor
		for elec in self.m_electrodeLines:
			self.addRect(group, 0, elec[0], self.m_width, thickness, elec[1])

		
	def showNumbering(self):
		locListName = self.m_innerRowNames[0]
		diff = self.m_numberingDiff
		locs = self.getAllLocationsOf(locListName)

		for y in self.m_numberingYValues:
			idx = diff
			while idx <= self.m_numPinsPerLine:
					start = locs[idx]
					x = start.m_x
					self.addText(self.m_svgTextsGroup, str(idx), x, y + (self.m_distY / 2.0))
					idx += diff


	def showTexts(self, rowNames):
		texts = self.m_svgTextsGroup
		if texts is None:
			texts = self.addGroup(self.m_mainNode, 'texts')
			self.m_svgTextsGroup = texts
		for name in rowNames:
			locs = self.getAllLocationsOf(name)
			for ii in [0, len(locs) - 1]:
				start = locs[ii]
				x = start.m_x
				y = start.m_y + self.m_pinRadius * 1.2
				self.addText(texts, name, x, y)


	def showSvgSockets(self):
		sockets = self.addGroup(self.m_mainNode, 'sockets')
		self.doAllPins(lambda loc : self.showOneSvgSocket(sockets, loc))





	def createFzpConnectors(self):
		conns = self.m_fzpConnectors
		conns.set('ignoreTerminalPoints', 'true')
		self.doAllPins(lambda loc : self.createFzpConnector(loc))


	def createFzpConnector(self, location):
		conn = ET.SubElement(self.m_fzpConnectors, 'connector')
		connName = location.m_name
		conn.set('id', connName)
		conn.set('name', connName)
		conn.set('type', 'female')
		self.addSimpleNode(conn, 'description', 'breadboard socket')
		views = ET.SubElement(conn, 'views')
		for viewName in self.getFzpViews():
			v = ET.SubElement(views, viewName)
			p = ET.SubElement(v, 'p')
			p.set('layer', 'breadboardbreadboard')
			p.set('svgId', connName + 'pin')
		erc = ET.SubElement(conn, 'erc')
		erc.set('ignore', 'always')


	def createFzpBuses(self):
		'''
			create all buses in the fzp file
		'''
		# first the outer buses
		indexes = self.getOuterRowIndices()
		for outerName in self.m_outerRowNames:
			locs = self.getAllLocationsOf(outerName)
			pinIds = [locs[idx].m_name for idx in indexes]
			id = 'o' + outerName
			self.addBus(id, pinIds)

		# then the inner buses
		for busGroup in self.m_busGroups:
			#locs = self.getAllLocationsOf(outerName)
			id = 'i' + busGroup[0] + busGroup[-1]
			for idx in range(self.m_numPinsPerLine):
				pinIds = [rowName + str(idx+1) for rowName in busGroup]
				self.addBus(id + str(idx+1), pinIds)

	
	def fzpInitViews(self, module, viewFiles):
		views = ET.SubElement(module, 'views')
		self.fzpInitView(views, 'iconView', viewFiles[0], 'icon')
		for viewName in self.getFzpViews():
			self.fzpInitView(views, viewName, viewFiles[1], 'breadboardbreadboard')


	def createIconSvg(self, fNameRoot, text=None):
		main = self.createSvgRootNode(32, 32)
		symbols = self.addGroup(main, 'symbols')
		size = 32.0
		scale = size / self.m_height

		for electrode in self.m_electrodeLines:
			self.addRect(symbols, 0, scale * electrode[0], size, 0.4, electrode[1])
		if text:
			half = self.round(size * 0.5)
			fontSize = 12
			self.addText(symbols, text, half, half + fontSize * 0.35, fontSize=fontSize )
			
			
		#self.doAllPins(lambda loc : self.writeOneIconSymbol(symbols, loc, scale, size))
		
		fName = self.m_outFolder + '/' + fNameRoot
		self.m_iconFileName = fNameRoot
		self.writePrettyXml(main, fName)


	def writeOneIconSymbol(self, parent, loc, scale, size):
		x = self.round(loc.m_x * scale - size)
		y = self.round(loc.m_y * scale - size)
		self.addRect(parent, x, y, size, size, '#999', usePrefix=False)


#############################################################
#############################################################

class FritzingMicroProcessor(FritzingPart):
	def __init__(self, mmOrInch, outFolder, width, height, pinDistX):
		super().__init__(mmOrInch, outFolder, width, height, pinDistX, pinDistX)
		self.m_pinRows = dict()
		self.m_pinRadius = self.round(pinDistX * 0.15)	# recommended
		self.initSvg()
		self.m_mainNode = self.addGroup(self.m_svgRoot, name='microPins')
		self.m_texts = self.addGroup(self.m_svgRoot, name='texts')
		self.m_graphics = self.addGroup(self.m_svgRoot, name='graphics')

		self.m_schematicSvgFileName = None


	def addPinRow(self, name, x,  y, distX, distY, microPins):
		list = []
		pX = x
		pY = y
		for pin in microPins:
			pin.m_x = self.round(pX)
			pin.m_y = self.round(pY)
			pX += distX
			pY += distY
			list.append(pin)
		self.m_pinRows[name] = list


	def writeSvg(self, fNameRoot):
		
		fName = self.m_outFolder + '/' + fNameRoot
		
		self.m_mainSvgFileName = fNameRoot

		fontSize = self.s_usedFontSize * 0.5

		for name, list in self.m_pinRows.items():
			shift = False
			yText = list[0].m_y
			if yText < self.m_height * 0.5:
				yText1 = yText + self.m_distY*0.7
				yText2 = yText1 + fontSize
			else:
				yText1 = yText - self.m_distY*0.5
				yText2 = yText1 - fontSize
			for microPin in list:
				if microPin.m_name is not None:
					self.showOneSvgSocket(self.m_mainNode, microPin)
					yText = yText2 if shift else yText1
					self.addText(self.m_texts, microPin.m_name, microPin.m_x, yText, fontSize=fontSize)
					shift = not shift


		self.writePrettyXml(self.m_svgRoot, fName)



	def writeSchematicSvg(self, fNameRoot, numWidth, numHeight, outer):
		fName = self.m_outFolder + '/' + fNameRoot
		self.m_schematicSvgFileName = fNameRoot

		width = numWidth * self.m_distX + 2*outer
		height = numHeight * self.m_distY + 2*outer
		svg = self.createSvgRootNode(width, height)
		schematic = self.addGroup(svg, 'schematic')
		outerRect = self.addRect(schematic, outer, outer, width-2*outer, height-2*outer, '#FFFFFF')
		outerRect.set('class', 'interior rect')
		outerRect.set('stroke', '#000000' )
		lineStrokeWidth = 0.1 * self.s_scaleFactor
		outerRect.set('stroke-width', str(2 * lineStrokeWidth))
		fontSize = self.m_distY * 0.5
		rectRadius = self.m_distX * 0.2

		for _,list in self.m_pinRows.items():
			for microPin in list:
				if microPin.m_name is not None:
					loc = microPin.m_schemLoc
					if loc is None:
						continue
					pos = microPin.m_schemPos
					if loc == 'l':
						startX = 0
						stopX = outer
						startY = self.m_distY * pos + outer
						stopY = startY
						textX = stopX + 2*lineStrokeWidth
						textY = stopY + fontSize*0.35
						anchor = 'start'
					elif loc == 'r':
						startX = width
						stopX = width - outer
						startY = self.m_distY * pos + outer
						stopY = startY
						textX = stopX - 2*lineStrokeWidth
						textY = stopY + fontSize*0.35
						anchor = 'end'
					elif loc == 't':
						startX = self.m_distX * pos + outer
						stopX = startX
						startY = 0
						stopY = outer
						textX = startX
						textY = stopY + fontSize
						anchor = 'middle'
					elif loc == 'b':
						startX = self.m_distX * pos + outer
						stopX = startX
						startY = height
						stopY = height - outer
						textX = startX
						textY = stopY - fontSize
						anchor = 'middle'
					
					self.addLine(schematic, startX, startY, stopX, stopY, '#000000', lineStrokeWidth, id=microPin.m_name + 'pin')
					self.addText(schematic, microPin.m_name, textX, textY, fontSize=fontSize, anchor=anchor)
					rect = self.addRect(schematic, startX - rectRadius, startY - rectRadius, 2*rectRadius, 2*rectRadius, '#ff0000')
					rect.set('id', microPin.m_name + 'terminal')


		self.writePrettyXml(svg, fName)


	def writePcbSvg(self, fNameRoot):
		fName = self.m_outFolder + '/' + fNameRoot
		self.m_schematicSvgFileName = fNameRoot

		svg = self.createSvgRootNode(self.m_width, self.m_height)
		group = self.addGroup(svg)
		texts = self.addGroup(svg)
		
		color = '#9a916c'
		rad = 0.61
		strokeWidth = 0.33
		fontSize = self.s_usedFontSize * 0.5
		shift = False


		for _,list in self.m_pinRows.items():
			yText = list[0].m_y
			if yText < self.m_height * 0.5:
				yText1 = yText + self.m_distY*0.7
				yText2 = yText1 + fontSize
			else:
				yText1 = yText - self.m_distY*0.5
				yText2 = yText1 - fontSize
			for microPin in list:
				if microPin.m_name is not None:
					#addCircle(self, parent, cx, cy, r, strokeWidth, fill, stroke):
					circle = self.addCircle(group, microPin.m_x, microPin.m_y, rad, strokeWidth, 'none', color)
					circle.set('id', microPin.m_name + 'pad')
					circle.set('connectorname', microPin.m_name)
					yText = yText2 if shift else yText1
					self.addText(texts, microPin.m_name, microPin.m_x, yText, fontSize=fontSize)
					shift = not shift

		self.writePrettyXml(svg, fName)