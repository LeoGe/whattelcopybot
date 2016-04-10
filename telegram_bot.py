from multiprocessing import Process, Pipe
from os import getpid, urandom, path
from time import sleep
from enum import Enum
import binascii, json, signal, sys
from random import randint

from telegram.ext import Updater
from telegram.ext.dispatcher import run_async
from telegram.update import Update

class Command(Enum):
    message = 1
    token = 2
    token_ack = 3
    delete = 4

class TelegramBot(Process):

    CREDENTIALS = "<CREDENTIALS-HERE>"
    SAVEPATH = path.expanduser("~") + "/.config/whattelcopybot/telegram"
    
    def __init__(self, conn):
        self.connection=conn
        super(TelegramBot, self).__init__()

        self.telegram_to_whatsapp=dict()
        with open("tokens.txt") as f:
            self.poems = f.read().splitlines()
    # save hashmap to file when exit
    def save_to_file(self, signum, frame):
        with open(TelegramBot.SAVEPATH, 'w+') as f:
            f.write(json.dumps(self.telegram_to_whatsapp))
            f.truncate()
        
        sys.exit(0)

    #load hashmap from file (if it exists and is not empty)
    def load_from_file(self):
        if path.isfile(TelegramBot.SAVEPATH):
            with open(TelegramBot.SAVEPATH) as f:
                read=f.read()
                if read!="":
                    self.telegram_to_whatsapp = json.loads(read)

    #send message to Telegram chat
    def got_whatsapp(self, bot, msg):
        if not "," in msg:
            bot.sendMessage(int(msg), "Success: Connected to Whatsapp group!")
        else:
            telegram_id, content = msg.split(",")
            bot.sendMessage(int(telegram_id), text=content)

    # if both groups are connected send message to WhatsappBot
    def got_telegram(self,bot,update):
        if not type(update) is Update or update.message == None:
            return

        if update.message.new_chat_participant!=None:
            if update.message.new_chat_participant.username=="WhattelCopyBot":
                self.help(bot,update)
        elif update.message.left_chat_participant!=None:
            if update.message.left_chat_participant.username=="WhattelCopyBot":
                print("REMOVE")
                if str(update.message.chat_id) in self.telegram_to_whatsapp:
                    self.connection.send([Command.delete, self.telegram_to_whatsapp[str(update.message.chat_id)]])
                    del self.telegram_to_whatsapp[str(update.message.chat_id)]
        elif str(update.message.chat_id) in self.telegram_to_whatsapp:
                whatsapp_id=self.telegram_to_whatsapp[str(update.message.chat_id)]
                self.connection.send([Command.message, whatsapp_id, update.message.from_user.first_name+ ": " + update.message.text])
   
    def help(self,bot,update):
        helpText="Hello Traveller, my name is John Whattel. I will copy all of your messages from whatsapp to telegram and vice versa.\n/token (generate token to connects two chats)\n/delete (disconnects the chats)\n/help (show this notice again)"
        bot.sendMessage(update.message.chat_id,text=helpText)

    # generate token and send it to WhatsappBot and to the Telegram chat
    def get_token(self, bot, update):
        if str(update.message.chat_id) in self.telegram_to_whatsapp:
            bot.sendMessage(update.message.chat_id,text="Sorry, chat is already connected to a Whatsapp group!")
            return

        rand_int = randint(0,len(self.poems))
        while self.poems[rand_int] == "":
            rand_int = randint(0,len(self.poems))

        bot.sendMessage(update.message.chat_id, text="Please paste this token into the Whatsapp chat you want to be connected to. I have to be a member of this chat.")
        bot.sendMessage(update.message.chat_id, text="Generated token: "+self.poems[rand_int])
        self.connection.send([Command.token, self.poems[rand_int], update.message.chat_id])
        self.poems[rand_int]=""

    def delete(self, bot, update):
        if str(update.message.chat_id) in self.telegram_to_whatsapp:
            self.connection.send([Command.delete, self.telegram_to_whatsapp[str(update.message.chat_id)]])
            del self.telegram_to_whatsapp[str(update.message.chat_id)]
            bot.sendMessage(update.message.chat_id, text="Hey there, this chat connecion was deleted")
        else:
            bot.sendMessage(update.message.chat_id, text="Something went terribly wrong :( This chat is not connected")

    def run(self):
        print("Start TelegramBot with PID: " + str(getpid()))
       
        # connect to TelegramBot with CREDENTIALS
        updater = Updater(TelegramBot.CREDENTIALS)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher
        
        # Message handlers only receive updates that don't contain commands
        dp.addTelegramMessageHandler(self.got_telegram)
        
        # got a whatsapp message
        dp.addStringRegexHandler('[^/].*', self.got_whatsapp)
        
        dp.addTelegramCommandHandler("help", self.help)
        dp.addTelegramCommandHandler("token", self.get_token)
        dp.addTelegramCommandHandler("delete", self.delete)

        # All TelegramErrors are caught for you and delivered to the error
        # handler(s). Other types of Errors are not caught.
        #dp.addErrorHandler(error)
        
        # Start the Bot and store the update Queue, so we can insert updates
        update_queue = updater.start_polling(poll_interval=0.1, timeout=10)
       
        # save our hashmap when the TelegramBot is terminated
        signal.signal(signal.SIGINT, self.save_to_file)
        signal.signal(signal.SIGTERM, self.save_to_file)

        # load our hashmap when the TelegramBot is started
        self.load_from_file()

        isRunning = True

        while isRunning:
            msg = self.connection.recv()
            
            if msg[0] == Command.message:
                update_queue.put(str(msg[1])+","+str(msg[2]))
            elif msg[0] == Command.token_ack:
                # connect Telegram ID to Whatsapp ID
                self.telegram_to_whatsapp[str(msg[2])] = msg[1]
                update_queue.put(str(msg[2]))
            elif msg[0] == Command.token:
                print("Error: got wrong message from WhatsappBot")
