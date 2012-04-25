#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, os.path
import time
import re
import urlparse
from pprint import pprint

try: debug = int(os.environ["DEBUG"]) != 0
except: debug = False

debug_shell = None
try:
	#sys.path += [os.path.expanduser("~/Programmierung/py_better_exchook")]
	import better_exchook
	better_exchook.install()
	orig_debug_shell = better_exchook.debug_shell
	
	# wrap debug_shell so that we don't end up calling it recursively
	debug_shell_running = False
	def debug_shell(user_ns, user_global_ns):
		global debug_shell_running
		if debug_shell_running: return
		debug_shell_running = True
		orig_debug_shell(user_ns, user_global_ns)
		debug_shell_running = False
	better_exchook.debug_shell = debug_shell
	
	# debug shell: better_exchook.debug_shell(locals(), globals())
except:
	print "failed to import better_exchook"
	sys.excepthook(*sys.exc_info())
	print "This is optional but you might want to get it from here:"
	print "  https://github.com/albertz/py_better_exchook"
	print
	if debug:
		print "This is configured with debug and we need some functions from it, thus it is not optional."
		sys.exit(-1)


try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	from PyQt4.QtWebKit import *
except:
	print "failed to import PyQt4"
	sys.excepthook(*sys.exc_info())
	print "This is mandatory. Install it with Homebrew by:"
	print "  brew install pyqt"
	print
	sys.exit(-1)

def iterHtmlNodes(n):
	while not n.isNull():
		yield n
		n = n.nextSibling()

def deepIterHtmlNodes(root):
	for n in iterHtmlNodes(root):
		yield n
		for c in deepIterHtmlNodes(n.firstChild()):
			yield c

def nodeAttribs(n):
	attribNames = list(n.attributeNames())
	return dict(map(lambda a: (unicode(a), unicode(n.attribute(a))), attribNames))

def dumpNode(n):
	assert isinstance(n, QWebElement)
	childs = list(iterHtmlNodes(n.firstChild()))
	s = ""
	if len(childs) == 0:
		s = repr(unicode(n.toPlainText()))
	print unicode(n.tagName()).lower(), str(len(childs)) + " childs", s, nodeAttribs(n)

def getRoot(root):
	if isinstance(root, QWebView):
		root = root.page()
	if isinstance(root, QWebPage):
		root = root.mainFrame()
	if isinstance(root, QWebFrame):
		root = root.documentElement()
	assert isinstance(root, QWebElement)
	return root

def dumpHtmlTree(root):
	root = getRoot(root)
	for n in deepIterHtmlNodes(root):
		dumpNode(n)

def matchNode(n, tagName, attribs={}):
	if n.isNull(): return False
	if unicode(n.tagName()).lower() != tagName.lower(): return False
	nAttr = nodeAttribs(n)
	for k,v in attribs.items():
		nv = nAttr.get(k, "")
		if v != nv: return False
	return True

def findNodes(tagName, attribs={}):
	root = getRoot(web)
	for n in deepIterHtmlNodes(root):
		if matchNode(n, tagName, attribs):
			yield n

def findLinks(txt):
	for l in findNodes("a"):
		if unicode(l.toPlainText()) == txt:
			yield l

def selectInputBox(n):
	n.evaluateJavaScript("this.checked = true;")

def setInputText(n, txt):
	n.setAttribute("value", txt)

def selectInputSelect(n, txt):
	txtRepr = repr(txt)
	if txtRepr[:1] == 'u': txtRepr = txtRepr[1:]
	assert txtRepr[:1] in ["'",'"']
	assert txtRepr[-1:] in ["'",'"']
	n.evaluateJavaScript("this.value = " + txtRepr + ";")
	
def submitClick(n):
	#n.evaluateJavaScript("this.click();")
	# from http://stackoverflow.com/a/3432510/133374
	n.evaluateJavaScript(
		"var evObj = document.createEvent('MouseEvents');" +
		"evObj.initEvent( 'click', true, true );" +
		"this.dispatchEvent(evObj);")

def submitClickNative(n):
	# http://stackoverflow.com/questions/2655414/qt-force-qwebview-to-click-on-a-web-element-even-one-not-visible-on-the-window
	center = n.geometry().center()
	n.setFocus()
	eventArgs = center, Qt.MouseButton(1), Qt.MouseButtons(1), Qt.KeyboardModifiers(0)
	pressEvent = QMouseEvent(QMouseEvent.MouseButtonPress, *eventArgs)
	app.sendEvent(web, pressEvent)
	releaseEvent = QMouseEvent(QMouseEvent.MouseButtonRelease, *eventArgs)
	app.sendEvent(web, releaseEvent)
	
def onFinishedLoading( result ):
	global webNextAction
	print "finished loading:", web.mainFrame().baseUrl()
	if webNextAction is None: return
	#print "huhu", result, webNextAction
	#dumpHtmlTree(web)
	#print unicode(getRoot(web).toPlainText()).encode("utf-8")
	try:
		assert result, "failed to load web page"
		webNextAction()
		#if webNextAction is not None:
		#	time.sleep(3)
	except:
		sys.excepthook(*sys.exc_info())
		print "page content:", unicode(getRoot(web).toPlainText()).encode("utf-8")
		print "*** registering failed"
		webNextAction = None

def showMacDockIcon():
	# http://stackoverflow.com/a/4686782/133374
	import ctypes
	# /System/Library/Frameworks/ApplicationServices.framework/Frameworks/HIServices.framework/Headers/Processes.h
	# /System/Library/Frameworks/CoreServices.framework/Frameworks/CarbonCore.framework/Headers/MacTypes.h
	OSStatus = ctypes.c_int32 # MacTypes.h
	ProcessApplicationTransformState = ctypes.c_uint32 # Processes.h
	class ProcessSerialNumber(ctypes.Structure): # MacTypes.h
		_fields_ = [
			("highLongOfPSN", ctypes.c_ulong),
			("lowLongOfPSN", ctypes.c_ulong)]
	kCurrentProcess = 2 # Processes.h
	kProcessTransformToForegroundApplication = 1 # Processes.h
	kProcessTransformToBackgroundApplication = 2
	kProcessTransformToUIElementApplication = 4
	TransformProcessType = ctypes.pythonapi.TransformProcessType # Processes.h
	TransformProcessType.argtypes = (ctypes.POINTER(ProcessSerialNumber), ProcessApplicationTransformState)
	TransformProcessType.restype = OSStatus
	psn = ProcessSerialNumber()
	psn.highLongOfPSN = 0
	psn.lowLongOfPSN = kCurrentProcess
	r = TransformProcessType(psn, kProcessTransformToUIElementApplication)
	print "TransformProcessType:", r

def hideMacDockIcon():
	# http://stackoverflow.com/a/9220857/133374
	import AppKit
	# https://developer.apple.com/library/mac/#documentation/AppKit/Reference/NSRunningApplication_Class/Reference/Reference.html
	NSApplicationActivationPolicyRegular = 0
	NSApplicationActivationPolicyAccessory = 1
	NSApplicationActivationPolicyProhibited = 2
	AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
		
app = QApplication(sys.argv)
if sys.platform == "darwin" and not debug:
	hideMacDockIcon()

if debug:
	view = QWebView()
	web = view.page()
	view.show()
else:
	#view = None
	#web = QWebPage()
	# we need a QWebView for the img drawing
	view = QWebView()
	web = view.page()

web.connect(web, SIGNAL("loadFinished(bool)"), onFinishedLoading)

def loadUrl(l):
	if isinstance(web, QWebView):
		web.load(QUrl(l))
	elif isinstance(web, QWebPage):
		web.mainFrame().load(QUrl(l))
	else:
		assert False, "type of " + str(web) + " unknown"

debug_shell_here = lambda: debug_shell(locals(), globals())

try: bookUrl = sys.argv[1]
except:
	loadUrl("http://books.google.com")
	assert view, "we need user interaction"
	raw_input("Press enter once you selected the book")
	bookUrl = unicode(web.mainFrame().baseUrl())

def findPageSelectorNodes():
	nextPageImgNodes = [ n for n in findNodes("img") if n.attribute("src").contains("page_right.png") ]
	assert len(nextPageImgNodes) == 1
	nextPageImgNode = nextPageImgNodes[0]
	nextPageNode = nextPageImgNode.parent()
	assert nextPageNode.tagName() == "DIV"
	prevPageNode = nextPageNode.previousSibling()
	assert prevPageNode.tagName() == "DIV"
	curPageNode = prevPageNode.previousSibling()
	assert curPageNode.tagName() == "DIV"
	assert curPageNode.toPlainText().contains("Page")
	return curPageNode, prevPageNode, nextPageNode

def getCurPage():
	curPageNode,_,_ = findPageSelectorNodes()
	txt = unicode(curPageNode.toPlainText())[len("Page"):]
	try: return int(txt)
	except: return -1

def selectPage(num):
	curPage = getCurPage()
	if num > curPage:
		while num > getCurPage():
			_,_,nextPageNode = findPageSelectorNodes()
			submitClickNative(nextPageNode)
	if num < curPage:
		while num < getCurPage():
			_,prevPageNode,_ = findPageSelectorNodes()
			submitClickNative(prevPageNode)
	assert num == getCurPage()
	
def paramsFromUrl(url):
	url = unicode(url) # in case it is a QString
	parsedUrl = urlparse.urlparse(url)
	return dict(urlparse.parse_qsl(parsedUrl.query))


	
def findPageImages():
	pageImages = {}
	for n in findNodes("img"):
		widthAttrib = n.attribute("width")
		if widthAttrib.isEmpty(): continue
		width = int(widthAttrib)
		if width < 500: continue
		srcParams = paramsFromUrl(n.attribute("src"))
		if "pg" not in srcParams: continue
		pgText = srcParams["pg"]
		if pgText[0:2] != "PA": continue
		pg = int(pgText[2:])
		pageImages[pg] = n
	return sorted(pageImages.iteritems())


startPage = int(sys.argv[2])
endPage = int(sys.argv[3])
assert startPage <= endPage

def getPageImage(num):
	imgs = dict(findPageImages())
	return imgs[num]

def pageImageLoaded(num):
	img = getPageImage(num)
	return img.geometry().height() > 0

def scrollViewport(dx, dy):
	# this is for now. make this more dynamic later...
	outerViewportNode = list(findNodes("div",{"id":"viewport"}))[0]
	scrollareaNode = outerViewportNode.firstChild()	
	innerViewportNode = scrollareaNode.firstChild()
	scrollareaNode.evaluateJavaScript("this.scrollLeft += %i" % dx)
	scrollareaNode.evaluateJavaScript("this.scrollTop += %i" % dy)
	app.processEvents()

def imgVisibleRect(imgNode):
	curVisible = imgNode.webFrame().geometry().intersect(imgNode.geometry())
	curVisible = curVisible.translated(-imgNode.geometry().topLeft()) # relative
	return curVisible

def exportCurPage():
	global mydir, web
	curPage = getCurPage()
	imgNode = getPageImage(curPage)
	imgSize = imgNode.geometry().size()
	
	# In some cases (always? most often), invisible areas of the image
	# seem to be invalid. To overcome this:
	# It scrolls always around and copies the visible area until
	# the whole image has been copied.
	# Note that we cannot render a subpart of the image, thus the
	# render clipRect can also be ignored here and we need
	# some own image for every copy op.
	img = QImage(imgSize, QImage.Format_ARGB32)
	imgPainter = QPainter(img)
	while True:		
		imgNode = getPageImage(curPage) # there might be a new imgNode
		curVisible = imgVisibleRect(imgNode)

		subimg = QImage(imgSize, QImage.Format_ARGB32)
		subimgPainter = QPainter(subimg)
		imgNode.render(subimgPainter)
		subimgPainter.end()

		imgPainter.drawImage(
			curVisible.left(), curVisible.top(),
			subimg,
			curVisible.left(), curVisible.top(),
			curVisible.width(), curVisible.height())

		#print curVisible, imgSize
		#subimg.save(mydir + "/page%i_%i_%i.png" % (curPage,curVisible.left(),curVisible.top()))
		if curVisible.right() < imgSize.width() - 1:
			scrollViewport(100,0)
		elif curVisible.bottom() < imgSize.height() - 1:
			scrollViewport(-imgSize.width(),0) # back to left
			scrollViewport(0,100)
		else:
			break
	
	imgPainter.end()
	img.save(mydir + "/page%i.png" % curPage)
	
def web_selectNextPage():
	global webNextAction, startPage, endPage
	webNextAction = None

	selectPage(startPage)
	lastPage = None
	
	while True:
		curPage = getCurPage()
		if lastPage is not None:
			assert curPage > lastPage, "switching pages doesn't work"
		lastPage = curPage
		if curPage > endPage:
			print "finished"
			break
		
		while not pageImageLoaded(curPage):
			time.sleep(0.1)
			app.processEvents()

		# TODO: export
		print "export", curPage, "..."
		exportCurPage()
		#debug_shell(locals(), globals())
		#return
	
		# select next
		_,_,nextPageNode = findPageSelectorNodes()
		submitClickNative(nextPageNode)
		

def fixupBookUrl(url):
	import urlparse, urllib
	parsedUrl = list(urlparse.urlparse(url))
	parsedUrl[1] = "books.google.com"
	query = dict(urlparse.parse_qsl(parsedUrl[4]))
	query["hl"] = "en"
	parsedUrl[4] = urllib.urlencode(query)
	return urlparse.urlunparse(parsedUrl)
	
def doExport():
	global webNextAction, success, bookUrl
	success = False
	webNextAction = web_selectNextPage
	bookUrl = fixupBookUrl(bookUrl)
	loadUrl(bookUrl)
	while webNextAction is not None:
		time.sleep(0.1)
		app.processEvents()
	return success


mydir = os.path.dirname(__file__)
LogFile = mydir + "/google-books-export.log"
print "logfile:", LogFile

try:
	log = eval(open(LogFile).read())
	assert isinstance(log, dict)
except IOError: # e.g. file-not-found. that's ok
	log = {}
except:
	print "logfile reading error"
	sys.excepthook(*sys.exc_info())
	log = {}

def betterRepr(o):
	# the main difference: this one is deterministic
	# the orig dict.__repr__ has the order undefined.
	if isinstance(o, list):
		return "[" + ", ".join(map(betterRepr, o)) + "]"
	if isinstance(o, tuple):
		return "(" + ", ".join(map(betterRepr, o)) + ")"
	if isinstance(o, dict):
		return "{\n" + "".join(map(lambda (k,v): betterRepr(k) + ": " + betterRepr(v) + ",\n", sorted(o.iteritems()))) + "}"
	# fallback
	return repr(o)
	
def saveLog():
	global log, LogFile
	f = open(LogFile, "w")
	f.write(betterRepr(log))
	f.write("\n")

# do
doExport()

# exit:
del web
sys.exit()
#sys.exit(app.exec_())

