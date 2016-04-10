from yowsup.layers                             import YowParallelLayer
from yowsup.layers.auth                        import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_messages           import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts           import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks               import YowAckProtocolLayer
from yowsup.layers.network                     import YowNetworkLayer
from yowsup.layers.coder                       import YowCoderLayer
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.layers import EventCallback
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS
from yowsup.layers.axolotl                     import YowAxolotlLayer

import sys

from multiprocessing import Process
from os import getpid, path
import asyncore, socket, json, signal

import logging
logging.basicConfig()

from telegram_bot import Command

class EchoLayer(YowInterfaceLayer):
    def init(self, conn):
        self.connection = conn
	self.tokens = dict()
	self.whatsapp_to_telegram = dict()

    # is called when a telegram message arrives
    @EventCallback("got_telegram")
    def onCallback(self, layerEvent):
        msg = self.connection.recv()
	if msg[0]==Command.token:
		self.tokens[msg[1]] = msg[2]
	elif msg[0]==Command.message:
		msg = TextMessageProtocolEntity(msg[2].encode('ascii',errors='ignore'), to = msg[1])
        	self.toLower(msg)
	elif msg[0] == Command.delete:
		del self.whatsapp_to_telegram[msg[1]]

    # is called when the WhatsappBot shutting down
    @EventCallback("nighttime")
    def onNightTime(self, layerEvent):
    	with open(WhatsappBot.SAVEPATH, 'w+') as f:
            f.write(json.dumps(self.whatsapp_to_telegram))
	    f.truncate()

    # is called when the WhatsappBot starts
    @EventCallback("daytime")
    def onDayTime(self, layerEvent):
        if path.isfile(WhatsappBot.SAVEPATH):
            with open(WhatsappBot.SAVEPATH) as f:
                read=f.read()
	        if read!="":
		    self.whatsapp_to_telegram = json.loads(read)

    # is called a Whatsapp message arrives
    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        print("message from whatsapp from " + messageProtocolEntity.getNotify() + " : " + messageProtocolEntity.getBody())
        if messageProtocolEntity.getBody() in self.tokens:
                self.connection.send([Command.token_ack, messageProtocolEntity.getFrom(), self.tokens[messageProtocolEntity.getBody()]])
		self.whatsapp_to_telegram[messageProtocolEntity.getFrom()] = self.tokens[messageProtocolEntity.getBody()]
	elif messageProtocolEntity.getFrom() in self.whatsapp_to_telegram:
		telegram_ID=self.whatsapp_to_telegram[messageProtocolEntity.getFrom()]
		self.connection.send([Command.message,telegram_ID,messageProtocolEntity.getNotify() + ": " + messageProtocolEntity.getBody()])

    
    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

# inject a event into the yowsup stack when a message from Telegram arrives
class Communication(asyncore.dispatcher):
    def __init__(self, conn, stack):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection = conn
        self.stack = stack

    def handle_close(self):
        pass

    def handle_connect(self):
        pass
        
    def handle_read(self):
        pass
    
    def readable(self):
        if self.connection.poll():
            self.stack.broadcastEvent(YowLayerEvent("got_telegram"))

        return True

class WhatsappBot(Process):
    CREDENTIALS = ("<CREDENTIALS-HERE>")
    SAVEPATH = path.expanduser("~") + "/.config/whattelcopybot/whatsapp"

    def __init__(self,conn):
        self.connection=conn
        super(WhatsappBot,self).__init__()
        
    # injects an event into yowsup to save our file
    def save_to_file(self, signum, frame):
	self.stack.broadcastEvent(YowLayerEvent("nighttime"))
        sys.exit(0)

    def run(self):
        print("Start WhatsappBot with PID: " + str(getpid()))

        layers = (
            EchoLayer,
            YowParallelLayer([YowAuthenticationProtocolLayer, YowMessagesProtocolLayer, YowReceiptProtocolLayer, YowAckProtocolLayer]),YowAxolotlLayer
        ) + YOWSUP_CORE_LAYERS
        
        self.stack = YowStack(layers, self.connection)
        self.stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, WhatsappBot.CREDENTIALS)         #setting credentials
        self.stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])    #whatsapp server address
        self.stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)              
        #self.stack.setProp(YowCoderLayer.PROP_RESOURCE, YowsupEnv.getCurrent())          #info about us as WhatsApp client
       
        # initialize the EchoStack with our connection to Telegram
        echoLayer = self.stack.getLayer(-1)
        echoLayer.init(self.connection)

        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))   #sending the connect signal
	
        # inject an event into yowsup to load our file
        self.stack.broadcastEvent(YowLayerEvent("daytime"))

        # create our dummy stream handler
        Communication(self.connection, self.stack)
	
	# save our hashmap when the TelegramBot is terminated
        signal.signal(signal.SIGINT, self.save_to_file)
        signal.signal(signal.SIGTERM, self.save_to_file)

        # this is the WhatsappBot main loop
	self.stack.loop()

