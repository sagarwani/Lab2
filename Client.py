import playground
import asyncio
import playground
import sys
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT8, UINT16, UINT32, BUFFER, STRING
from asyncio.protocols import Protocol
from playground.asyncio_lib.testing import TestLoopEx
from playground.network.testing import MockTransportToStorageStream
from playground.network.testing import MockTransportToProtocol
import random
from playground.network.packet.fieldtypes.attributes import Optional

global state
state = 0

class PEEPPacket(PacketType):
    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [

        ("Type", UINT8),

        ("SequenceNumber", (UINT32({Optional:True}))),
        ("Checksum", UINT16),

        ("Acknowledgement", UINT32({Optional: True})),

        ("Data", BUFFER({Optional: True}))
    ]


class Client(Protocol):

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport


    def data_received(self, data):
        Clientpacket = PEEPPacket()
        self.deserializer = PacketType.Deserializer()
        self.deserializer.update(data)


        for packet in self.deserializer.nextPackets():
            if state == 0:
                print ("==== SYN ====")
                Clientpacket.Type = 0
                Clientpacket.SequenceNumber = random.randrange(1,1000,1)
                Clientpacket.Acknowledgement = 0
                state = 1
                clientpacketbytes = packet.__serialize__()
                self.transport.write(clientpacketbytes)

            if state == 1 and packet.Type == 1:
                print ("==== ACK ====")
                Clientpacket.Type = 2
                Clientpacket.SequenceNumber = packet.Acknowledgement
                Clientpacket.Acknowledgement = packet.SequenceNumber + 1
                state = 2
                clientpacketbytes = packet.__serialize__()
                self.transport.write(clientpacketbytes)

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.set_debug(enabled=True)
    client = Client()
    coro = playground.getConnector().create_playground_connection(control.buildProtocol, '20174.1.1.1', 101)
    transport, protocol = loop.run_until_complete(coro)
    client.connection_made(transport)
    loop.run_forever()
    loop.close()
