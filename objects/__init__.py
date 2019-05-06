version = "DEV"
embyversion = "0.1"

from core import Objects
from core import ListItem
from core import Movies
from core import MusicVideos
from core import TVShows
from core import Music

from play import PlayStrm
from play import PlaySingle
from play import PlayPlugin
from play import Playlist

from listener import listener

import utils
import monitor
import player

Objects().mapping()
