## example bot ##

rooms = ["room", "roomhere"]

from irc import IRCBot, run_bot

owner = "theholder" # put your irc nick here

class bot(IRCBot):

	def say(self, nick, message, channel):
		if nick.lower() != owner:
			return
		else:
			ret = message[4:]
			return ret
		
	def command_patterns(self):
		return(
			self.command("say", self.say),
		)
		
host = "irc.domain.tld"
port = 6667
nick = "bot"

run_bot(bot, 
	host, 
	port, 
	nick, 
	rooms)
		
