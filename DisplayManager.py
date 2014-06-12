import threading
import time
import os
import sys

class DisplayManager(threading.Thread):
	def __init__(self, torrent, threadID):
		threading.Thread.__init__(self)
		self.torrent = torrent

	def run(self):
		while(self.torrent.started == False):
			time.sleep(2)
		print "TORRENT STARTED!!"
		time.sleep(5)
		while(True):
			# os.system('cls' if os.name=='nt' else 'clear') 
			try:
				print "Avg Speed(Current Session): " + str(self.torrent.fileManager.downloaded/((time.time()-self.torrent.start_time)*1024)) + " KBps || Remaining: " + str((self.torrent.fileManager.file_to_stream_length - self.torrent.fileManager.bytesWritten)/(1024*1024)) + " MB || Efficiency: " + str((self.torrent.fileManager.downloaded*100)/self.torrent.requester.total_data_received) + "%  || Completed:" + str((self.torrent.fileManager.bytesWritten)/(1024*1024))+" MB            \r",
			except Exception, e:
				print "Avg Speed(Current Session): " + str(self.torrent.fileManager.downloaded/((time.time()-self.torrent.start_time)*1024)) + " KBps || Remaining: " + str((self.torrent.fileManager.file_to_stream_length - self.torrent.fileManager.bytesWritten)/(1024*1024)) + " MB || Efficiency: N/A  || Completed:" + str((self.torrent.fileManager.bytesWritten)/(1024*1024))+" MB            \r",
			
			sys.stdout.flush()
			# The refresh Interval
			time.sleep(1)
		