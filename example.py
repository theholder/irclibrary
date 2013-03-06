rooms = ["room", "roomhere"]

from irc import IRCBot, run_bot
import random

owner = "theholder" # put your irc nick here

class bot(IRCBot):

	def nick(self, nick, message, channel):
		if nick.lower() != owner:
			return
		else:
			ret = message[4:]
			return ret
	def dice(self, nick, message, channel):
		return "%s rolls a dice and gets %s" % (nick, random.randrange(1, 6))

	def slap(self, nick, message, channe):
		try:
			inp = message[5:].lower()
		except:
			inp = nick.lower()
		return "beeeeech slaps %s" % inp
		
	def command_patterns(self):
		return(
			self.command("say", self.say),
			self.command("dice", self.dice),
			self.command("slap", self.slap),
		)
		
host = "irc.domain.tld"
port = 6667
nick = "bot"

run_bot(bot, 
	host, 
	port, 
	nick, 
	rooms)
		
