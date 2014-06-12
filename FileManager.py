# Malay Keshav, Rahul Upadhyaya and Khushal Sagar

import os
import logging as Logger
import math
from bitstring import BitArray
import logging as Logger
from Constants import *
import hashlib


class FileManager(object):
	"""
	Class to manage all the blocks and pieces and other Helper Functions
	Also to read and write from the File.
	"""

	def __init__(self, info):
		self.StreamCompleted = False
		self.downloaded 	= 0
		self.uploaded		= 0
		self.bytesWritten 	= 0
		Logger.debug("Initializing File Manager")
		self.initPiecesBlocks(info)
		self.files_list = list()
		self.setMarkersForFileToDownload(info)
		self.initHashes(info)
		self.initFile()
		Logger.debug("Initializing File Manager Complete")


	def initHashes(self, info):
		self.piece_hash = list()
		for i in xrange(self.no_of_pieces):
			hh = info['pieces'][i*20:(i*20)+20]
			self.piece_hash.append(hh)

	# Function Reads the File Piece by Piece, matching the SHA1 Hash as given in the .torrent file. 
	# This is done until the first piece that does not match the SHA1 hash is found.
	# The piece_id head pointer and the block_offset head pointer is now set to this point
	# This helps in resuming the file download from the piece where it had been stopped downloading
	def reCheck(self, file_name):
		fin = open(file_name, "rb")
		p_id = 0
		while(True):
			b_id = 0
			b_count = self.getBlockCountFor(p_id)
			piece_data = ""
			while(b_id != b_count):
				data = self.readBlock(p_id, b_id)
				piece_data += data
				b_id += 1
			c_hash = hashlib.sha1(piece_data).digest()
			if c_hash ==self.piece_hash[p_id]:
				for x in xrange(b_count):
					self.updateStatus(p_id, x)
				self.bytesWritten += b_count*BLOCK_SIZE
				p_id+=1
			else :
				break
			if self.checkBounds(p_id, 0) == 2:
				raise "FILE ALREADY DOWNLOADED!"
				self.StreamCompleted = True
				break
		self.uploaded = 0
		self.updateCurrentHeadPosition()





	def initFile(self):
		file_name = self.file_to_stream['name']
		# Check if File Already Exists, If yes, then Read it.
		if os.path.isfile(file_name) == True:
			# File Exists
			print "File Already Exists. Checking For Partial Streaming"
			self.reCheck(file_name)
		else :
			fout = open(file_name, "wb")
			data = BitArray(int(self.file_to_stream_length)*8)
			data = data.tobytes()
			fout.write(data)
			fout.close()

	def initPiecesBlocks(self, info):
		Logger.debug("Initializing properties")
		self.piece_length 	= info['piece length']
		self.total_length 	= self.real_total_length = self.getTotalLength(info)
		self.no_of_blocks 	= int(math.ceil(float(self.piece_length)/float(BLOCK_SIZE)))
		self.no_of_pieces 	= int(math.ceil(float(self.total_length)/float(self.piece_length)))
		self.pieces_status 	= BitArray(self.no_of_pieces)
		self.block_status 	= list()
		self.block_data		= list()
		for x in xrange(self.no_of_pieces-1):
			ll = list()
			for y in xrange( int(math.ceil( float(self.piece_length) / float(BLOCK_SIZE)))):
				ll.append(dict())
			self.block_data.append(ll)
			self.block_status.append(BitArray(self.no_of_blocks))
		self.last_piece_size = self.total_length - self.piece_length*(self.no_of_pieces-1)
		ll = list()
		for x in xrange( int(math.ceil( float(self.last_piece_size) / float(BLOCK_SIZE)) )):
			ll.append(dict())
		self.block_data.append(ll)
		self.block_status.append(BitArray(int(math.ceil(self.last_piece_size/BLOCK_SIZE))))



		# Logger.info("My Bitfield :" + str(Messages.Bitfield(bitfield=self.torrent.pieces_status)))

	def getTotalLength(self, info):
		if('files' in info):
			listofFiles = info['files']
			total = 0
			for files in listofFiles:
				total += files['length']
			return total
		else:
			return info['length']

	# Sets the Starting And Ending Point of the File to Stream. 
	# The Function Sets the start_piece_id and start_block_offset for the file in the start_piece_id
	# Also stores the byte offset inside the block in start_byte_offset
	# Also stores the length of the File to Stream in file_to_stream_length in bytes
	def setMarkersForFileToDownload(self, info):
		Logger.debug("Setting Markers For File to be Downloaded in the Global Byte Array Data")
		if('files' in info):
			Logger.debug("Torrent has Multiple Files")
			# If Multiple Files
			x = 1
			for file_ in info['files']:
				path = ""
				for p in file_['path']:
					path += p
				print x, "||",file_['length'], "||",  path
				x += 1
			print "Enter ID for File To Stream :"
			choice = int(input())
			byteOffset = 0
			x = 1
			for file_ in info['files']:
				if x >= choice:
					self.file_to_stream = file_
					p = ""
					for p in file_['path']:
						path = p
					self.file_to_stream['name'] = path
					break
				byteOffset += file_['length']
				x += 1

			self.real_start_absolute_byte_offset 	= self.start_absolute_byte_offset 	= byteOffset
			self.real_start_piece_id 				= self.start_piece_id 				= int(byteOffset/self.piece_length) 
			self.real_start_block_offset 			= self.start_block_offset 			= int((byteOffset%self.piece_length)/BLOCK_SIZE)
			self.real_start_byte_offset 			= self.start_byte_offset 			= int((byteOffset%self.piece_length)%BLOCK_SIZE)

			self.real_file_to_stream_length 		= self.file_to_stream_length 		= self.file_to_stream['length']
			self.start_diff = 0;

			if(self.real_start_byte_offset > 0):
				self.start_absolute_byte_offset -= self.real_start_byte_offset
				self.file_to_stream_length += self.real_start_byte_offset



			if( ((self.real_start_absolute_byte_offset + self.real_file_to_stream_length)%self.piece_length)%BLOCK_SIZE != 0 ):
				diff = ((self.real_start_absolute_byte_offset + self.real_file_to_stream_length)%self.piece_length)%BLOCK_SIZE
				diff = BLOCK_SIZE - diff
				self.file_to_stream_length += diff
				self.end_byte_offset = diff

			print self.start_piece_id, self.start_block_offset, self.start_byte_offset


		else :
			print "Single File Path :", info['name']
			self.start_piece_id = 0
			self.start_block_offset = 0
			self.start_byte_offset = 0
			self.file_to_stream_length = info['length']
			self.file_to_stream = {'name':info['name'], 'length':info['length'], 'md5sum': info['md5sum']}

		self.current_pos_piece_id = self.start_piece_id
		self.current_block_offset = self.start_block_offset

	# Returns what 'data' to be written at (piece_id, block_id)
	# The same (piece_id, block_id) will have upto MALI_LIMIT data blocks.
	# If atleast two of them are same, then we know that it is not malicious (to a very good extent atleast)
	# Returns -1 to say that two same data blocks found yet
	def shouldWrite(self, piece_id, block_id, data):
		if data not in self.block_data[piece_id][block_id]  :
			self.block_data[piece_id][block_id][data] = 0
		self.block_data[piece_id][block_id][data] += 1
		# A certain Data pair has been formed. Return this data
		if self.block_data[piece_id][block_id][data] > 1 or self.block_data[piece_id][block_id][data] >= MALI_LIMIT :
			return data
		# If none of the data received for the given block do not match and the max limit has been reached then randomly pick any piece
		# This might cause the selection of a malicious data block. 
		# TODO : Get rid of malicious data blocks
		if len(self.block_data[piece_id][block_id]) == MALI_LIMIT:
			self.block_data[piece_id][block_id].popitem()[0]
		# No Match found until now, but the Max Limit has not been reached as well
		return -1


	# Arguments : 
	# 	piece_id 	: The offset of the piece where to write the data 
	# 	block_id 	: The offset of the block inside the piece where to write the data
	# 	data 		: The data to be written
	def writeToFile(self, piece_id, block_id, data):
		# If the block has already been written, then skip
		if self.blockExists(piece_id, block_id) :
			return
		data = self.shouldWrite(piece_id, block_id, data)
		# If the blocks already been added have no commmon data yet
		if data == -1 :
			return

		if piece_id == self.start_piece_id and block_id == self.start_block_offset :
			data = data[self.start_byte_offset:]

		if self.incrementPieceBlock(piece_id, block_id) == (-1, -1):
			data = data[:-self.end_byte_offset]

		Logger.debug(str("Writing to Disk " + str(piece_id) + "," + str(block_id)))
		file_name = self.file_to_stream['name']
		fout = open(file_name, "rb+")
		seek_offset = self.byteOffset(piece_id, block_id) - self.start_absolute_byte_offset
		if(seek_offset < 0 or seek_offset >= self.file_to_stream_length):
			raise "ERROR : The Block being written is out of bounds or is not the file being downloaded"
			return
		fout.seek(seek_offset)
		fout.write(data)
		fout.close()
		self.updateStatus(piece_id, block_id)
		self.bytesWritten += len(data)
		self.downloaded   += len(data)
		self.updateCurrentHeadPosition()

	# Arguments : 
	# 	piece_id 	: The offset of the piece where to read the data from 
	# 	block_id 	: The offset of the block inside the piece where to read the data from
	# Return :
	# 	A bytearray of size 'BLOCK_SIZE' which represents the block at (piece_id, block_id)

	def readBlock(self, piece_id, block_id):
		Logger.info(str("Reading From Disk " + str(piece_id) + "," + str(block_id)))
		file_name = self.file_to_stream['name']
		fin = open(file_name, "rb")
		seek_offset = self.byteOffset(piece_id, block_id) - self.start_absolute_byte_offset
		if(seek_offset < 0 or seek_offset >= self.file_to_stream_length):
			raise "ERROR : The Block that is trying to be read is out of bounds or is not the file being downloaded"
			return
		fin.seek(seek_offset)
		data = bytearray(fin.read(BLOCK_SIZE))
		fin.close()
		self.uploaded += len(data)
		return data

	# Checks to see if the Block has already been written and saved
	def blockExists(self, piece_id, block_id):
		if self.checkBounds(piece_id, block_id) != 0:
			return False
		if(self.block_status[piece_id][block_id] == True):
			return True
		return False

	# Returns the Byte Offser (0 Index) for a given combination of (piece_id, block_id)
	def byteOffset(self, piece_id, block_id):
		ret = 0
		ret += piece_id*self.piece_length
		ret += block_id*BLOCK_SIZE
		return ret

	def getBlockCountFor(self, piece_id):
		if piece_id >= len(self.block_status) or piece_id < 0:
			return -1
		return len(self.block_status[piece_id])

	def getPieceLength(self, piece_id):
		return self.getBlockCountFor(piece_id) * BLOCK_SIZE

	# Update the Status Bits to true, to show we have the given block
	def updateStatus(self, piece_id, block_id):
		self.block_status[piece_id][block_id] = True

		
	# Increment the pair (piece_id, block_id) to the next in interation and return the new (piece_id', block_id')
	# The Function Returns (-1, -1) if the end is reached
	def incrementPieceBlock(self, piece_id, block_id):
		val = self.checkBounds(piece_id, block_id+1)
		if val == 0:
			return (piece_id, block_id+1)
		elif val == 1:
			return (piece_id+1, 0)
		else :
			return (-1, -1)

	def getPieceBlockForByteOffset(self, byteoffset):
		piece_id = int(byteOffset/self.piece_length) 
		block_id = int((byteOffset%self.piece_length)/BLOCK_SIZE)
		return piece_id,block_id

	# Updates the Position of the Head.
	# The Head points to the first unavailable block minus 1 in the entire data.
	# Sets 'StreamCompleted' as True if End of File Reached
	def updateCurrentHeadPosition(self):
		while( self.block_status[self.current_pos_piece_id][self.current_block_offset] == True ):
			(self.current_pos_piece_id, self.current_block_offset) = self.incrementPieceBlock(self.current_pos_piece_id, self.current_block_offset)
			if self.current_pos_piece_id == -1 and self.current_block_offset == -1:
				self.StreamCompleted = True
				return

	# Checks whether (piece_id, block_id) is correct
	# Returns 0 : If all Correct
	# Returns 1 : If piece_id needs to be incremented by 1 and block_id needs to be set to 0
	# Returns 2 : If this is the last block_id and last piece_id of the given File we are streaming
	def checkBounds(self, piece_id, block_id):
		if piece_id >= len(self.block_status):
			return 2
		if(self.getBlockCountFor(piece_id) > block_id):
			seek_offset = self.byteOffset(piece_id, block_id) - self.start_absolute_byte_offset
			if( seek_offset >= self.file_to_stream_length):
				return 2
			else: 
				return 0
		if self.checkBounds(piece_id+1, 0) == 0:
			return 1
		return 2

