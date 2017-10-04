import asyncio
import playground
import random
import logging
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

    def __init__(self):
        #self.loop = loop
        self.transport = None
        self.deserializer = PacketType.Deserializer()

    def connection_made(self, transport):
        print("Client connection_made is called\n")
        self.transport = transport
        print(self.transport)
        # PACKET 1 - Request to Buy packet
        startbuy = RequestToBuy()
        print("Sending Request to Buy")
        self.transport.write(startbuy)

    def data_received(self, data):
        print("Client Data_received is called")
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


    def connection_lost(self, exc):
        print('\nThe server closed the connection')
        #print('Stop the event loop')
        self.transport.close()
        self.transport = None

'''
class Passthrough1(StackingProtocol, StackingTransport):

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        print("Passthrough1 client connection_made called")
        self.transport = transport

        #self.higherProtocol().connection_made(self.transport)

        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        print("Passthrough1 client Data_received called")

        self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        print('Passthrough1 client connection_lost called')
        self.transport = None

class Passthrough1Transport(StackingTransport):

    def __init__(self,transport):
        #self.protocol=protocol
        self.transport = transport
        super().__init__(self.transport)

    def write(self, data):
        print("Calling Passthrough1 Transport write")
        self.transport.write(data)


'''
class PeepClientTransport(StackingTransport):

    def __init__(self,protocol,transport):
        self.protocol = protocol
        self.transport = transport
        super().__init__(self.transport)


    def write(self, data):
        #print(data)
        print ("calling write")
        #print(self.lowerTransport)
        print("RAW PACKET-DATA")
        print(data)
        bytes = data.__serialize__()
        print (bytes)
        print("LOWER TRANSPORT")
        print(self.lowerTransport())
        self.protocol.write(bytes)
            #print ("I wrote the packet")

    def close(self):
        self.lowerTransport().connection_lost()


class PEEPClient(StackingProtocol):

    def __init__(self):
        print("INIT Passthrough")
        self.transport = None
        self.state = 0

    def calculateChecksum(self, c):
        self.c = c
        self.c.Checksum = 0
        print(self.c)
        bitch = self.c.__serialize__()
        return zlib.adler32(bitch) & 0xffff

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
        print("PEEP Client Connection_made CALLED")
        self.transport = transport
        self.protocol = self
        print("hahahah"+str(self.protocol.transport))
        if self.state == 0:
            packet = PEEP()
            packet.Type = 0
            packet.SequenceNumber = random.randrange(1, 1000, 1)
            packet.Acknowledgement = 0
            # packet.Data = b'test'
            self.state += 1
            dude = self.calculateChecksum(packet)
            #print(dude)
            print("SYN PACKET")
            print(packet)
            packet.Checksum = self.calculateChecksum(packet)
            packs = packet.__serialize__()
            print("Serialized SYN",packs)
            self.transport.write(packs)


    def data_received(self, data):

        print("PEEP Client Data_Received CALLED")
        self.deserializer = PacketType.Deserializer()
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            checkvalue = self.checkChecksum(packet)
            if self.state == 1 and packet.Type == 1 and checkvalue == True:
                print("\nSYN-ACK Received. Seqno=", packet.SequenceNumber, " Ackno=", packet.Acknowledgement)

                #Sending ACK

                ack = PEEP()
                ack.Type = 2
                ack.SequenceNumber = packet.Acknowledgement
                ack.Acknowledgement = packet.SequenceNumber + 1
                self.state += 1
                ack.Checksum = self.calculateChecksum(ack)
                print("ACK")
                print(ack)
                clientpacketbytes = ack.__serialize__()
                print ("sending ack")
                self.transport.write(clientpacketbytes)

                peeptransport = PeepClientTransport(self, self.transport)
                #print("PEEP TRANSPORT")
                #print(peeptransport)
                #print("PEEP-CLIENT TRANSPORT"
                #print(self.transport)

                #higherTransport = StackingTransport(self, self.transport)
                #self.higherProtocol().connection_made(peeptransport)
                self.higherProtocol().connection_made(peeptransport)

            else:
                print ("Calling definition identifier")
                self.transport.write(data)
            #else:
            #    print("Incorrect packet received. Closing connection!")
            #    self.transport.close()

    def connection_lost(self, exc):
        print ("closing connection")


    def write(self,data):
        print("lalalalalalal")
        self.transport.write(data)


class initiate():
    def send_first_packet(self):
        self.loop = loop
        return ShopClientProtocol()

if __name__ == "__main__":

    loop = asyncio.get_event_loop()

    logging.getLogger().setLevel(logging.NOTSET)  # this logs *everything*
    logging.getLogger().addHandler(logging.StreamHandler())  # logs to stderr

    f = StackingProtocolFactory(lambda: PEEPClient())
    ptConnector = playground.Connector(protocolStack=f)

    playground.setConnector("passthrough", ptConnector)

    go = initiate()
    #coro = loop.create_connection(lambda: ShopClientProtocol(),'127.0.0.1', 8888)
    coro = playground.getConnector('passthrough').create_playground_connection(go.send_first_packet, '20174.1.1.1', 8888)
    loop.run_until_complete(coro)

    loop.run_forever()
    loop.close()
