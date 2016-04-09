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
#from yowsup import env
#from yowsup.env import YowsupEnv
import sys
from yowsup.common.tools import Jid

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
    
    @EventCallback("got_telegram")
    def onCallback(self, layerEvent):
        msg = self.connection.recv()
        print(msg)
	if msg[0]==Command.token:
		self.tokens[msg[1]] = msg[2]
	elif msg[0]==Command.message:
		msg = TextMessageProtocolEntity(msg[2].encode('ascii',errors='ignore'), to = msg[1])#'491778808907-1457090836@g.us')
        	self.toLower(msg)

    @EventCallback("nighttime")
    def onNightTime(self, layerEvent):
    	with open(WhatsappBot.SAVEPATH, 'w+') as f:
            f.write(json.dumps(self.whatsapp_to_telegram))
	    f.truncate()

    @EventCallback("daytime")
    def onDayTime(self, layerEvent):
        if path.isfile(WhatsappBot.SAVEPATH):
            with open(WhatsappBot.SAVEPATH) as f:
                read=f.read()
	        if read!="":
		    self.whatsapp_to_telegram = json.loads(read)

        print("loaded")

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
	print(messageProtocolEntity)
        print(self.whatsapp_to_telegram)
        if messageProtocolEntity.getBody() in self.tokens:
		self.connection.send([Command.token_ack, messageProtocolEntity.getFrom(), self.tokens[messageProtocolEntity.getBody()]])
		self.whatsapp_to_telegram[messageProtocolEntity.getFrom()] = self.tokens[messageProtocolEntity.getBody()]
	elif messageProtocolEntity.getFrom() in self.whatsapp_to_telegram:
		telegram_ID=self.whatsapp_to_telegram[messageProtocolEntity.getFrom()]
		self.connection.send([Command.message,telegram_ID,messageProtocolEntity.getParticipant().split('@')[0] + ": " + messageProtocolEntity.getBody()])

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

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
    CREDENTIALS = () # replace with your phone and password
    SAVEPATH = "./whatsapp"

    def __init__(self,conn):
        self.connection=conn
        super(WhatsappBot,self).__init__()
        

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
       
        echoLayer = self.stack.getLayer(-1)
        echoLayer.init(self.connection)

        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))   #sending the connect signal
	self.stack.broadcastEvent(YowLayerEvent("daytime"))

        Communication(self.connection, self.stack)
	
	signal.signal(signal.SIGINT, self.save_to_file)
        signal.signal(signal.SIGTERM, self.save_to_file)

	#try:
	self.stack.loop() #this is the program mainloop
	#except Exception as e:
	##	print e
