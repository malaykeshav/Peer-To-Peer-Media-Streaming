# Malay Keshav, Rahul Upadhyaya and Khushal Sagar

import magnetToTorrent as Magnet
import Torrent
import gzip
import os
import urllib2
import urllib
import bencode_torrent as bencode
import hashlib
import requests
import logging as Logger
from struct import *
from twisted.internet import reactor
import socket,struct
import time
import Core
import sys
import threading
from DisplayManager import DisplayManager

def init_log():
	Logger.basicConfig(filename='BTP_LOG.log',
							filemode='a',
							format='%(asctime)s : %(message)s',
							level=Logger.INFO)
	Logger.info("Client Started.\nLog Initialized")

class Client(object):
	"""Main Torrent Client Class"""
	def __init__(self, torrent_link):
		super(Client, self).__init__()
		self.torrent_link = torrent_link
		self.peerID = self.generatePID()
		self.port = 6888
		self.initAll()

	def generatePID(self):
		ret = "MKR_" + str(os.getpid()) + str(os.times()[-1])
		ret = pack('20s', ret[:20])

		Logger.info("Peer ID Generated :" + str(ret))
		# print "Peer ID Generated :", ret
		return ret


	def initAll(self):
		self.isMagnet = Magnet.isMagnetURI(self.torrent_link)
		Logger.info("Initializing Torrent Data")
		if(self.isMagnet == True):
			# Send MagnetURI To class and get torrent Data
			pass
		else:
			# Get Torrent Data From Net 
			torrent_raw_data  = self.downloadTorrentFile()
			self.torrent = Torrent.Torrent(reactor, raw_data = torrent_raw_data, peer_id = self.peerID, port = self.port)
		Logger.info("Initialization For Torrent Data Complete")

	def downloadTorrentFile(self):
		Logger.info("Now Downloading Torrent File")
		url = self.torrent_link
		f = urllib2.urlopen(url)
		temp_torrent_filename = "tempTorrentFile.torrent.gz"
		data = f.read()			
		try:								
			#download the torrent file pointed to by the url.
			with open(temp_torrent_filename, "wb") as code:
				code.write(data)					
			#save it in a temp file.
			f = gzip.open(temp_torrent_filename,'rb')
			file_content = f.read()									
			#unzip it to extract original contents and delete this temp file.
			os.remove(temp_torrent_filename)
		except:
			file_content = data
		Logger.info("Torrent File Download Complete")
		return file_content	

init_log()
# client = Client("http://torcache.net/torrent/BCF27930087EAA422413B02650B55BB2A9567C49.torrent?title=[kickass.to]eminem.the.marshall.mathers.lp2.deluxe.edition.2013.320kbps.cbr.mp3.vx.p2pdl")	
# client = Client("http://torcache.net/torrent/A7C04E9C66061C5C0E66FC2C61BA5A28D819F0AD.torrent?title=[kickass.to]linkin.park.greatest.hits.2013")
# client = Client("http://torcache.net/torrent/B22B8FC4068C723EF8FE59540DC7199A9AA7D738.torrent?title=[kickass.to]queen.2014.hindi.320kbps.vbr.mp3.songs.praky")
client = Client(sys.argv[1])
client.torrent.start()
displayManager = DisplayManager(client.torrent,1)
displayManager.start()
reactor.run()



