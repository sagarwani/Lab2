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

class ShopServerProtocol(asyncio.Protocol):

    serverstate = 0

    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.transport = None

    def connection_made(self, transport):
        print("Server connection_made is called")
        self.transport = transport

    def data_received(self, data):
        print("Server Data_received is called")

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
        self.transport = transport
        super().__init__(self.transport)

    def write(self, data):
        bytes = data.__serialize__()
        self.protocol.write(bytes)

global window_size
window_size = 0

class PEEPServerProtocol(StackingProtocol):
    serverstate = 0
    clientseq = 0
    serverseq = 0

    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.transport = None

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
                    synack = PEEP()
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
                    print("================= Corrupt ACK packet. Please check on client end.===============\n")
                    self.transport.close()

            # Reset packet received
            elif pkt.Type == 5:
                 print("================ Server received connection close from client. Closing socket.===============\n")



if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    # Each client connection will create a new protocol instance

    Serverfactory = StackingProtocolFactory(lambda: PEEPServerProtocol())
    ptConnector= playground.Connector(protocolStack=Serverfactory)

    playground.setConnector("passthrough",ptConnector)

    coro = playground.getConnector('passthrough').create_playground_server(lambda: ShopServerProtocol(),8888)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
