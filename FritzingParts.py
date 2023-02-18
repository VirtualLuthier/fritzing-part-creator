import os
import xml.etree.ElementTree as ET
from xml.dom import minidom


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
	s_fontSize = 4.6036
	s_textFill = '#202020'

	def __init__(self, folder, width, height, distX, distY=None, factor=1):
		self.m_outFolder = folder
		if not os.path.exists(folder):
			os.mkdir(folder)
		self.m_locationLists = dict()
		self.m_factor = factor
		self.m_width = self.round(width)
		self.m_height = self.round(height)
		self.m_distX = distX
		if distY is None:
			distY = distX
		self.m_distX = distX
		self.m_distY = distY
		self.m_svgRoot = None
		self.m_mainNode = None

		# the fpz stuff
		self.m_fpzFile = None
		self.m_fzpRoot = None
		self.m_fzpConnectors = None
		self.m_fzpBuses = None



	def round(self, num):
		return round(num, FritzingPart.s_roundingSize)


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
		ret = ET.Element('svg')
		ret.set('version', '1.1')
		ret.set('id', 'Layer_1')
		ret.set('xmlns', 'http://www.w3.org/2000/svg')
		ret.set('xmlns:xlink', 'http://www.w3.org/1999/xlink')
		ret.set('x', '0px')
		ret.set('y', '0px')
		ret.set('width', str(width) + 'px')		# fails to show corect buses: width*1.25
		ret.set('height', str(height) + 'px')
		ret.set('viewBox', '0 0 ' + str(width) + ' ' + str(height))

		return ret


	def fillBackground(self, color):
		sub = self.startGroup(self.m_mainNode, name='background')
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


	def addPath(self, parent, color, d):
		path = ET.SubElement(parent, 'path')
		path.set('fill', color)
		path.set('d', d)


	def startGroup(self, parent=None, name=None):
		group = ET.SubElement(parent, 'g')
		if name is not None:
			group.set('id', name)
		return group


	def addText(self, parent, text, x, y, fill=None, rotation=0):
		svgText = ET.SubElement(parent, 'text')
		svgText.set('x', str(self.round(x)))
		svgText.set('y', str(self.round(y)))
		svgText.set('fill', self.s_textFill)
		svgText.set('font-family', self.s_fontFamily)
		svgText.set('font-size', str(self.s_fontSize))
		#svgText.set('text-align', 'center')
		svgText.set('text-anchor', 'middle')
		svgText.text = text


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


###############################################################
###############################################################


class FritzingBreadBoard (FritzingPart):
	def __init__(self, folder, width, height, numPins, distX, distY=None, factor=1 ):
		super().__init__(folder, width, height, distX, distY, factor)
		self.m_numPins = numPins
		self.m_pinRadius = 1.197
		self.m_innerRowNames = []		# the names of my non-electrode names
		self.m_outerRowNames = []		# the names of my elctrode rows
		self.m_outerPinGroupsSize = 6	# denotes the gaps in the outer pin rows
		self.m_numberingDiff = 5		# the grid of wanted numbers
		self.m_numberingHeights = []	# the y values of the numbering lines
		self.m_svgTextsGroup = None		# the svg node holding all texts
		self.m_electrodes = []			# array of red or blue electrode lines (set by application)
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
		self.addLocationList(name, x, y, self.m_distX, 0, self.m_numPins+2)


	def addOuterRow(self, name, x, y):
		self.m_outerRowNames.append(name)
		self.addLocationList(name, x, y, self.m_distX, 0, self.m_numPins+2)


	def getOuterRowIndices(self):
		'''
			get all indices of the pins in outer rows (not including name locations)
		'''
		ret = []
		for ii in range(1, self.m_numPins + 1):
			if ii % self.m_outerPinGroupsSize != 0:
				ret.append(ii)
		return ret


	def getInnerRowIndices(self):
		'''
			Get the indices of all pins in an inner row (not including name locations)
		'''
		return range(1, self.m_numPins + 1)


	def writeSvg(self, fNameRoot):
		self.m_innerRowNames = sorted(self.m_innerRowNames)
		self.m_outerRowNames = sorted(self.m_outerRowNames)
		fName = self.m_outFolder + '/' + fNameRoot
		self.initSvg()
		self.m_mainNode = self.startGroup(self.m_svgRoot, name='breadboardbreadboard')
		self.fillBackground('#d9d9d9')

		self.showTexts(self.m_innerRowNames)
		self.showTexts(self.m_outerRowNames)
		self.showSvgSockets()
		self.showNumbering()
		self.showElectrodes()

		self.writePrettyXml(self.m_svgRoot, fName)


	def showElectrodes(self):
		group = self.startGroup(self.m_mainNode, 'electrodes')
		for elec in self.m_electrodes:
			self.addRect(group, 0, elec[0], self.m_width, 0.5, elec[1])

		
	def showNumbering(self):
		locListName = self.m_innerRowNames[0]
		diff = self.m_numberingDiff
		locs = self.getAllLocationsOf(locListName)

		for y in self.m_numberingHeights:
			idx = diff
			while idx <= self.m_numPins:
					start = locs[idx]
					x = start.m_x
					self.addText(self.m_svgTextsGroup, str(idx), x, y + (self.m_distY / 2.0))
					idx += diff


	def showTexts(self, rowNames):
		texts = self.m_svgTextsGroup
		if texts is None:
			texts = self.startGroup(self.m_mainNode, 'texts')
			self.m_svgTextsGroup = texts
		for name in rowNames:
			locs = self.getAllLocationsOf(name)
			for ii in [0, len(locs) - 1]:
				start = locs[ii]
				x = start.m_x
				y = start.m_y + self.m_pinRadius * 1.2
				self.addText(texts, name, x, y)


	def showSvgSockets(self):
		sockets = self.startGroup(self.m_mainNode, 'sockets')
		self.doAllPins(lambda loc : self.showOneSvgSocket(sockets, loc))


	def showOneSvgSocket(self, parent, loc):
		id = loc.m_name + 'pin'
		group = self.startGroup(parent, id)

		dEnd = 'c0-1.322,1.071-2.394,2.394-2.394c1.321,0,2.394,1.072,2.394,2.394'
		startX = self.round(loc.m_x - 2.393)
		startY = loc.m_y
		d = 'M'+str(startX) + ',' + str(startY) + dEnd
		self.addPath(group, '#e6e6e6', d)

		dEnd = 'c0,1.322-1.072,2.394-2.394,2.394c-1.322,0-2.394-1.071-2.394-2.394l0,0'
		startX = self.round(loc.m_x + 2.394)
		startY = loc.m_y
		d = 'M'+str(startX) + ',' + str(startY) + dEnd
		self.addPath(group, '#bfbfbf', d)

		c = ET.SubElement(group, 'circle')
		c.set('cx', str(loc.m_x))
		c.set('cy', str(loc.m_y))
		c.set('r', str(self.m_pinRadius))
		c.set('fill', '#383838')


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
			for idx in range(self.m_numPins):
				pinIds = [rowName + str(idx+1) for rowName in busGroup]
				self.addBus(id + str(idx+1), pinIds)

	
	def fzpInitViews(self, module, viewFiles):
		views = ET.SubElement(module, 'views')
		self.fzpInitView(views, 'iconView', viewFiles[0], 'icon')
		for viewName in self.getFzpViews():
			self.fzpInitView(views, viewName, viewFiles[1], 'breadboardbreadboard')


	def createIconSvg(self, fNameRoot):
		main = self.createSvgRootNode(32, 32)
		symbols = self.startGroup(main, 'symbols')
		scaleX = 32.0 / self.m_width
		scaleY = 32.0 / self.m_height
		scale = scaleX if scaleX < scaleY else scaleY
		size = self.round(3.6 * scale)

		self.doAllPins(lambda loc : self.writeOneIconSymbol(symbols, loc, scale, size))
		
		fName = self.m_outFolder + '/' + fNameRoot
		self.writePrettyXml(main, fName)


	def writeOneIconSymbol(self, parent, loc, scale, size):
		x = self.round(loc.m_x * scale - size)
		y = self.round(loc.m_y * scale - size)
		self.addRect(parent, x, y, size, size, '#999', usePrefix=False)


