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
	debug_shell = better_exchook.debug_shell
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

	
def onFinishedLoading( result ):
	global webNextAction
	#print "huhu", result, webNextAction
	#dumpHtmlTree(web)
	#print unicode(getRoot(web).toPlainText()).encode("utf-8")
	try:
		assert result, "failed to load web page"
		webNextAction()
		if webNextAction is not None:
			time.sleep(3)
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
	view = None
	web = QWebPage()

web.connect(web, SIGNAL("loadFinished(bool)"), onFinishedLoading)

def loadUrl(l):
	if isinstance(web, QWebView):
		web.load(QUrl(l))
	elif isinstance(web, QWebPage):
		web.mainFrame().load(QUrl(l))
	else:
		assert False, "type of " + str(web) + " unknown"

debug_shell_here = lambda: debug_shell(locals(), globals())


def doExport():
	global webNextAction, success
	success = False
	webNextAction = None
	loadUrl("http://books.google.com/")
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
except:
	print "failed to load logfile (if this is the first run, this can be ignored)"
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

