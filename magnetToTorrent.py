import urllib2

def isMagnetURI(link):
	print "Checking For MagnetURI"
	link = link[:6]
	if(link == "magnet"):
		return True
	return False

class MagnetURI(object):
	"""MagnetURI LINK"""
	def __init__(self, link):
		super(MagnetURI, self).__init__()
		self.link = link
	def getTorrentData(self):
		ret = dict()
		slink = (self.link[8:]).split('&')
		tracker = []
		for ele in slink:
			ele = urllib2.unquote(ele.encode("utf8"))
			ele = ele.split('=')
			if(ele[0] == "xt"):
				ret['hash'] = ele[1][9:]
			if(ele[0] == "tr"):
				tracker.append(ele[1])
			else:
				ret[ele[0]] = ele[1]
		ret['tr'] = tracker
		return ret
