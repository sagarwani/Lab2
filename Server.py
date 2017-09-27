class PEEPServerProtocol(asyncio.Protocol):
    serverstate = 0
    clientseq = 0
    serverseq = 0

    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.transport = None

    def tcp_checksum(instance):
        # instead of concat 16-bit words, we use data that is a multiple of 16
        # (i.e. 576, the whole segment)
        all_text = str(instance.type) + str(instance.sequenceNumber) + str(instance.acknowledgement) + instance.data
        sum = 0
        for i in range((0), len(all_text) - 1, 2):
            # get unicode/byte values of operands
            first_operand = ord(all_text[i])
            second_operand = ord(all_text[i + 1]) << 8

            # add
            current_sum = first_operand + second_operand

            # add and wrap around
            sum = ((sum + current_sum) & 0xffff) + ((sum + current_sum) >> 16)
        return sum

    def connection_made(self, transport):
        print("PEEP Server connection_made is called")
        self.transport = transport
        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        print("PEEP Server data_received is called")
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            # CheckSUM Check
            # SYN from client
            if pkt.type == 0 and self.serverstate == 0:
                self.serverstate += 1
                self.clientseq = pkt.sequencenumber
                if(pkt.checksum == self.tcp_checksum(pkt)):
                    synack = PEEP()
                    synack.type = 1
                    synack.acknowledgement = pkt.sequencenumber + 1
                    synack.sequencenumber = random.randint(5000, 9999)
                    self.serverseq = synack.sequencenumber
                    synack.checksum = self.tcp_checksum(synack)
                    self.transport.write(synack.__serialize__())
                else:
                    print("Checksum error. Packet data corrupt.")
            elif pkt.type == 2 and self.serverstate == 1 and pkt.sequencenumber == self.clientseq + 1 and pkt.acknowledgement == self.serverseq + 1:
                # Data transmission can start
                self.serverstate += 1
                if(pkt.checksum == self.tcp_checksum(pkt)):
                    print("TCP Connection successfull. Client OK to send the data now.")
                else:
                    print("Corrupt ACK packet. Please check on client end.")
                self.higherProtocol().data_received(data)
            # Reset packet received
            elif pkt.Type == 5:
                print("Server received connection close from client. Closing socket.")
                self.transport.close()
