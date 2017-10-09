import asyncio
import playground
import random, zlib, logging
from playground import getConnector
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, UINT16, UINT8, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
from playground.network.common.Protocol import StackingProtocol, StackingProtocolFactory, StackingTransport

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

class PEEPpacket(PacketType):

    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: True})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", BUFFER({Optional: True}))
         ]

class ShopServerProtocol(asyncio.Protocol):

    serverstate = 0

    def __init__(self, loop):
        self.deserializer = PacketType.Deserializer()
        self.transport = None
        self.loop = loop

    def connection_made(self, transport):
        print("ShopServer connection_made is called")
        self.transport = transport

    def data_received(self, data):
        print("ShopServer Data_received is called")

        self.deserializer.update(data)
        #print(data)
        for pkt in self.deserializer.nextPackets():
                #print("Client ------------{}---------------> Server".format(pkt.DEFINITION_IDENTIFIER))


                if isinstance(pkt, RequestToBuy) and self.serverstate == 0:
                    self.serverstate += 1

                    # PACKET 2 - Request Item packet
                    response = RequestItem()

                    print("Sent RequestItem")
                    self.transport.write(response.__serialize__())
                    #print(self.serverstate)

                elif isinstance(pkt, SendItem) and self.serverstate == 1:
                    self.serverstate += 1

                    # PACKET 4 - Request Money packet
                    response = RequestMoney()

                    if pkt.Item == "Bread":
                        response.Amount = 4
                    elif pkt.Item == "Butter":
                        response.Amount = 10

                    print("Sent RequestMoney")
                    self.transport.write(response.__serialize__())

                elif isinstance(pkt, SendMoney) and self.serverstate == 2:
                    self.serverstate += 1

                    # PACKET 6 - Finish Transaction packet
                    response = FinishTransaction()

                    print("Sent FinishTransaction")
                    self.transport.write(response.__serialize__())
                    self.transport.close()

                else:
                    print(pkt.Type)
                    print("Server Received Incorrect Packet. Closing Connection. Try Again!")
                    self.transport.close()


    def connection_lost(self,exc):
        print('\nThe ShopClient sent a connection close to the server')
        self.transport.close()
        self.loop.stop()


'''
class PassThrough1(StackingProtocol, StackingTransport):

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        print("Passthrough1 server connection_made called")

        self.transport = transport

        #self.higherProtocol().connection_made(self.transport)
        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        print("Passthrough1 server Data_received called")

        self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        print('Passthrough1 server connection_lost called')
        self.transport = None
'''

class PeepServerTransport(StackingTransport):

    def __init__(self,protocol, transport):
        self.protocol=protocol
        self.exc = None
        self.transport = transport
        super().__init__(self.transport)

    def write(self, data):
        #bytes = data.__serialize__()
        self.protocol.write(data)

    def close(self):
        self.protocol.close()

    def connection_lost(self):
        self.protocol.connection_lost(self.exc)

global window_size
window_size = 0

class PEEPServerProtocol(StackingProtocol):
    serverstate = 0
    clientseq = 0
    serverseq = 0

    def __init__(self, loop):
        self.deserializer = PacketType.Deserializer()
        self.transport = None
        self.loop = loop

    def calculateChecksum(self, instance):
        self.instance = instance
        self.instance.Checksum = 0
        bytes = self.instance.__serialize__()
        return zlib.adler32(bytes) & 0xffff

    def checkChecksum(self, instance):
        self.instance = instance
        pullChecksum = self.instance.Checksum
        self.instance.Checksum = 0
        bytes = self.instance.__serialize__()
        if pullChecksum == zlib.adler32(bytes) & 0xffff:
            return True
        else:
            return False

    def connection_made(self, transport):
        print("\n================== PEEP Server Connection_made Called =========================\n")
        self.transport = transport


    def data_received(self, data):
        print("\n===================== PEEP Server Data_Received called =====================\n")
        self.deserializer.update(data)
        print (data)
        for pkt in self.deserializer.nextPackets():
            # Checksum Check
            # SYN from client
            checkvalue = self.checkChecksum(pkt)
            if pkt.Type == 0 and self.serverstate == 0:
                #window_size += 1
                self.serverstate += 1
                self.clientseq = pkt.SequenceNumber
                if checkvalue == True:
                    print("\n===================== SYN Received. Seq= ", pkt.SequenceNumber, " Ackno=", pkt.Acknowledgement)
                    #Sending SYN
                    print("\n", pkt)
                    synack = PEEPpacket()
                    synack.Type = 1
                    synack.Acknowledgement = pkt.SequenceNumber + 1
                    synack.SequenceNumber = random.randint(5000, 9999)
                    self.serverseq = synack.SequenceNumber
                    synack.Checksum = self.calculateChecksum(synack)
                    print("\n=========================== Sending SYN-ACK ========================\n")
                    print(synack)
                    packs = synack.__serialize__()
                    self.transport.write(packs)


                else:
                    print("Checksum error. Packet Data corrupt.")
                    self.transport.close()

            elif pkt.Type == 2 and self.serverstate == 1 and pkt.SequenceNumber == self.clientseq + 1 and pkt.Acknowledgement == self.serverseq + 1:
                # Data transmission can start
                print("\n======================= ACK Received. Seq no=", pkt.SequenceNumber, " Ack no=", pkt.Acknowledgement)

                self.serverstate += 1
                if checkvalue == True:
                    print("\n================ TCP Connection successful! Client OK to send the Data now.============= \n")

                    # calling higher connection made since we have received the ACK

                    peeptransport = PeepServerTransport(self, self.transport)
                    higherTransport = StackingTransport(peeptransport)
                    self.higherProtocol().connection_made(higherTransport)

                else:
                    print("================= Corrupted ACK packet. Please check on client end.===============\n")
                    self.transport.close()

            # Reset packet received
            elif pkt.Type == 5 :

                 if checkvalue:
                     print("====================Got Encapasulated Packet and Deserialized==================")

                     print(pkt.Data)
                     self.higherProtocol().data_received(pkt.Data)

                 else:
                     print("================= Corrupted Data packet. Please check on client end.===============\n")
                     self.transport.close()

                 #print("================ Server received connection close from client. Closing socket.===============\n")

            elif pkt.Type == 3 and self.serverstate == 2:
                if checkvalue:
                    print("RIP Received from Client. Sending RIP-ACK.")
                    # RIPack
                    ripack = PEEPpacket()
                    self.exc=0
                    self.serverstate += 1
                    ripack.Type = 4
                    ripack.Acknowledgement = pkt.SequenceNumber + 1
                    ripack.SequenceNumber = 5555
                    calcChecksum = PEEPServerProtocol(self.loop)
                    ripack.Checksum = calcChecksum.calculateChecksum(ripack)
                    ripz = ripack.__serialize__()
                    self.transport.write(ripz)
                else:
                    print("Corrupt RIP packet received. Please check on server end.")

            elif pkt.Type == 4 and self.serverstate == 3:
                if checkvalue:
                    self.serverstate += 1
                    print("RIP-ACK Received from Client. Closing down the connection.")
                    self.connection_lost(self.exc)
                else:
                    print("Corrupt RIP-ACK packet received. Please check on server end.")


    def write(self,data):
        print ("=================== Writing Data down to wire from Server ================\n")

        Sencap = PEEPpacket()
        calcChecksum = PEEPServerProtocol(self.loop)
        Sencap.Type = 5
        Sencap.Acknowledgement = 5555
        Sencap.SequenceNumber = 3333
        Sencap.Data = data
        #Sencap.Checksum = 0
        Sencap.Checksum = calcChecksum.calculateChecksum(Sencap)

        print(Sencap)
        bytes = Sencap.__serialize__()

        self.transport.write(bytes)

    def close(self):
        #RIPpacket
        rip = PEEPpacket()
        rip.Type = 3
        rip.Acknowledgement = 0
        rip.SequenceNumber = 6666
        calcChecksum = PEEPServerProtocol(self.loop)
        rip.Checksum = calcChecksum.calculateChecksum(rip)
        ripz = rip.__serialize__()
        self.transport.write(ripz)


    def connection_lost(self,exc):
        print("============== PEEPServer Closing connection ===========\n")
        self.transport.close()
        self.loop.stop()
        self.transport = None



if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    # Each client connection will create a new protocol instance

    logging.getLogger().setLevel(logging.NOTSET)  # this logs *everything*
    logging.getLogger().addHandler(logging.StreamHandler())  # logs to stderr

    Serverfactory = StackingProtocolFactory(lambda: PEEPServerProtocol(loop))
    ptConnector= playground.Connector(protocolStack=Serverfactory)

    playground.setConnector("passthrough",ptConnector)

    coro = playground.getConnector('passthrough').create_playground_server(lambda: ShopServerProtocol(loop),8888)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.close()
