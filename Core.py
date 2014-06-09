# Malay Keshav, Rahul Upadhyaya and Khushal Sagar

from twisted.internet import reactor, protocol
import Messages
import urllib
import logging as Logger
from bitstring import BitArray
import time
import struct
from Constants import *
import time

class BitTorrenter(protocol.Protocol):
	def __init__(self, torrent):
		self.torrent 			= torrent
		self.pending_requests 	= 0
		self.interested 		= False
		self.peer_interested 	= False
		self.choked 			= True
		self.peer_choked 		= True
		self.buffer 			= ""
		self.set_of_blocks_requested = set()
		self.peer_has_pieces 	= BitArray(torrent.fileManager.no_of_pieces)
		self.set_of_blocks_received = set()

	def connectionMade(self):
		self.transport.write(self.torrent.handshake_message)
		
		self.factory 			= self.transport.connector.factory
		self.ip 				= self.transport.connector.host
		self.port 				= self.transport.connector.port
		Logger.info(str("Connection Made with " + str(self.ip) + ", " + str(self.port)))

	def dataReceived(self, data):
		data = self.handleData(data)
		while(data != None):
			if(data[1:20].lower() == "bittorrent protocol"): 
				# The message is a Handshake Message
				self.parseHandshake(data)
			else:
				self.parseNonHandshakeMessage(data)
			if(self.canSendRequest()):
				self.generate_next_request()	#Send Request for next block
			# Get Next Message in Queue
			if(self.torrent.fileManager.bytesWritten != 0):
				Logger.info("File Size Remaining: " + str((self.torrent.fileManager.file_to_stream_length - self.torrent.fileManager.bytesWritten)/1024) + " kilobytes")
				Logger.info("Efficiency: " + str((self.torrent.fileManager.bytesWritten*100)/self.torrent.requester.total_data_received) + "%")
				Logger.info("Speed: " + str(self.torrent.fileManager.bytesWritten/((time.time()-self.torrent.start_time)*1024)) + " kilobytes/second")
			data = self.handleData()

	# Handles the newly received Data. It appends the data to the buffer and returns the next message in Queue. The Returned message should be parsed based on its type
	def handleData(self, data = ""):
		self.buffer += data
		message = ""
		if(self.buffer[1:20].lower() == "bittorrent protocol"): 
			message += self.buffer[:68]
			self.buffer = self.buffer[68:]
			return message
		message_length = Messages.bytes_to_number(self.buffer[:4]) + 4
		if(len(self.buffer) >= message_length):
			message = self.buffer[:message_length]
			self.buffer = self.buffer[message_length:]
			return message
		return None


	def parseHandshake(self, data=""):
		# If the Info Hash matches the torrent's info hash, add the peer to the successful handshake set
		handshake_response_data = Messages.Handshake(data)
		handshake_info_hash 	= handshake_response_data.info_hash
		if handshake_info_hash == urllib.unquote(self.torrent.payload['info_hash']):
			self.factory.peers_handshaken.add((self.ip, self.port))
			self.transport.write(str(Messages.Interested()))
			self.buffer += data[68:]
			self.transport.write(str(Messages.Bitfield(bitfield=self.torrent.fileManager.pieces_status.tobytes())))
		else :
			self.killPeer()
		return


	def killPeer(self):
		if (self.ip, self.port) in self.factory.peers_found:
			self.factory.peers_handshaken.remove((self.ip, self.port))
		self.transport.loseConnection()

	def parseNonHandshakeMessage(self, data):
		bytestring = data
		if (bytestring[0:4] == '\x00\x00\x00\x00'): 
			# Its a Keep Alive message #
			message_obj = Messages.KeepAlive(response=bytestring)
		else:
			message_obj  = {
			  0: lambda: Messages.Choke(response=bytestring),
			  1: lambda: Messages.Unchoke(response=bytestring),
			  2: lambda: Messages.Interested(response=bytestring),
			  3: lambda: Messages.Interested(response=bytestring),
			  4: lambda: Messages.Have(response=bytestring),
			  5: lambda: Messages.Bitfield(response=bytestring),
			  6: lambda: Messages.Request(response=bytestring),
			  7: lambda: Messages.Piece(response=bytestring),
			  8: lambda: Messages.Cancel(response=bytestring),
			  9: lambda: Messages.Port(response=bytestring),
            }[    struct.unpack('!b',data[4])[0]   ]()     # The 5th byte in 'data' is the message type/id 
		self.process_message(message_obj)

	def canSendRequest(self):
		if self.interested and not self.choked and self.pending_requests<=5:
			return True
		return False

	def process_message(self, message_obj):
		fmt = 'Peer : {:16s} || {:35s}'
		if isinstance(message_obj, Messages.Choke):
			Logger.info(fmt.format(str(self.ip) , "Choke"))
			self.choked = True
		elif isinstance(message_obj, Messages.Unchoke):
			Logger.info(fmt.format(str(self.ip) , "UnChoke"))
			self.choked = False
		elif isinstance(message_obj, Messages.Interested):
			Logger.info(fmt.format(str(self.ip) , "Interested"))
			self.peer_interested = True
		elif isinstance(message_obj, Messages.NotInterested):  
			Logger.info(fmt.format(str(self.ip) , "Not Interested"))
			self.peer_interested = False
		elif isinstance(message_obj, Messages.Have):
			piece_index = Messages.bytes_to_number(message_obj.index)
			self.torrent.requester.havePiece(self, piece_index)
			Logger.info(fmt.format(str(self.ip) , "Has Piece Index :" + str(piece_index)))
			ret = self.torrent.fileManager.checkBounds(piece_index,0)
			if ret != 2:
				self.interested = True;
				if self.peer_choked == True:
					self.transport.write(str(Messages.Unchoke()))
				self.peer_choked = False
			self.peer_has_pieces[piece_index] = 1
		elif isinstance(message_obj, Messages.Bitfield):
			Logger.info(str("Peer :") + str(self.ip) + " || " + "Bitfield")
			self.torrent.requester.haveBitfield(self,message_obj.bitfield)
			bitarray = BitArray(bytes=message_obj.bitfield)
			self.peer_has_pieces = bitarray[:len(self.peer_has_pieces)]
			flag = False
			for i in range(self.torrent.fileManager.start_piece_id,len(message_obj.bitfield)):
				ret = self.torrent.fileManager.checkBounds(i,0)
				if ret != 2:
					if message_obj.bitfield[i] == True:
						flag = True
						break
				else:
					break
			if flag == True:
				self.interested = True
				self.transport.write(str(Messages.Unchoke()))
				self.peer_choked = False
		elif isinstance(message_obj, Messages.Request):
			Logger.info(fmt.format(str(self.ip) , "Request"))
			if self.peer_choked == False:
				answer_request(message_obj.index,message_obj.begin,message_obj.length)
		elif isinstance(message_obj, Messages.Piece):
			self.pending_requests -= 1
			piece_index = Messages.bytes_to_number(message_obj.index)
			block_byte_offset = Messages.bytes_to_number(message_obj.begin)
			block_index = block_byte_offset/BLOCK_SIZE
			Logger.info(fmt.format(str(self.ip) , str(piece_index) + "," + str(block_index) + " :: Recevied Data Piece!!! !:D :D :D"))
			self.torrent.requester.updateTotalDataReceived(len(message_obj.block))
			if((piece_index,block_index) in self.set_of_blocks_requested):
				self.set_of_blocks_requested.remove((piece_index,block_index))
			self.set_of_blocks_received.add((piece_index,block_index))
			#Change the following line as per the function name used in FileManager.

			message_obj.index = Messages.bytes_to_number(message_obj.index)
			message_obj.begin = Messages.bytes_to_number(message_obj.begin)

			self.writeData(message_obj.index, message_obj.begin, message_obj.block)

			Logger.info("Received || Total Current Requests :" + str(self.torrent.requester.total_requests))
			Logger.info("Received || Wasted Requests:" + str(self.torrent.requester.total_requests_wasted))
			Logger.info("Received || Cancelled Requests:" + str(self.torrent.requester.total_requests_cancelled))
			Logger.info("Received || Requests Used:" + str(self.torrent.requester.total_requests_used))
			Logger.info("Received || Total Requests Sent:" + str(self.torrent.requester.total_requests_sent))

			# assert self.torrent.requester.total_requests_sent == self.torrent.requester.total_requests_wasted + self.torrent.requester.total_requests_cancelled + self.torrent.requester.total_requests_used, "Chutiyapa in count of requests wasted and Cancelled"

		elif isinstance(message_obj, Messages.Cancel):
			Logger.info(fmt.format(str(self.ip) , "Cancelled Request :\\"))
		elif isinstance(message_obj, Messages.Port):
			Logger.info(fmt.format(str(self.ip) , "Natalie Portman ? :D"))
	
	def generate_next_request(self):
		while True:
			#Ask the Requests Manager for new Blocks to request
			piece_index,block_index = self.torrent.requester.get_next_block(self)
			if block_index < 0 or len(self.set_of_blocks_requested) >= MAX_REQUEST_TO_PEER:
				if self.torrent.fileManager.StreamCompleted == True:
					reactor.stop()
				else:
					break
			block_byte_offset = block_index*BLOCK_SIZE
			#Add this to the set of blocks requested.
			self.set_of_blocks_requested.add((piece_index,block_index))

			self.transport.write(str(Messages.Request(
				index = Messages.number_to_bytes(piece_index), 
				begin = Messages.number_to_bytes(block_byte_offset), 
				length = Messages.number_to_bytes(BLOCK_SIZE))))
			self.torrent.requester.requestSuccessful(self, piece_index,block_index)
			#Add timeout for requests.
			Logger.info("Sending Request For Piece :" + str(Messages.number_to_bytes(piece_index)) + " to " + str(self.ip))
			reactor.callLater(TIMEOUT,self.checkTimeout,piece_index,block_index)

	def checkTimeout(self, piece_index, block_index):
		#Called after the expected time of receiving a (piece,block).Checks the set of pending requests to determine if retransmission is needed or not.
		if (piece_index,block_index) in self.set_of_blocks_requested:
			self.torrent.requester.removeRequest(self,piece_index, block_index)

	def writeData(self, piece_index, begin, data):
		if(begin%BLOCK_SIZE != 0):
			#The beginning of data is in the middle of a block. Discard this data since we are going to request data in blocks anyway
			data = data[((math.ceil(float(begin)/float(BLOCK_SIZE))*BLOCK_SIZE) - begin):]
			begin += (math.ceil(float(begin)/float(BLOCK_SIZE))*BLOCK_SIZE) - begin
		block_index = int(begin/BLOCK_SIZE)
		while(data != ""):
			if(len(data) >= BLOCK_SIZE):
				if(self.torrent.fileManager.blockExists(piece_index,block_index) == True):
					self.torrent.requester.total_requests_wasted += 1
					self.torrent.requester.cancelRemainingRequests(piece_index,block_index)
				else:
					self.torrent.fileManager.writeToFile(piece_index,block_index, data)
					self.torrent.requester.total_requests_used += 1
					self.torrent.requester.removeRequest(self,piece_index,block_index)
					if(self.torrent.fileManager.blockExists(piece_index,block_index) == True):
						self.torrent.requester.cancelRemainingRequests(piece_index,block_index)
				data = data[BLOCK_SIZE:]
				piece_index,block_index = self.torrent.fileManager.incrementPieceBlock(piece_index, block_index)
			else:
				break

	def answer_request(self, piece_index, begin, length):
		data = ""
		remaining_length = length
		while(remaining_length>0):
			block_index = int(begin/BLOCK_SIZE)
			if(self.torrent.fileManager.blockExists(piece_index,block_index)):	#block_exists indicates if block is present
				if(remaining_length >= BLOCK_SIZE):
					data = self.torrent.fileManager.readBlock(piece_index,block_index)[begin%BLOCK_SIZE:]	#readBlock returns the data block
					begin = math.ceil(begin/BLOCK_SIZE)*ConstantsBLOCK_SIZE
					remaining_length -= BLOCK_SIZE-begin%BLOCK_SIZE
				else:
					data = self.torrent.fileManager.readBlock(piece_index,block_index)[begin%BLOCK_SIZE:remaining_length]
					remaining_length = 0
				self.transport.write(str(Messages.Piece(
				index = Messages.number_to_bytes(piece_index), 
				begin = Messages.number_to_bytes(begin), 
				block = data)))	#send corresponding data block
				if(begin == self.torrent.fileManager.get_piece_length(piece_index)):	#get piece length for corresponding piece index
					piece_index += 1
					begin = 0

	def cancelRequestFor(self,piece_index,block_index):
		if((piece_index,block_index) in self.set_of_blocks_requested):
			self.set_of_blocks_requested.remove((piece_index,block_index))
		begin = block_index*BLOCK_SIZE
		piece_index = Messages.number_to_bytes(piece_index)
		begin = Messages.number_to_bytes(block_index)
		length = Messages.number_to_bytes(BLOCK_SIZE)
		self.transport.write(str(Messages.Cancel(index = piece_index, begin = begin, length = length)))

# Each torrent has its own Factory. And only one factory
class BitTorrentFactory(protocol.ClientFactory): 
	def __init__(self, torrent):
		self.torrent = torrent
		self.peers_found = dict()
		self.peers_handshaken = set()
		self.inQueue	= set()

	def numberOfConnectedPeers(self):
		return len(self.peers_found)

	# Has Been Added To the Reactor Queue
	def addToQueue(self, peer_ip, peer_port):
		self.inQueue.add((peer_ip, peer_port))

	# Check if Already in the Reactor Queue or Not
	def isInQueue(self, peer_ip, peer_port):
		if (peer_ip, peer_port) in self.inQueue:
			return True
		return False

	def removeFromQueue(self, peer_ip, peer_port):
		self.inQueue.remove((peer_ip, peer_port))

	# To check if there is already a discovered peer  with the Peer having ip : peer_ip and port : peer_port
	def hasPeer(self, peer_ip, peer_port):
		if (peer_ip, peer_port) in self.peers_found:
			return True
		return False

	def buildProtocol(self, addr):
		peer = BitTorrenter(self.torrent) # Protocol is named as 'peer'

		# Add The peer to the set of discovered Peers
		# Make Sure the Peers for which the Protocol is being built, is not already added
		# This Check needs to be done before the reactor.connectToTCP() is called
		self.peers_found[(addr.host, addr.port)] = peer

		# Remove from the Queue as it has not been processed
		self.removeFromQueue(addr.host, addr.port)
		return peer

	def clientConnectionFailed(self, connector, reason): 
		Logger.info(str("Connection failed REASON :" + str(reason)))

		# reactor.stop()
	def clientConnectionLost(self, connector, reason): 
		try:
			del self.peers_found[(connector.host, connector.port)]
		except Exception, e:
			Logger.info("ERROR DELETING PEER FROM THE FACTORY DICTIONARY!")
		Logger.info("Connection lost.")
