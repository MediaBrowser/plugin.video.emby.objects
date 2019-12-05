version = "181167263"
embyversion = "4.1.15"

from objects import utils

from objects.core import Objects
from objects.core import ListItem
from objects.core import Movies
from objects.core import MusicVideos
from objects.core import TVShows
from objects.core import Music

from objects.play import PlayStrm
from objects.play import PlaySingle
from objects.play import PlayPlugin
from objects.play import Playlist

from objects.listener import listener

from objects import monitor
from objects import player

Objects().mapping()
