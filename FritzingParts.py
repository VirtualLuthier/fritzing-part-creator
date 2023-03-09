'''
	Can create a fritzing 
	- breadboard, or
	- a microcontroller like an arduino
	by using an API.
	Tries to use the mminimal input to create all
	needed files
	It values clarity higher than beauty. So it does not 
	use image backgrounds, but shows more text.
	One reason for implementing it was the fact, that fritzing seems to have 
	a problem with coordinates. My svg files always have the real (mm or in)
	coordinates.
	In general the icon file must be drawn by the caller (breadboards have some own
	icon functionality)
'''
'''
	For pinouts see e.g. https://docs.arduino.cc/hardware/micro
'''


import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from zipfile import ZipFile, ZIP_DEFLATED


########################################################################
########################################################################



class Location:
	'''
		The location of a pin on the part
	'''
	def __init__(self, x, y, name):
		self.m_x = self.round(x)
		self.m_y = self.round(y)
		self.m_name = name


	def dump(self):
		print(str(self.m_x) + ', ' + str(self.m_y))


	def round(self, num):
		return round(num, FritzingPart.s_roundingSize)
	

##########################################################################
##########################################################################


class MicroPin(Location):
	'''
		This is a location that can handle a position on the schematic view
		or a reference to another pin (e.g. GND or RESET).
		- Position r5 means e.g. on the right side at the 5th grid point
		- Position oGND means, is represented by the pin with name "GND"
	'''
	def __init__(self, name, position):
		super().__init__(-1, -1, name)
		self.m_schemLoc = None
		self.m_schemPos = None
		if position is not None:
			self.m_schemLoc = position[0]
			numString = position[1:]
			if self.m_schemLoc == 'o':
				self.m_schemPos = numString		# id of used other pin
			else:
				self.m_schemPos = int(numString)
		elif name is not None:
			raise Exception('schematic position needed for pin: ' + name)



##############################################################
##############################################################

class LocationList:
	'''
		A list of locations
	'''


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
	'''
		Contains the common functionality of
		- Breadboard generator and
		- MicroprocessorGenerator
	'''
	# some static common settings
	s_roundingSize = 3		# for rounding of coordinates
	s_fontFamily = 'DroidSans'
	s_fontSize = 1.62		# for mm
	s_usedFontSize = 0		# will be calculated
	s_textFill = '#000000'	# '#202020'
	s_scaleFactor = 1		# for mm, recalculated for in

	# describes the first socket svg path for mm(usage m<1 point>c<3 points>c<3 points>)
	# will be recalculated for in
	s_socketRestPartMM1 = [
		-0.844, 0,											# first m
		0, -0.466,    0.377, -0.844,    0.844, -0.844,		# first c
		0.466, 0,     0.844, 0.377,     0.844, 0.844 		# 2nd c
	]

	# describes the 2nd socket svg path for mm (usage m<1 point>c<3 points>c<3 points>)
	# will be recalculated for in
	s_socketRestPartMM2 = [
		0.844, 0,											# first m
		0, 0.466,     -0.377, 0.844,    -0.844, 0.844,		# first c
		-0.466, 0,    -0.844, -0.377,   -0.844, -0.844 		# 2nd c
	]

	s_femaleSocketRestPath1 = ''		# will be set according to mm or in
	s_femaleSocketRestPath2 = ''		# will be set according to mm or in

	def __init__(self, m_mmOrInch, folder, filenameRoot, width, height, distX, distY=None):
		'''
			mmOrInch:		mm or in
			folder:			where to output files
			filenameRoot:	used to create all output file names
		'''
		m_mmOrInch = 'in' if m_mmOrInch == 'inch' else m_mmOrInch
		if not m_mmOrInch in ['mm', 'in']:
			raise Exception('first Argument must be mm or in')
		self.m_mmOrInch = m_mmOrInch
		self.adaptm_mmOrInch(m_mmOrInch)

		self.m_outFolder = folder
		if not os.path.exists(folder):
			os.mkdir(folder)
		self.m_filenameRoot = filenameRoot

		self.m_locationLists = dict()		# dict name => LocationList
		self.m_width = self.round(width)	# in mm or in
		self.m_height = self.round(height)	# in mm or in
		self.m_distX = distX				# pin distance horizontally
		if distY is None:
			distY = distX
		self.m_distY = distY

		self.m_svgRoot = None				# xml node, used for all svg files
		self.m_mainNode = None				# main group in svg root

		# the fpz stuff
		self.m_fzpBuses = []
		self.m_fzpRoot = None				# xml root node
		self.m_fzpConnectors = None
		self.m_fzpBusesNode = None			# xml buses man node


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
			scale the coodinates in numbers, scale them and combine them to a path, using types as path directives
			Can handle most everything except arcs (which have values that must not be scaled)
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
		'''
			build a string using the coords from start in array numbers
		'''
		ret = ''
		for ii in range(numOfCoords):
			ret += str(numbers[start + ii]) + ','
		ret = ret[:-1]		# remove last trailing comma
		return ret


	def getFullPathFor(self, postfix):
		'''
			return the full path for this postfix
		'''
		return self.m_outFolder + '/' + self.getFilenameFor(postfix)


	def getFilenameFor(self, postfix):
		'''
			return the bare file name for this postfix
		'''
		return self.m_filenameRoot + postfix


	def addLocationList(self, name, left, top, dx, dy, num):
		'''
			Create a list of num locations in steps of (dx, dy) and store it under the given name
		'''
		theList = LocationList(name, left, top, dx, dy, num)
		self.m_locationLists[name] = theList


	def getAllLocationsOf(self, name):
		theList = self.m_locationLists[name]
		return theList.getLocations()


	def dumpLocations(self):
		for locList in self.m_locationLists.values():
			locList.dump()


	def initSvg(self):
		'''
			Create the svg node with the correct size and store it
		'''
		root = self.createSvgRootNode(self.m_width, self.m_height)
		root.set('enable-background', 'new 0 0 ' + str(self.m_width) + ' ' + str(self.m_height))


	def createSvgRootNode(self, width, height):
		'''
			Create a node with the needed svg namespace settings
		'''
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
		self.m_svgRoot = ret
		return ret


	def fillBackground(self, color):
		sub = self.addGroup(self.m_mainNode, name='background')
		self.addRect(sub, 0, 0, self.m_width, self.m_height, color)


	def addRect(self, parent, x, y, w, h, color):
		'''
			add a svg rect with the given parameters.
		'''
		#prefix = 'svg:' if useNamespace else ''
		rect = ET.SubElement(parent, 'rect')
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


	def addText(self, parent, text, x, y, fill=None, rotation=0, fontSize=0, fontFamily=None, anchor='middle'):
		svgText = ET.SubElement(parent, 'text')
		svgText.set('x', str(self.round(x)))
		svgText.set('y', str(self.round(y)))

		fill = self.s_textFill if not fill else fill
		svgText.set('fill', fill)

		fontFamily = fontFamily if fontFamily else self.s_fontFamily
		svgText.set('font-family', fontFamily)

		fontSize = fontSize if fontSize > 0 else self.s_usedFontSize
		svgText.set('font-size', str(fontSize))

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


	def createFzp(self, moduleId, fritzingVersion, metaDict, tags, properties):
		'''
			Create fzp file
			- first set metadata
			- create the connectors
			- create buses
		'''
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

		self.fzpInitAllViews(module)

		self.m_fzpConnectors = ET.SubElement(module, 'connectors')
		self.m_fzpBusesNode = ET.SubElement(module, 'buses')
		self.m_fzpRoot = module
		self.createFzpConnectors()
		self.createFzpBuses()

		self.writePrettyXml(self.m_fzpRoot, '.fzp')


	def writePrettyXml(self, root, postfix):
		'''
			write the wanted xml file nicely indented - a bit complicated, but works
		'''
		rough_string = ET.tostring(root, 'utf-8')
		reparsed = minidom.parseString(rough_string)
		pretty = reparsed.toprettyxml(indent="	", newl='\n', encoding='utf-8')
		with open(self.getFullPathFor(postfix), 'wb') as xmlFile:
			xmlFile.write(pretty)


	def addBusNode(self, id, connectors):
		'''
			Add one bus to the fzp file with given id and connectors list
		'''
		bus = ET.SubElement(self.m_fzpBusesNode, 'bus')
		bus.set('id', id)
		for conn in connectors:
			nodeMember = ET.SubElement(bus, 'nodeMember')
			nodeMember.set('connectorId', conn)


	def addSimpleNode(self, parent, tag, text):
		'''
			Add an xml node with given tag and text
		'''
		ret = ET.SubElement(parent, tag)
		ret.text = str(text)
		return ret


	@classmethod
	def getFzpViews(cls):
		'''
			return the possible views (without icon view)
		'''
		return ['breadboard', 'schematic', 'pcb']


	def fzpInitOneView(self, parent, viewName, image, layerIds, srcFolder):
		'''
			init one view at start of the fzp file
		'''
		view = ET.SubElement(parent, viewName + 'View')
		layers = ET.SubElement(view, 'layers')
		layers.set('image', srcFolder + '/' + image)
		for layerId in layerIds:
			layer = ET.SubElement(layers, 'layer')
			layer.set('layerId', layerId)


	def writeFzpz(self):
		'''
			Write the zipped combination file for installation of the part
		'''
		fName = self.getFullPathFor('.fzpz')
		with ZipFile(fName, 'w') as myZip:
			self.writeZippedFile(myZip, 'svg.breadboard.', 'Main.svg')
			self.writeZippedFile(myZip, 'svg.icon.', 'Icon.svg')
			self.writeZippedFile(myZip, 'svg.schematic.', 'Schematic.svg')
			self.writeZippedFile(myZip, 'svg.pcb.', 'Pcb.svg')
			self.writeZippedFile(myZip, 'part.', '.fzp')


	def writeZippedFile(self, zipFile, prolog, postfix):
		'''
			Add one compressed file the fzpz file
		'''
		fullName = self.getFullPathFor(postfix)
		if not os.path.exists(fullName):
			return
		destName = prolog + self.m_filenameRoot + postfix
		zipFile.write(fullName, arcname=destName, compress_type= ZIP_DEFLATED)


	def createIconRootNode(self):
		'''
			For microprocessors the application must draw its own icon file
		'''
		ret = self.createSvgRootNode(32, 32)	
		return ret
	

	def writeOutIconFile(self):
		self.writePrettyXml(self.m_svgRoot, 'Icon.svg')


	def showOneSvgSocket(self, parent, loc):
		'''
			Mostly useful for breadboards, but could also be used by Microprocessors
		'''
		id = loc.m_name + 'pin'
		group = self.addGroup(parent, id)

		startX = str(loc.m_x)
		startY = str(loc.m_y)

		d = 'M'+startX + ',' + startY + self.s_femaleSocketRestPath1
		self.addPath(group, '#e6e6e6', d)

		d = 'M'+startX + ',' + startY + self.s_femaleSocketRestPath2
		self.addPath(group, '#bfbfbf', d)

		self.addCircle(group, loc.m_x, loc.m_y, self.m_pinRadius, self.m_pinRadius/ 5, '#383838', None)


	def addConnectorBus(self, connectors):
		'''
			Store one bus for later usage in the fzp file
		'''
		self.m_fzpBuses.append(connectors)


###############################################################
###############################################################


class FritzingBreadBoard (FritzingPart):
	'''
		A fritzing breadboard. Please see description of __init__()
		outerRows are the rows holding anode or cathode
		inner rows are normally (A-E) and (F-J)
	'''

	def __init__(self, m_mmOrInch, folder, fNameRoot, width, height, numPins, distX, distY=None):
		super().__init__(m_mmOrInch, folder, fNameRoot, width, height, distX, distY)
		self.m_numPinsPerLine = numPins
		self.m_pinRadius = self.round(distX * 0.15)	# recommended
		self.m_innerRowNames = []		# the names of my non-electrode rows
		self.m_outerRowNames = []		# the names of my electrode rows
		self.m_outerPinGroupsSize = 6	# denotes the gaps in the outer pin rows
		self.m_numberingDiff = 5		# the grid of wanted numbers
		self.m_numberingYValues = []	# the y values of the numbering lines
		self.m_svgTextsGroup = None		# the svg node holding all texts
		self.m_electrodeLines = []		# array of red or blue electrode lines (set by application)
		self.m_busGroups = []			# array denoting the lines which are bussed together (set by application)



	def doAllPins(self, theLambda):
		'''
			Iterate over all pins, doing theLambda for each
		'''
		self.doAllOuterPins(theLambda)
		self.doAllInnerPins(theLambda)


	def doAllOuterPins(self, theLambda):
		'''
			Iterate over all outer row pins, doing theLambda for each
		'''
		indexList = self.getOuterRowIndices()
		for nm in self.m_outerRowNames:
			locs = self.getAllLocationsOf(nm)
			for idx in indexList:
				loc = locs[idx]
				theLambda(loc)


	def doAllInnerPins(self, theLambda):
		'''
			Iterate over all inner row pins, doing theLambda for each
		'''
		indexList = self.getInnerRowIndices()
		for nm in self.m_innerRowNames:
			locs = self.getAllLocationsOf(nm)
			for idx in indexList:
				loc = locs[idx]
				theLambda(loc)


	def addInnerRow(self, name, x, y):
		'''
			Sotr one inner row for later use
		'''
		self.m_innerRowNames.append(name)
		self.addLocationList(name, x, y, self.m_distX, 0, self.m_numPinsPerLine+2)


	def addInnerRows(self, names, left, y, numbersBefore, numbersAfter):
		'''
			add a consecutive set of inner rows. If numbersBefore and/or numbersAfter is True, add one/two row(s) for numbers display
			Return the y value for the next usable row
		'''
		runningY = y
		if numbersBefore:
			self.m_numberingYValues.append(runningY)
			runningY += self.m_distY
		for name in names:
			self.addInnerRow(name, left, runningY)
			runningY += self.m_distY
		if numbersAfter:
			self.m_numberingYValues.append(runningY)
			runningY += self.m_distY
		return runningY


	def addOuterRow(self, name, x, y):
		'''
			Store an other row for later usage
		'''
		self.m_outerRowNames.append(name)
		self.addLocationList(name, x, y, self.m_distX, 0, self.m_numPinsPerLine+2)


	def add2OuterRows(self, names, left, y):
		'''
			Add 2 outer rows and one blue and one red line for later use.
			Return y value for the next possible row
		'''
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
			get all indices of the pins in outer rows (not including name locations).
			Leave the  unused locations out.
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


	def writeMainSvg(self):
		'''
			Generate all svg objects amd write to file
		'''
		self.m_innerRowNames = sorted(self.m_innerRowNames)
		self.m_outerRowNames = sorted(self.m_outerRowNames)
		self.initSvg()
		self.m_mainNode = self.addGroup(self.m_svgRoot, name='breadboardbreadboard')
		self.fillBackground('#d9d9d9')

		self.createRowNames(self.m_innerRowNames)
		self.createRowNames(self.m_outerRowNames)
		self.showSvgSockets()
		self.showNumbering()
		self.showElectrodes()

		self.writePrettyXml(self.m_svgRoot, 'Main.svg')


	def showElectrodes(self):
		'''
			create the svg lines in red and blue
		'''
		group = self.addGroup(self.m_mainNode, 'electrodes')
		thickness = 0.3 * self.s_scaleFactor
		for elec in self.m_electrodeLines:
			self.addRect(group, 0, elec[0], self.m_width, thickness, elec[1])

		
	def showNumbering(self):
		'''
			Create the svg numbers beneath the inner rows
		'''
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


	def createRowNames(self, rowNames):
		'''
			Create the svg for the names of the inner rows
		'''
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
		'''
			Create the svg for all sockets
		'''
		sockets = self.addGroup(self.m_mainNode, 'sockets')
		self.doAllPins(lambda loc : self.showOneSvgSocket(sockets, loc))


	def createFzpConnectors(self):
		'''
			Create the xml description of all connectors in the fzp file
		'''
		conns = self.m_fzpConnectors
		conns.set('ignoreTerminalPoints', 'true')
		self.doAllPins(lambda loc : self.createFzpConnector(loc))


	def createFzpConnector(self, location):
		'''
			Create the xml descriptor of one connector in the fzp file
		'''
		conn = ET.SubElement(self.m_fzpConnectors, 'connector')
		connName = location.m_name
		conn.set('id', connName)
		conn.set('name', connName)
		conn.set('type', 'female')
		self.addSimpleNode(conn, 'description', 'breadboard socket')
		views = ET.SubElement(conn, 'views')
		for viewName in self.getFzpViews():
			v = ET.SubElement(views, viewName + 'View')
			p = ET.SubElement(v, 'p')
			p.set('layer', 'breadboardbreadboard')
			p.set('svgId', connName + 'pin')
		erc = ET.SubElement(conn, 'erc')
		erc.set('ignore', 'always')


	def createFzpBuses(self):
		'''
			create all xml buses in the fzp file
		'''
		# first the outer buses (blue and red lines)
		indexes = self.getOuterRowIndices()
		for outerName in self.m_outerRowNames:
			locs = self.getAllLocationsOf(outerName)
			pinIds = [locs[idx].m_name for idx in indexes]
			id = 'o' + outerName
			self.addBusNode(id, pinIds)

		# then the inner buses
		for busGroup in self.m_busGroups:
			id = 'i' + busGroup[0] + busGroup[-1]
			for idx in range(self.m_numPinsPerLine):
				pinIds = [rowName + str(idx+1) for rowName in busGroup]
				self.addBusNode(id + str(idx+1), pinIds)

	
	def fzpInitAllViews(self, module):
		'''
			List the views in the start of the fzp file
		'''
		views = ET.SubElement(module, 'views')
		self.fzpInitOneView(views, 'icon', self.getFilenameFor('Icon.svg'), ['icon'], 'icon')
		for viewName in self.getFzpViews():
			self.fzpInitOneView(views, viewName, self.getFilenameFor('Main.svg'), ['breadboardbreadboard'], 'breadboard')


	def createIconSvg(self, text=None):
		'''
			Create a simple svg file resembling the look of the board. If text is given, show it in the center
		'''
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
						
		self.writePrettyXml(main, 'Icon.svg')


	#def writeOneIconSymbol(self, parent, loc, scale, size):
	#	obsolete
	#	x = self.round(loc.m_x * scale - size)
	#	y = self.round(loc.m_y * scale - size)
	#	self.addRect(parent, x, y, size, size, '#999')


#############################################################
#############################################################


class FritzingMicroProcessor(FritzingPart):
	'''
		Usable to create the fritzing model of an arduino or an esp32
	'''
	def __init__(self, mmOrInch, outFolder, fileNameRoot, width, height, pinDistX):
		super().__init__(mmOrInch, outFolder, fileNameRoot, width, height, pinDistX, pinDistX)
		self.m_pinRows = dict()
		self.m_pinRadius = self.round(pinDistX * 0.15)	# recommended

		# initialize for breadboard view:
		self.initSvg()
		self.m_mainNode = self.addGroup(self.m_svgRoot, name='microPins')
		self.m_texts = self.addGroup(self.m_svgRoot, name='texts')
		self.m_graphics = self.addGroup(self.m_svgRoot, name='graphics')


	def addPinRow(self, name, x,  y, distX, distY, microPins):
		'''
			for an example for micro pins see the CreateArduinoMicro.py
		'''
		list = []
		self.m_pinRows[name] = list
		pX = x
		pY = y
		for pin in microPins:
			name = pin.m_name
			if name:
				oldPin = self.findPinNamed(name)
				if oldPin is not None:
					raise Exception('duplicate name: ' + name)
			pin.m_x = self.round(pX)
			pin.m_y = self.round(pY)
			pX += distX
			pY += distY
			list.append(pin)
		

	def findPinNamed(self, name):
		'''
			Find the pin with the given name (must be unique)
		'''
		for _, list in self.m_pinRows.items():
			for pin in list:
				if pin.m_name == name:
					return pin
		return None


	def writeMainSvg(self):
		'''
			Create the pins and texts for the breadboard view
			Currently no background image is supported
			output the svg file
		'''
		self.fillBackground('#d0d0d0')

		fontSize = self.s_usedFontSize * 0.5

		for _, list in self.m_pinRows.items():
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
					self.showOneMicroSocket(self.m_mainNode, microPin)
					yText = yText2 if shift else yText1
					self.addText(self.m_texts, microPin.m_name, microPin.m_x, yText, fontSize=fontSize)
					shift = not shift


		self.writePrettyXml(self.m_svgRoot, 'Main.svg')


	def showOneMicroSocket(self, parent, microPin):
		'''
			create the svg code for an socket (currently a plain circle)
		'''
		id = microPin.m_name + 'pin'
		circle = self.addCircle(parent, microPin.m_x, microPin.m_y, self.m_pinRadius, self.m_pinRadius/ 5, '#383838', None)
		circle.set('id', id)
		return circle



	def getSchematicOtherReferences(self):
		'''
			return a dict with e.g. RESET => [RESET_2, RESET_3], GND => [GND_2]
			also add the found buses
		'''
		ret = dict()
		for _,list in self.m_pinRows.items():
			for microPin in list:
				loc = microPin.m_schemLoc
				if loc == 'o':
					# a reference
					pos = microPin.m_schemPos
					if not pos in ret.keys():
						# a new other referenced pin
						other = self.findPinNamed(pos)
						if other.m_schemLoc == 'o':
							raise Exception('illegal double other reference: ' + pos)
						ret[pos] = []
					ret[pos].append(microPin.m_name)
		# now add the according buses (if not yet present):
		for name, list in ret.items():
			foundBus = None
			for bus in self.m_fzpBuses:
				if name in bus:
					foundBus = bus
					break
			if foundBus is None:
				foundBus = [name]
				self.m_fzpBuses.append(foundBus)
			for listItem in list:
				if not listItem in foundBus:
					foundBus.append(listItem)
		return ret


	def writeSchematicSvg(self, numWidth, numHeight, outer):
		'''
			Create the schematic svg objects and output the file. Handle the intricate
			case of double pins (like GND and RESET)
		'''
		outerX = outer * self.m_distX
		outerY = outer * self.m_distY
		width = numWidth * self.m_distX + 2*outerX
		height = numHeight * self.m_distY + 2*outerY
		svg = self.createSvgRootNode(width, height)
		schematic = self.addGroup(svg, 'schematic')
		innerRect = self.addRect(schematic, outerX, outerY, width-2*outerX, height-2*outerY, '#FFFFFF')
		innerRect.set('class', 'interior rect')
		innerRect.set('stroke', '#000000' )
		lineStrokeWidth = 0.1 * self.s_scaleFactor
		innerRect.set('stroke-width', str(2 * lineStrokeWidth))
		fontSize = self.m_distY * 0.5
		rectRadius = self.m_distX * 0.2

		schematicOtherReferences = self.getSchematicOtherReferences()
		for _,list in self.m_pinRows.items():
			for microPin in list:
				name = microPin.m_name
				if name is None:
					continue
				loc = microPin.m_schemLoc
				if loc != 'o':
					if name in schematicOtherReferences.keys():
						others = schematicOtherReferences[name]
						for otherName in others:
							self.outputOneSchematicPin(schematic, microPin, otherName, outerX, outerY, width, height, lineStrokeWidth, fontSize, rectRadius)
					self.outputOneSchematicPin(schematic, microPin, name, outerX, outerY, width, height, lineStrokeWidth, fontSize, rectRadius * 2)

		self.writePrettyXml(svg, 'Schematic.svg')


	def outputOneSchematicPin(self, parent, microPin, pinRoot, outerX, outerY, width, height, lineStrokeWidth, fontSize, rectRadius):
		'''
			translate the position of a pin to a line, (end-)rect and the text
		'''
		pos = microPin.m_schemPos
		loc = microPin.m_schemLoc
		if loc == 'l':
			startX = 0
			stopX = outerX
			startY = self.m_distY * pos + outerY
			stopY = startY
			textX = stopX + 2*lineStrokeWidth
			textY = stopY + fontSize*0.35
			anchor = 'start'
		elif loc == 'r':
			startX = width
			stopX = width - outerX
			startY = self.m_distY * pos + outerY
			stopY = startY
			textX = stopX - 2*lineStrokeWidth
			textY = stopY + fontSize*0.35
			anchor = 'end'
		elif loc == 't':
			startX = self.m_distX * pos + outerX
			stopX = startX
			startY = 0
			stopY = outerY
			textX = startX
			textY = stopY + fontSize
			anchor = 'middle'
		elif loc == 'b':
			startX = self.m_distX * pos + outerX
			stopX = startX
			startY = height
			stopY = height - outerY
			textX = startX
			textY = stopY - fontSize
			anchor = 'middle'
		else:
			raise Exception('illegal schema position given: ' + loc + pos)
		
		self.addLine(parent, startX, startY, stopX, stopY, '#000000', lineStrokeWidth, id=pinRoot + 'pin')
		self.addText(parent, microPin.m_name, textX, textY, fontSize=fontSize, anchor=anchor)
		rect = self.addRect(parent, startX - rectRadius, startY - rectRadius, 2*rectRadius, 2*rectRadius, 'none')
		rect.set('id', pinRoot + 'terminal')
		rect.set('stroke-width', '0')
		rect.set('stroke', 'none')


	def writePcbSvg(self):
		'''
			create and output the contents of the pcb file
		'''
		svg = self.createSvgRootNode(self.m_width, self.m_height)
		silkscreen = self.addGroup(svg, 'silkscreen')
		rect = self.addRect(silkscreen, 0, 0, self.m_width, self.m_height, 'none')
		rect.set('stroke', '#000000')
		rect.set('stroke-width', str(self.round(self.s_scaleFactor * 0.1)))
		copper0 = self.addGroup(svg, 'copper0')
				
		copper0Color = '#9a916c'
		rad = 0.619 * self.s_scaleFactor
		strokeWidth = 0.3379 * self.s_scaleFactor
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
					circle = self.addCircle(copper0, microPin.m_x, microPin.m_y, rad, strokeWidth, 'none', copper0Color)
					circle.set('id', microPin.m_name + 'pad')
					circle.set('connectorname', microPin.m_name)
					yText = yText2 if shift else yText1
					self.addText(silkscreen, microPin.m_name, microPin.m_x, yText, fontSize=fontSize)
					shift = not shift

		self.writePrettyXml(svg, 'Pcb.svg')



	def fzpInitAllViews(self, module):
		'''
			create the views description at the beginning of the fzp file
		'''
		views = ET.SubElement(module, 'views')
		self.fzpInitOneView(views, 'icon', self.getFilenameFor('Icon.svg'), ['icon'], 'icon')
		#for viewName in self.getFzpViews():
		self.fzpInitOneView(views, 'breadboard', self.getFilenameFor('Main.svg'), ['breadboard'], 'breadboard')
		self.fzpInitOneView(views, 'schematic', self.getFilenameFor('Schematic.svg'), ['schematic'], 'schematic')
		self.fzpInitOneView(views, 'pcb', self.getFilenameFor('Pcb.svg'), ['copper1', 'silkscreen', 'copper0'], 'pcb')


	def createFzpConnectors(self):
		'''
			Create all the xml descriptions of the connectors. Handle also the double used pins like GND and RESET
		'''
		connectors = self.m_fzpConnectors
		schematicOtherReferences = self.getSchematicOtherReferences()
		for _,list in self.m_pinRows.items():
			for microPin in list:
				mainIdRoot = microPin.m_name
				if mainIdRoot is None:
					continue
				
				loc = microPin.m_schemLoc
				if loc != 'o':					
					if mainIdRoot in schematicOtherReferences.keys():
						others = schematicOtherReferences[mainIdRoot]
						for otherName in others:
							self.createOneFzpConnector(connectors, otherName, mainIdRoot)
				self.createOneFzpConnector(connectors, mainIdRoot, mainIdRoot)
							

	def createOneFzpConnector(self, parent, idRoot, name):
		'''
			Create the xml for one connector. idRoot and name may be different for doubly used pins
		'''
		connector = ET.SubElement(parent, 'connector')
		connector.set('id', 'connector' + idRoot)
		connector.set('type', 'male')
		connector.set('name', name)
		desc = ET.SubElement(connector, 'description')
		desc.text = name
		views = ET.SubElement(connector, 'views')

		view = ET.SubElement(views, 'breadboardView')
		self.addConnectorViewLayer(view, 'breadboard', idRoot + 'pin')

		view = ET.SubElement(views, 'schematicView')
		p = self.addConnectorViewLayer(view, 'schematic', idRoot + 'pin')
		p.set('terminalId', idRoot + 'terminal')

		view = ET.SubElement(views, 'pcbView')
		self.addConnectorViewLayer(view, 'copper0', idRoot + 'pad')
		self.addConnectorViewLayer(view, 'copper1', idRoot + 'pad')


	def addConnectorViewLayer(self, parent, layerName, svgId):
		'''
			Describe the connector references between the different views
		'''
		p = ET.SubElement(parent, 'p')
		p.set('layer', layerName)
		p.set('svgId', svgId)
		return p


	def createFzpBuses(self):
		'''
			Create the xml bus descriptions in the fzp file
		'''
		idx = 1
		for bus in self.m_fzpBuses:
			self.addBusNode('bus' + str(idx), ['connector' + nm for nm in bus])
			idx += 1