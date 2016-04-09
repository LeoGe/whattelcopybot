from multiprocessing import Process, Pipe
from os import getpid, urandom, path
from time import sleep
from enum import Enum
import binascii, json, signal, sys

from telegram.ext import Updater
from telegram.ext.dispatcher import run_async

class Command(Enum):
    message = 1
    token = 2
    token_ack = 3
    shutdown = 4

class TelegramBot(Process):
    
    SAVEPATH = "./telegram"
    
    def __init__(self, conn):
        self.connection=conn
        super(TelegramBot, self).__init__()

        self.telegram_to_whatsapp=dict()

    def save_to_file(self, signum, frame):
        with open(TelegramBot.SAVEPATH, 'w+') as f:
            f.write(json.dumps(self.telegram_to_whatsapp))
            f.truncate()
        
        sys.exit(0)

    def load_from_file(self):
        if path.isfile(TelegramBot.SAVEPATH):
            with open(TelegramBot.SAVEPATH) as f:
                read=f.read()
                if read!="":
                    self.telegram_to_whatsapp = json.loads(read)
                    print(self.telegram_to_whatsapp)

    def got_whatsapp(self, bot, msg):
        print("Hallo")
        telegram_id, content = msg.split(",")
        bot.sendMessage(int(telegram_id), text=content)

    def got_telegram(self,bot,update):
        if str(update.message.chat_id) in self.telegram_to_whatsapp:
            whatsapp_id=self.telegram_to_whatsapp[str(update.message.chat_id)]
            self.connection.send([Command.message, whatsapp_id, update.message.from_user.first_name+ ": " + update.message.text])

    def get_token(self, bot, update):
        token = binascii.hexlify(urandom(3)).decode('utf8')

        bot.sendMessage(update.message.chat_id, text="Generated token: "+token)
        self.connection.send([Command.token, token, update.message.chat_id])

    def run(self):
        print("Start TelegramBot with PID: " + str(getpid()))
        
        updater = Updater()

        # Get the dispatcher to register handlers
        dp = updater.dispatcher
        
        # Message handlers only receive updates that don't contain commands
        dp.addTelegramMessageHandler(self.got_telegram)
        
        # got a whatsapp message
        dp.addStringRegexHandler('[^/].*', self.got_whatsapp)
        
        dp.addTelegramCommandHandler("token", self.get_token)
        
        # All TelegramErrors are caught for you and delivered to the error
        # handler(s). Other types of Errors are not caught.
        #dp.addErrorHandler(error)
        
        # Start the Bot and store the update Queue, so we can insert updates
        update_queue = updater.start_polling(poll_interval=0.1, timeout=10)
        
        signal.signal(signal.SIGINT, self.save_to_file)
        signal.signal(signal.SIGTERM, self.save_to_file)

        self.load_from_file()

        isRunning = True

        while isRunning:
            if not self.connection.poll():
                sleep(0.01)
                continue
        
            msg = self.connection.recv()
            
            print(msg)
            
            if msg[0] == Command.message:
                update_queue.put(str(msg[1])+","+str(msg[2]))
            elif msg[0] == Command.token_ack:
                self.telegram_to_whatsapp[str(msg[2])] = msg[1]
            elif msg[0] == Command.shutdown:
                print("SHUTDOWN")
                isRunning = False

        print("Shutdown Telegram")

