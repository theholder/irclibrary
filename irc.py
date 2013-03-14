################################################################
# File: irc.py
# Title: IRC Client Library
# Author: sorch/theholder <support@sorch.info>
# Version: 0.5
# Description:
#  An event-based library for connecting to one or multiple IRC rooms
################################################################

################################################################
# License
################################################################
# Copyright 2013 Contributing Authors
# This program is distributed under the terms of the GNU GPL.
#################################################################


#IMPORTS
###


import logging,os,random,re,sys,time,json, tools
from tools import ts
try:
    from gevent import socket
except ImportError:
    import socket

from logging.handlers import RotatingFileHandler
from optparse import OptionParser


class IRCConnection(object):
    """\
    Connection class for connecting to IRC servers
    """
    # a couple handy regexes for reading text
    nick_re = re.compile('.*?Nickname is already in use')
    nick_regged_re = re.compile('.*?This nickname is registered')
    ping_re = re.compile('^PING (?P<payload>.*)')
    chanmsg_re = re.compile(':(?P<nick>.*?)!\S+\s+?PRIVMSG\s+#(?P<channel>[-\w]+)\s+:(?P<message>[^\n\r]+)')
    privmsg_re = re.compile(':(?P<nick>.*?)!~\S+\s+?PRIVMSG\s+[^#][^:]+:(?P<message>[^\n\r]+)')
    part_re = re.compile(':(?P<nick>.*?)!\S+\s+?PART\s+#(?P<channel>[-\w]+)')
    join_re = re.compile(':(?P<nick>.*?)!\S+\s+?JOIN\s+:\s*#(?P<channel>[-\w]+)')
    quit_re = re.compile(':(?P<nick>.*?)!\S+\s+?QUIT\s+.*')
    registered_re = re.compile(':(?P<server>.*?)\s+(?:376|422)')
    
    # mapping for logging verbosity
    verbosity_map = {
        0: logging.ERROR,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    
    def __init__(self, server, port, nick, logfile=None, verbosity=1, needs_registration=True):
        self.server = server
        self.port = port
        self.nick = self.base_nick = nick
        
        self.logfile = logfile
        self.verbosity = verbosity
        
        self._registered = not needs_registration
        self._out_buffer = []
        self._callbacks = []
        self.logger = self.get_logger('ircconnection.logger', self.logfile)
    
    def get_logger(self, logger_name, filename):
        log = logging.getLogger(logger_name)
        log.setLevel(self.verbosity_map.get(self.verbosity, logging.INFO))
        
        if self.logfile:
            handler = RotatingFileHandler(filename, maxBytes=1024*1024, backupCount=2)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            log.addHandler(handler)
        
        if self.verbosity == 2 or not self.logfile:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            log.addHandler(stream_handler)
        
        return log
    
    def send(self, data, force=False):
        """\
        Send raw data over the wire if connection is registered. Otherewise,
        save the data to an output buffer for transmission later on.
        If the force flag is true, always send data, regardless of 
        registration status.
        """
        if self._registered or force:
            self._sock_file.write('%s\r\n' % data)
            self._sock_file.flush()
        else:
            self._out_buffer.append(data)
    
    def connect(self):
        """\
        Connect to the IRC server using the nickname
        """
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sock.connect((self.server, self.port))
        except socket.error:
            self.logger.error('Unable to connect to %s on port %d' % (self.server, self.port), exc_info=1)
            sys.exit(1)
        
        self._sock_file = self._sock.makefile()
        self.register_nick()
        self.register()
    
    def close(self):
        self._sock.close()    
    
    def register_nick(self):
        print('\033[94m[INF]\033[0m Registering nick %s' % self.nick)
        self.send('NICK %s' % self.nick, True)

    def register(self):
        print('\033[94m[INF]\033[0m Authing as %s' % self.nick)
        self.send('USER %s %s bla :%s' % (self.nick, self.server, self.nick), True)

    def join(self, channel):
        channel = channel.lstrip('#')
        self.send('JOIN #%s' % channel)
        print('joining #%s' % channel)

    def part(self, channel):
        channel = channel.lstrip('#')
        self.send('PART #%s' % channel)
        self.logger.debug('leaving #%s' % channel)

    def push(self, channel, type, ret):
        q = "\x01%s %s\x01" % (type, ret)
        self.send("PRIVMSG #%s :%s" %( channel.lstrip("#"), q))
    
    def respond(self, message, channel=None, nick=None):
        """\
        Multipurpose method for sending responses to channel or via message to
        a single user
        """
        if channel:
            self.send('PRIVMSG #%s :%s' % (channel.lstrip('#'), message))
        elif nick:
            self.send('PRIVMSG %s :%s' % (nick, message))
    
    def dispatch_patterns(self):
        """\
        Low-level dispatching of socket data based on regex matching, in general
        handles
        
        * In event a nickname is taken, registers under a different one
        * Responds to periodic PING messages from server
        * Dispatches to registered callbacks when
            - any user leaves or enters a room currently connected to
            - a channel message is observed
            - a private message is received
        """
        return (
            (self.nick_re, self.new_nick),
            (self.ping_re, self.handle_ping),
            (self.part_re, self.handle_part),
            (self.join_re, self.handle_join),
            (self.quit_re, self.handle_quit),
            (self.chanmsg_re, self.handle_channel_message),
            (self.privmsg_re, self.handle_private_message),
            (self.registered_re, self.handle_registered),
            (self.nick_regged_re, self.handle_regnick),
        )
    
    def register_callbacks(self, callbacks):
        """\
        Hook for registering custom callbacks for dispatch patterns
        """
        self._callbacks.extend(callbacks)
    
    def new_nick(self):
        """\
        Generates a new nickname based on original nickname followed by a
        random number
        """
        old = self.nick
        self.nick = '%s_%s' % (self.base_nick, random.randint(1, 1000))
        print('\033[33m[WARN]\033[0m Nick %s already taken, trying %s' % (old, self.nick))
        self.register_nick()

    def handle_regnick(self):
		"""\
		Handles identifying to NickServ
		"""
		ret = "id %s" % tools.password
		print('\033[33m[WARN]\033[0m Nick is registered identifying')
		self.respond(ret, None, "nickserv")
    
    def handle_ping(self, payload):
        """\
        Respond to periodic PING messages from server
        """
        self.send('PONG %s' % payload, True)

    def handle_registered(self, server):
        """\
        When the connection to the server is registered, send all pending
        data.
        """
        if not self._registered:
            print('[%s]:\033[94m[INF]\033[0m Registered' % ts)
            self._registered = True
            for data in self._out_buffer:
                self.send(data)
            self._out_buffer = []
    
    def handle_part(self, nick, channel):
        for pattern, callback in self._callbacks:
            if pattern.match('/part'):
                callback(nick, '/part', channel)
        print("[INF] %s part #%s" % (nick.lower(), channel.lower()))
    
    def handle_join(self, nick, channel):
        for pattern, callback in self._callbacks:
            if pattern.match('/join'):
                callback(nick, '/join', channel)
        print("[INF] %s joined #%s" % (nick.lower(), channel.lower()))
    
    def handle_quit(self, nick):
        for pattern, callback in self._callbacks:
            if pattern.match('/quit'):
                callback(nick, '/quit', channel)
    
    def _process_command(self, nick, message, channel):
        results = []
        
        for pattern, callback in self._callbacks:
            match = pattern.match(message)
            if match:
                results.append(callback(nick, message, channel, **match.groupdict()))
        return results
        print(results)
    
    def handle_channel_message(self, nick, channel, message):
        for result in self._process_command(nick, message, channel):
            if result:
                self.respond(result, channel=channel)
                ts = time.strftime("%I:%M%p %S", time.localtime(time.time()))
                print("[%s]: @#%s: %s" % (ts,str(channel), str(result)))
    
    def handle_private_message(self, nick, message):
        for result in self._process_command(nick, message, None):
            if result:
                self.respond(result, nick=nick)
    
    def enter_event_loop(self):
        """\
        Main loop of the IRCConnection - reads from the socket and dispatches
        based on regex matching
        """
        patterns = self.dispatch_patterns()
        self.logger.debug('entering receive loop')
        
        while 1:
            try:
                data = self._sock_file.readline()
            except socket.error:
                data = None
            
            if not data:
                print('\033[94m[INF]\033[0m server closed connection')
                self.close()
                return True
            
            data = data.rstrip()

            for pattern, callback in patterns:
                match = pattern.match(data)
                if match:
                    callback(**match.groupdict())


class IRCBot(object):
    """\
    A class that interacts with the IRCConnection class to provide a simple way
    of registering callbacks and scripting IRC interactions
    """
    def __init__(self, conn):
        self.conn = conn
        
        # register callbacks with the connection
        self.register_callbacks()
    
    def register_callbacks(self):
        """\
        Hook for registering callbacks with connection -- handled by __init__()
        """
        self.conn.register_callbacks((
            (re.compile(pattern), callback) \
                for pattern, callback in self.command_patterns()
        ))
    
    def _ping_decorator(self, func):
        def inner(nick, message, channel, **kwargs):
            message = re.sub('^%s[:,\s]\s*' % self.conn.nick, '', message)
            return func(nick, message, channel, **kwargs)
        return inner
    
    def is_ping(self, message):
        return re.match('^%s[:,\s]' % self.conn.nick, message) is not None
    
    def fix_ping(self, message):
        return re.sub('^%s[:,\s]\s*' % self.conn.nick, '', message)
    
    def command(self, pattern, callback):
        return (
            '^%s[:,\s]\s*%s' % (self.conn.nick, pattern.lstrip('^')),
            self._ping_decorator(callback),
        )
    
    def command_patterns(self):
        """\
        Hook for defining callbacks, stored as a tuple of 2-tuples:
        
        return (
            ('/join', self.room_greeter),
            ('!find (^\s+)', self.handle_find),
        )
        """
        raise NotImplementedError
    
    def respond(self, message, channel=None, nick=None):
        """\
        Wraps the connection object's respond() method
        """
        self.conn.respond(message, channel, nick)
        print("%s %s %s" % (nick, channel, message))

    def join(self, message):
           self.conn.send("JOIN #%s" % message.lower())

    def part(self, message):
           self.conn.send("PART #%s" % message.lower())


def run_bot(bot_class, host, port, nick, channels=None):
    """\
    Convenience function to start a bot on the given network, optionally joining
    some channels
    """
    conn = IRCConnection(host, port, nick)
    bot_instance = bot_class(conn)
    
    while 1:
        conn.connect()
        
        channels = channels or []
        
        for channel in channels:
            conn.join(channel)
        
        conn.enter_event_loop()


class SimpleSerialize(object):
    """\
    Allow simple serialization of data in IRC messages with minimum of space.
    
    * Only supports dictionaries *
    """
    def serialize(self, dictionary):
        return '|'.join(('%s:%s' % (k, v) for k, v in dictionary.iteritems()))
    
    def deserialize(self, string):
        return dict((piece.split(':', 1) for piece in string.split('|')))
