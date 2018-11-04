# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2014.

"""
Contains useful functions which used across the modules
"""

import threading
import xmpp
import urllib
from socket import error
from writer import *

isNumber = lambda obj: (not execute(int, (obj,), False) is None)


def execute(handler, list=(), log=True):
	"""
	Just executes handler(*list) safely
	Writes a crashlog if errors occurred
	"""
	try:
		result = handler(*list)
	except (SystemExit, xmpp.NodeProcessed):
		result = True
	except Exception:
		result = None
		if log:
			crashLog(handler.func_name)
			logger.error("Exception happened during executing function: %s%s" % (handler.func_name, str(list)))
	return result


def runThread(func, args=(), name=None, delay=0):
	"""
	Runs a thread with custom args and name
	Needed to reduce code
	Parameters:
		func: function you need to be running in a thread
		args: function arguments
		name: thread name
		att: number of attempts
		delay: if set, then threading.Timer will be started, not threading.Thread

	"""
	if delay:
		logger.debug("threading: starting timer for %s%s, "
			"name:%s, delay:%s" % (func.func_name, str(args), name, delay))
		thr = threading.Timer(delay, execute, (func, args))
	else:
		thr = threading.Thread(target=execute, args=(func, args))
	name = name or func.__name__
	name = str(name) + "-" + str(time.time())
	thr.name = name
	thr.start()
	return thr


def safe(func):
	"""
	Executes func(*args) safely
	"""
	def wrapper(*args):
		try:
			func(*args)
		except xmpp.NodeProcessed:
			pass
		except Exception:
			crashLog(func.func_name)
	wrapper.__name__ = func.__name__
	return wrapper


def cache(func):
	"""
	Caches user/group ids for future usage
	"""
	def wrapper(self, uid, fields=None):
		fields = fields or []
		fieldsStr = ",".join(fields)
		if uid in self.cache:
			if self.cache[uid]["fields"] == fieldsStr:
				return self.cache[uid]

		result = func(self, uid, fields)
		result["fields"] = fieldsStr
		if "uid" in result:
			del result["uid"]
		if uid in self.cache:
			self.cache[uid].update(result)
		else:
			self.cache[uid] = result
		return result
	wrapper.__name__ = func.__name__
	return wrapper


def threaded(func):
	"""
	Another decorator.
	Executes a function in a thread
	"""
	def wrapper(*args):
		runThread(func, args)
	wrapper.__name__ = "threaded_%s" % func.__name__
	return wrapper


def buildDataForm(form=None, type="form", fields=[], title=None, data=[]):
	"""
	Provides easier method to build data forms using dict for each form object
	Parameters:
		form: xmpp.DataForm object
		type: form type
		fields: list of form objects represented as dict, e.g.
			[{"var": "cool", "type": "text-single",
			"desc": "my cool description", "value": "cool"}]
		title: form title
		data: advanced data for form. e.g.
			instructions (if string in the list), look at xmpp/protocol.py:1326
	"""
	if title and form:
		form.setTitle(title)
	form = form or xmpp.DataForm(type, data, title)
	for key in fields:
		field = form.setField(key["var"], key.get("value"),
					key.get("type"), key.get("desc"), key.get("options"))
		if key.get("payload"):
			field.setPayload(key["payload"])
		if key.get("label"):
			field.setLabel(key["label"])
		if key.get("requred"):
			field.setRequired()
	return form


def buildIQError(stanza, error=xmpp.ERR_FEATURE_NOT_IMPLEMENTED, text=None):
	"""
	Provides a way to build IQ error reply
	"""
	error = xmpp.Error(stanza, error, True)
	if text:
		tag = error.getTag("error")
		if tag:
			tag.setTagData("text", text)
	return error


def normalizeValue(value):
	"""
	Normalizes boolean values from dataform replies
	"""
	if isNumber(value):
		value = int(value)
	elif value and value.lower() == "true":
		value = 1
	else:
		value = 0
	return value


def getLinkData(url, encode=True):
	"""
	Gets link data and ignores any exceptions
	Parameters:
		encode: base64 data encode
	"""
	try:
		opener = urllib.urlopen(url)
		data = opener.read()
	except (Exception, error):
		return ""
	if data and encode:
		data = data.encode("base64")
	return data


TIME_VALUES = {"s": 60, "m": 360, "d": 86400, "M": 2592000, "y": 31536000}


def TimeMachine(text):
	"""
	TARDIS Prototype
	"""
	time = 0
	for i in xrange(0, len(text) - 1, 3):
		current = text[i:i + 3]
		x = current[-1]
		if x in TIME_VALUES:
			time += int(current[:-1]) * TIME_VALUES[x]
	return time


class ExpiringObject(object):
	"""
	Object that acts the same as the one it keeps
	But also has a limited lifetime
	"""
	def __init__(self, obj, lifetime):
		self.obj = obj
		self.created = time.time()
		self.lifetime = lifetime

	def hasExpired(self):
		return time.time() >= (self.created + self.lifetime)

	def __getattr__(self, attr):
		try:
			result = object.__getattribute__(self, attr)
		except AttributeError:
			result = getattr(self.obj, attr)
		return result

	def __iter__(self):
		if hasattr(self.obj, "__iter__"):
			return self.obj.__iter__()
		raise TypeError("Not iterable")

	def next(self):
		if hasattr(self.obj, "next"):
			return self.obj.next()
		raise TypeError("Not iterable")

	# TODO what if our object isn't iterable?
	def __str__(self):
		result = ""
		for num, i in enumerate(self.obj):
			result += str(i)
			if num < (len(self.obj) - 1):
				result += ", "
		return result


# Yay!
