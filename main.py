from telegram_bot import TelegramBot, Command
from whatsapp_bot import WhatsappBot
from multiprocessing import Pipe 

from os import path, makedirs

if __name__ == "__main__":
    # create config path if it does not exist
    if not path.exists(path.expanduser("~") + "/.config/whattelcopybot"):
        makedirs(path.expanduser("~") + "/.config/whattelcopybot")
    
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
