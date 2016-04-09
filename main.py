from telegram_bot import TelegramBot, Command
from whatsapp_bot import WhatsappBot
from multiprocessing import Pipe 

if __name__ == "__main__":
    try:
        connT, connW = Pipe()
        teleBot = TelegramBot(connT)
        whatBot = WhatsappBot(connW)
        
        teleBot.start()
        whatBot.start()
        
        teleBot.join()
        whatBot.join()
    except KeyboardInterrupt:
        print("Interrupted by Strg+C")
        #connT.send([Command.shutdown])
        #connW.send([Command.shutdown])
	#teleBot.join()
	#whatBot.join()
