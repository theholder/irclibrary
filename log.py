import time

_kindNames = [
	"ERR",
	"WRN",
	"INF",
	"DBG",
]

_kindColors = [
	"red",
	"yellow",
	"cyan",
	"purple",
]

LOG_NAME_LIMIT = 5

ERROR = 0
WARNING = 1
INFO = 2
DEBUG = 3

_ANSI_COLORS = ["black", "red", "green", "yellow", "blue", "purple", "cyan", "white"]
def _ansi(reset = False, color = None):
	if reset:
		return "\x1b[0m"
	elif color != None:
		return "\x1b[%im" % (30 + _ANSI_COLORS.index(color))

def _ansi_color(color, text):
	return _ansi(color = color) + text + _ansi(reset = True)

def error(name, msg):
	write(name, ERROR, msg)

def warn(name, msg):
	write(name, WARNING, msg)

def info(name, msg):
	write(name, INFO, msg)

def debug(name, msg):
	write(name, DEBUG, msg)

def write(name, kind, msg):
	kindName = _kindNames[kind]
	kindColor = _kindColors[kind]
	ts = "%s" % (time.strftime("%m-%d-%y %H:%M:%S", time.localtime(time.time())))
	print("[[%s]] - [%s] [%s] %s" % (ts,_ansi_color("green", name.ljust(LOG_NAME_LIMIT)), _ansi_color(kindColor, kindName), msg))
