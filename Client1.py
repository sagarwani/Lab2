import asyncio
import playground
import random, logging
from playground import getConnector
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, UINT16, UINT8, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
from playground.network.common.Protocol import StackingProtocol, StackingProtocolFactory, StackingTransport
import zlib


class RequestToBuy(PacketType):
    DEFINITION_IDENTIFIER = "RequestToBuy"
    DEFINITION_VERSION = "1.0"

    FIELDS = [

             ]

class RequestItem(PacketType):
    DEFINITION_IDENTIFIER = "RequestItem"
    DEFINITION_VERSION = "1.0"

    FIELDS = [

             ]

class SendItem(PacketType):
    DEFINITION_IDENTIFIER = "SendItem"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
            ("Item", STRING),
             ]


class RequestMoney(PacketType):
    DEFINITION_IDENTIFIER = "RequestMoney"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Amount", UINT32)
             ]


class SendMoney(PacketType):
    DEFINITION_IDENTIFIER = "SendMoney"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Cash", UINT32)
             ]

class FinishTransaction(PacketType):
    DEFINITION_IDENTIFIER = "FinishTransaction"
    DEFINITION_VERSION = "1.0"

    FIELDS = [

             ]

class PEEP(PacketType):

    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: True})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", BUFFER({Optional: True}))
]

class ShopClientProtocol(asyncio.Protocol):

    clientstate = 0

    def __init__(self, loop):
        #self.loop = loop
        self.transport = None
        self.loop = loop
        self.deserializer = PacketType.Deserializer()

    def connection_made(self, transport):
        print("ShopClient connection_made is called\n")
        self.transport = transport
        # PACKET 1 - Request to Buy packet
        startbuy = RequestToBuy()
        print("Sending Request to Buy")
        self.transport.write(startbuy.__serialize__())

    def data_received(self, data):
        print("ShopClient Data_received is called")
        self.deserializer.update(data)
        #print(data)
        for pkt in self.deserializer.nextPackets():
            #print("Client <------------{}------------- Server".format(pkt.DEFINITION_IDENTIFIER))

            if isinstance(pkt, RequestItem) and self.clientstate == 0:
                self.clientstate += 1

                # PACKET 3 - Send Item packet
                item = "Butter"
                response = SendItem()
                response.Item = item

                print("Sent SendItem")
                self.transport.write(response.__serialize__())


            elif isinstance(pkt, RequestMoney) and self.clientstate == 1:
                self.clientstate += 1

                # PACKET 5 - Send Money packet
                response = SendMoney()

                response.Cash = pkt.Amount

                print("Sent SendMoney")
                self.transport.write(response.__serialize__())

            elif isinstance(pkt, FinishTransaction) and self.clientstate == 2:

                self.transport.close()

            else:
                print(pkt.Type)
                print("Client Received Incorrect Packet. Closing Connection. Try Again!")
                self.transport.close()


    def connection_lost(self,exc):
        print('\nThe ShopServer sent a connection close to the client')
        self.transport.close()
        self.transport = None
        self.loop.stop()


class PeepClientTransport(StackingTransport):

    def __init__(self,protocol,transport):
        self.protocol = protocol
        self.transport = transport
        self.exc = None
        super().__init__(self.transport)


    def write(self, data):
        print(data)
        self.protocol.write(data)

    def close(self):
        self.protocol.connection_lost(self.exc)


class PEEPClient(StackingProtocol):

    def __init__(self):
        self.transport = None
        self.state = 0

    def calculateChecksum(self, c):
        self.c = c
        self.c.Checksum = 0
        print(self.c)
        checkbytes = self.c.__serialize__()
        return zlib.adler32(checkbytes) & 0xffff

    def checkChecksum(self, instance):
        self.instance = instance
        pullChecksum = self.instance.Checksum
        instance.Checksum = 0
        bytes = self.instance.__serialize__()
        if pullChecksum == zlib.adler32(bytes) & 0xffff :
            return True
        else:
            return False


    def connection_made(self, transport):
        print("========PEEP Client Connection_made CALLED=========\n")
        self.transport = transport
        self.protocol = self

        if self.state == 0:
            packet = PEEP()
            packet.Type = 0
            packet.SequenceNumber = random.randrange(1, 1000, 1)
            packet.Acknowledgement = 0
            self.state += 1
            print("=============== Sending SYN PACKET ==================\n")
            packet.Checksum = self.calculateChecksum(packet)
            packs = packet.__serialize__()
            print("\n ================ Serialized SYN ==============: \n",packs)
            self.transport.write(packs)


    def data_received(self, data):

        print("=============== PEEP Client Data_Received CALLED =============\n")
        self.deserializer = PacketType.Deserializer()
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            checkvalue = self.checkChecksum(packet)
            if self.state == 1 and packet.Type == 1 and checkvalue == True:
                print("\n========================== SYN-ACK Received. Seqno= ", packet.SequenceNumber, " Ackno=", packet.Acknowledgement)

                #Sending ACK

                ack = PEEP()
                ack.Type = 2
                ack.SequenceNumber = packet.Acknowledgement
                ack.Acknowledgement = packet.SequenceNumber + 1
                self.state += 1
                ack.Checksum = self.calculateChecksum(ack)
                clientpacketbytes = ack.__serialize__()
                print ("=================== Sending ACK =================\n")
                self.transport.write(clientpacketbytes)

                peeptransport = PeepClientTransport(self, self.transport)
                self.higherProtocol().connection_made(peeptransport)

            elif packet.Type == 5:

                 print("====================Got Encapasulated Packet and Deserialized==================")

                 print(packet.Data)
                 self.higherProtocol().data_received(packet.Data)

            else:
                print("======== Incorrect packet received. Closing connection!=========\n")
                self.transport.close()


    def write(self,data):
        print ("=================== Writing Data down to wire from Client ================\n")


        Cencap = PEEP()
        calcChecksum = PEEPClient()
        Cencap.Type = 5
        Cencap.Acknowledgement = 5555
        Cencap.SequenceNumber = 3333
        Cencap.Data = data
        #Cencap.Checksum = 0
        Cencap.Checksum = calcChecksum.calculateChecksum(Cencap)

        print(Cencap)
        bytes = Cencap.__serialize__()

        self.transport.write(bytes)

        #self.transport.write(data)

    def connection_lost(self,exc):
        print ("============== PEEPClient Closing connection ===========\n")
        self.transport.close()



class initiate():
    def __init__(self, loop):
        self.loop = loop

    def send_first_packet(self):
        self.loop = loop
        return ShopClientProtocol(loop)

if __name__ == "__main__":

    loop = asyncio.get_event_loop()

    logging.getLogger().setLevel(logging.NOTSET)  # this logs *everything*
    logging.getLogger().addHandler(logging.StreamHandler())  # logs to stderr

    Clientfactory = StackingProtocolFactory(lambda: PEEPClient())
    ptConnector = playground.Connector(protocolStack=Clientfactory)

    playground.setConnector("passthrough", ptConnector)

    go = initiate(loop)
    coro = playground.getConnector('passthrough').create_playground_connection(go.send_first_packet, '20174.1.1.1', 8888)
    loop.run_until_complete(coro)

    loop.run_forever()
    loop.close()
