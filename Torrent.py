# Malay Keshav, Rahul Upadhyaya and Khushal Sagar

import bencoder as Bencoder
import bencode_torrent as bencode
import hashlib
import urllib2
import urllib
import TrackerAnnounce
import socket,struct
import Core
import Messages
import logging as Logger
import math
from bitstring import BitArray
import Constants
import RequestManager
import FileManager
import RequestManager
import time



class Torrent(object):
	"""Object that Stores Torrent"""
	def __init__(self, reactor, peer_id, port, raw_data = None, torrent_dict = None):
		super(Torrent, self).__init__()
		if(raw_data == None and torrent_dict == None):
			Logger.error("Not Enough Information to get Torrent Data.\nCannot Ignore Error. Program will now Terminate")
		elif (torrent_dict == None and raw_data != None):
			torrent_dict = Bencoder.bdecode(raw_data)

		self.started 		= False
		self.reactor 		= reactor
		self.start_time 	= time.time()
		self.comment 		= torrent_dict['comment']
		self.info 			= torrent_dict['info']
		self.announce_list 	= torrent_dict['announce-list']
		self.announce 		= torrent_dict['announce']
		self.peer_id 		= peer_id
		self.port 			= port
		self.payload 		= self.generateBasicPayload()
		self.protocol 		= Core.BitTorrentFactory(self)
		self.fileManager 	= FileManager.FileManager(self.info)
		self.requester 		= RequestManager.RequestManager(self)
		self.payload 		= self.updatePayload()

		# The handhshake message to be sent is constant for a given torrent 
		# str() has been overloaded
		self.handshake_message = str(Messages.Handshake(self.payload['info_hash'], self.payload['peer_id'])) 
		print "Total number of pieces :", len(self.info['pieces'])

	def updatePayload(self):
		peer_id = self.peer_id
		self.payload['left'] 		= urllib2.quote(str(self.getTotalLength()- self.fileManager.bytesWritten), '')
		self.payload['peer_id'] 		= urllib2.quote(str(peer_id), '')
		if self.started == False:
			self.payload['event'] 		= urllib2.quote("2",'')
		else :
			self.payload['event'] 		= urllib2.quote("0",'')
		self.payload['uploaded'] 	= urllib2.quote(str(self.fileManager.uploaded),'')
		self.payload['downloaded'] 	= urllib2.quote(str(self.fileManager.downloaded),'')
		return self.payload


	def generateBasicPayload(self):
		peer_id = self.peer_id
		port 	= self.port
		payload = dict()
		encoded_info_dict 		= str(bencode.encode(self.info))
		hash_obj 				= hashlib.sha1(encoded_info_dict)
		payload['info_hash'] 	= urllib.quote(str(hash_obj.digest()))
		payload['left'] 		= urllib2.quote(str(self.getTotalLength()), '')
		payload['peer_id'] 		= urllib2.quote(str(peer_id), '')
		payload['port']  		= urllib2.quote(str(port),'')
		if self.started == False:
			payload['event'] 		= urllib2.quote("2",'')
		else :
			payload['event'] 		= urllib2.quote("0",'')
		return payload

	def getTotalLength(self):
		if('files' in self.info):
			listofFiles = self.info['files']
			total = 0
			for files in listofFiles:
				total += files['length']
			return total
		else:
			return self.info['length']

	def start(self):
		# Connect to tracker and retrieve all the peers

		self.reactor.listenTCP(self.port, self.protocol)
		self.getPeerList() 
		self.started = True

	def updatePeers(self, tracker, peers):
		for peer in peers:
			if self.protocol.isInQueue(socket.inet_ntoa(struct.pack("!i",int(peer['IP']))), int(peer['port'])) == False:
				self.reactor.connectTCP(socket.inet_ntoa(struct.pack("!i",int(peer['IP']))), int(peer['port']), self.protocol)
				self.protocol.addToQueue(socket.inet_ntoa(struct.pack("!i",int(peer['IP']))), int(peer['port']))

	def getPeerList(self):
		Logger.info("Getting Peer List from Trackers")
		for tracker in self.announce_list:
			self.reactor.listenUDP(0, TrackerAnnounce.UDPClientProtocol(tracker[0], self))