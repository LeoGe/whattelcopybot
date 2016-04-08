from multiprocessing import Process, Pipe
from os import getpid, urandom
from time import sleep
from enum import Enum
import binascii

from telegram import Updater
from telegram.dispatcher import run_async

id = 0
telegram_conn = 0
whatsapp_to_telegram = dict()

class Command(Enum):
    message = 1
    token = 2
    token_ack = 3

@run_async
def got_telegram(bot, update, **kwargs):
    print(update.message.chat_id)
    telegram_conn.send([Command.message, update.message.chat_id, update.message.text])

    global id
    id = update.message.chat_id

def got_whatsapp(bot, update):
    if id != 0:
        bot.sendMessage(id, text=update)

def get_token(bot, update):
    token = binascii.hexlify(urandom(3)).decode('utf8')

    bot.sendMessage(update.message.chat_id, text="Generated token: "+token)
    telegram_conn.send([Command.token, token])

def start_telegram(conn):
    print("Telegram: " + str(getpid()))
    global telegram_conn
    telegram_conn = conn

    updater = Updater("192484269:AAGBW1zGBzlWypp7ApGX-3mtKeE6WVGnPbk")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Message handlers only receive updates that don't contain commands
    dp.addTelegramMessageHandler(got_telegram)

    # got a whatsapp message
    dp.addStringRegexHandler('[^/].*', got_whatsapp)

    dp.addTelegramCommandHandler("token", get_token)

    # All TelegramErrors are caught for you and delivered to the error
    # handler(s). Other types of Errors are not caught.
    #dp.addErrorHandler(error)

    # Start the Bot and store the update Queue, so we can insert updates
    update_queue = updater.start_polling(poll_interval=0.1, timeout=10)

    while True:
        if not conn.poll():
            sleep(0.01)
            continue

        a = conn.recv()
        
        print(a[1])
        
        if a[0] == Command.message:
            update_queue.put(a[1])
        elif a[0] == Command.token_ack:
            whatsapp_to_telegram[a[1]] = a[2]

def start_whatsapp(conn):
    print("Whatsapp: " + str(getpid()))
    
    while True:
        if conn.poll():
            # got a message from telegram
            print(conn.recv())

        conn.send([1000, "Test"])
        sleep(2)

if __name__==  "__main__":
    conn1, conn2 = Pipe()

    telegramProcess = Process(target=start_telegram, args=(conn2,))
    whatsappProcess = Process(target=start_whatsapp, args=(conn1,))
    
    # start both event loops
    telegramProcess.start()
    whatsappProcess.start()

    telegramProcess.join()
    whatsappProcess.join()
