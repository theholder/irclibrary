rooms = ["room", "roomhere"]

from irc import IRCBot, run_bot
import random

owner = "yournick" # put your irc nick here


def makebold(args):
	return "\x02%s\x0f" % args


class bot(IRCBot):

	def say(self, nick, message, channel):
		ret = message[4:]
		return ret

	def dice(self, nick, message, channel):
		return "%s rolls a dice and gets %s" % (nick, random.randrange(1, 6))

	def slap(self, nick, message, channel):
		try:
			inp = message[5:].lower()
		except:
			inp = nick.lower()
		return "beeeeech slaps %s" % inp
		
	def whoami(self, nick, message, channel):
		return "You are %s silly" % nick

	def help(self, nick, message, channel):
		args = message[5:].lower()
		if len(args) < 1:
			return "Hai %s I'm %s a bot of course... I do amazingly silly things: Commands(%s) : %s" % (nick, makebold(self.conn.nick), makebold(len(self.cl)), ",".join(sorted(self.cl)))
		else:
			return "%s: %s" % (args, makebold(self.getHelpkey(args)))
		
	def command_patterns(self):
		return(
			self.command("say", self.say, "say", "make the bot say something"),
			self.command("dice", self.dice, "dice", "make the bot roll a dice"),
			self.command("slap", self.slap, "slap", "make the bot slap someone"),
			self.command("help", self.help, "help", "get help on commands"),
			self.command("whoami", self.whoami, "whoami", "see who you are of course"),
		)
		
host = "irc.domain.tld"
port = 6667
nick = "bawt"

run_bot(bot, 
	host, 
	port, 
	nick, 
	rooms)
