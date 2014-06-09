Python Implementation of a Client for Torrent Streaming.
The Code downloads the file sequentially so as to allow playback in the media player even if the entire file has not be downloaded.

The Code can be run by simply executing Client.py as :


```
$ python Client.py link_to_torrent_file
```
The code will download the .torrent File and initiate downloading.
Incase the Torrent has multiple files, the code will ask which file to download/stream.

The code requires the [Twisted Framework](https://twistedmatrix.com/) and the [bitstring](https://pypi.python.org/pypi/bitstring/3.1.3) library.

## TO DO ##
* Implement a Terminal Display to show the current Statistics of the Torrent being downloaded.
* Implement a Graphical Display to show the current Statistics of the Torrent being downloaded.
* Adding support for resuming download.
* Adding support for Magnet URI
* Adding support to stream from a seek location.
