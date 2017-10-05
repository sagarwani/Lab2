from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import STRING,INT, BOOL, UINT32, ListFieldType, UINT8, UINT16, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
import asyncio
from io import StringIO
import playground
from playground.network.common.Protocol import StackingProtocol, StackingTransport, StackingProtocolFactory
import random
import zlib
import sys
from playground.asyncio_lib.testing import TestLoopEx
from playground.network.testing import MockTransportToStorageStream
from playground.network.testing import MockTransportToProtocol
from playground.common import logging as p_logging

#Call Start Message
class startcall(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.start"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ('flag', BOOL)]

#Call Response Packet Class Definition
class response(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.response"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("name", STRING),
               ("available", BOOL),
               ("location", STRING),
               ("ip", STRING),
               ("port", UINT32),
               ("xccpv", INT),
               ("codec", ListFieldType(STRING)),
               ]
#BYE Message to disconnect the call
class bye(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.bye"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("flag", BOOL)
               ]

#Calling INVITE Packet Class Definition
class invite(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.invite"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("name", STRING),
               ('available', BOOL),
               ("location", STRING),
               ("ip", STRING),
               ("port", UINT32),
               ("xccpv", INT),
               ("codec", ListFieldType(STRING)),
               ]
#Session Start Packet Class Definition
class session(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.session"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("callingip", STRING),
               ("callingport", UINT32),
               ("calledip", STRING),
               ("calledport", UINT32),
               ("codec", STRING),
               ("payload", INT)]

# Busy packet calling class
class busy(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.busy"
    DEFINITION_VERSION = "1.0"
    FIELDS = [  ]

#TCP Packet
class PEEPPacket(PacketType):

    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: True})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", BUFFER({Optional: True}))
    ]

# Server Protocol Class
class EchoServerProtocol(asyncio.Protocol):
    name='sequence'; location='sequence'; xccpv='1'; ip='sequence'; port=23; codec=['testlist']; ip1='sequence'; ip2='sequence'; port1=0; port2=0;available=1
    payload = {'G711u':64, 'G729':8, 'G711a':64, 'G722':84, 'OPUS': 124}
    output1 = StringIO
    output2 = StringIO
    lst1 = []
    state=0
    cod=0
    def invite(self, name, location, available, xccpv, ip, port, codec):
        self.name = name
        self.location = location
        self.available = available
        self.xccpv = xccpv
        self.ip = ip
        self.port = port
        self.codec = codec

    def session(self, ip1, port1, ip2, port2, codec, payload):
        self.ip1 = ip1
        self.port1 = port1
        self.ip2 = ip2
        self.port2 = port2
        self.codec = codec
        self.payload = payload

    def __init__(self, loop):
        self.transport = None
        self.invite('Bob', 'California', 1, 1, '10.0.0.1', 65001, ['G711u', 'G729', 'G722', 'OPUS', 'G711a'])
        self.loop = loop
        self._deserializer = PacketType.Deserializer()

    def connection_made(self, transport):
        print("\nEchoServer is now Connected to a Client\n")
        self.transport = transport


    def data_received(self, data):
        self._deserializer.update(data)
        for packet in self._deserializer.nextPackets():
            print("Packet received.", packet.DEFINITION_IDENTIFIER)
            if(packet.DEFINITION_IDENTIFIER == "lab1b.calling.start") and (self.available==1) and self.state==0:
                print('Packet 1 CLIENT -> SERVER: Call start request')
                print('\t\t\t\t ', packet)
                self.state +=1
                inv = invite()
                inv.name = self.name; inv.location = self.location; inv.xccpv = self.xccpv; inv.ip = self.ip; inv.port = self.port; inv.codec = self.codec; inv.available = self.available
                self.output1 = inv.ip
                self.output2 = inv.port
                self.lst1 = inv.codec
                pkbytes = inv.__serialize__()
                self.transport.write(pkbytes)
            elif(packet.DEFINITION_IDENTIFIER == "lab1b.calling.start") and (self.available==0) and self.state==0:
                bus = busy()
                pkbytes = bus.__serialize__()
                self.transport.write(pkbytes)
            elif(packet.DEFINITION_IDENTIFIER=='lab1b.calling.response') and self.state==1:
                print('\nPacket 3 CLIENT -> SERVER: Call response from {}'.format(packet.name))
                print('\t\t\t\t ', packet)
                self.state +=1
                ses = session()
                ses.callingip=self.output1; ses.calledip=packet.ip; ses.callingport = self.output2; ses.calledport = packet.port
                for codec in list(self.lst1):
                    for codec1 in list(packet.codec):
                        if codec==codec1:
                            ses.codec=codec
                            self.cod += 1
                if self.cod==0:
                    print('\nClient does not have supported codecs. Connection will now terminate.')
                else:
                    ses.payload = int(self.payload[ses.codec])
                    pkbytes = ses.__serialize__()
                    self.transport.write(pkbytes)
            elif(packet.DEFINITION_IDENTIFIER=='lab1b.calling.bye') and self.state==2:
                print('\nPacket 5 CLIENT -> SERVER: Call disconnect request from Alice.')
                print('\t\t\t\t ', packet)
                self.transport.close()
                self.loop.stop()
            else:
                print('Incorrect packet received. Please check the protocol on server side.')
                self.transport.close()

class PEEPServerProtocol(StackingProtocol, StackingTransport):
    serverstate = 0
    clientseq = 0
    serverseq = 0

    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.transport = None
        self.length = 10
        self.ack = 0

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
        self.transport = transport
        #higherTransport = StackingTransport(self.transport)
        #self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            checkvalue = self.checkChecksum(pkt)
            # CheckSUM Check
            # SYN from client
            if pkt.Type == 0 and self.serverstate == 0:
                self.serverstate += 1
                self.clientseq = pkt.SequenceNumber
                if checkvalue:
                    print("\nSYN Received. Seq=",pkt.SequenceNumber)
                    synack = PEEPPacket()
                    synack.Type = 1
                    self.length = sys.getsizeof(pkt)
                    synack.Acknowledgement = pkt.SequenceNumber + sys.getsizeof(pkt) + 1
                    self.ack = synack.Acknowledgement
                    synack.SequenceNumber = random.randint(5000, 9999)
                    self.serverseq = synack.SequenceNumber
                    synack.Checksum = self.calculateChecksum(synack)
                    packs = synack.__serialize__()
                    self.transport.write(packs)
                    #peeptransport = PeepServerTransport(self.transport)
                    #peeptransport.write(packs)
                else:
                    print("Checksum error. Packet data corrupt.")
                    self.transport.close()
            elif pkt.Type == 2 and self.serverstate == 1 and pkt.SequenceNumber == self.ack and pkt.Acknowledgement == self.serverseq + self.length + 1:
                # Data transmission can start
                print("\nACK Received. Seqno=",pkt.SequenceNumber," Ackno=",pkt.Acknowledgement)
                self.serverstate += 1
                if checkvalue:
                    print("\nTCP Connection successful. Client OK to send the data now.\n")
                    higherTransport = PeepServerTransport(self, self.transport)
                    self.higherProtocol().connection_made(higherTransport)
                    #self.higherProtocol().data_received(data)

                else:
                    print("Corrupt ACK packet. Please check on client end.")
            # Reset packet received
            elif pkt.Type == 5:
                print("Server received connection close from client. Closing socket.")

class PeepServerTransport(StackingTransport):

    def __init__(self,protocol, transport):
        self.protocol=protocol
        self.transport = transport
        #super().__init__(self.transport)

    def write(self, data):
        print("Calling PEEPServerTransport write")
        self.protocol.write(data)


class PassThrough2(StackingProtocol, StackingTransport):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        print("\nConnection made. Once data is received by PassThrough2, will be sent to higher layer")
        self.transport = transport
        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        print("\nData Received at PassThrough2. Sending it to higher layer.\n")
        self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        self.transport = None
        print("\nPassThrough2 Connection was Lost with Server because: {}".format(exc))
        self.transport.close()


if __name__ == "__main__":

    #p_logging.EnablePresetLogging(p_logging.PRESET_TEST)
    loop = asyncio.get_event_loop()
    #bob = EchoServerProtocol(loop)
    #bob.invite('Bob', 'California', 1, 1, '10.0.0.1', 65001, ['G711u', 'G729', 'G722', 'OPUS', 'G711a'])
    f = StackingProtocolFactory(lambda: PEEPServerProtocol(), lambda: PassThrough2())
    ptConnector = playground.Connector(protocolStack=f)
    playground.setConnector("passthrough", ptConnector)
    #loop.set_debug(enabled=True)
    conn = playground.getConnector('passthrough').create_playground_server(lambda: EchoServerProtocol(loop) , 8888)
    #conn = loop.create_server(lambda: EchoServerProtocol(), port=8000)
    server = loop.run_until_complete(conn)
    print("Echo Server Started at {}".format(server.sockets[0].gethostname()))
    print('\nPress Ctrl+C to terminate the process')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    loop.close()
