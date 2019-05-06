# -*- coding: utf-8 -*-

#################################################################################################

import logging

import xbmc

from objects.play import PlayStrm
from helper import window

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)
PLAY = {
    'PlayNow': 0,
    'PlayNext': 1,
    'PlayLast': 2
}

#################################################################################################


class Playlist(object):


    def __init__(self, server_id, items, mode=None, seektime=None, mediasource_id=None, 
                 audio=None, subtitle=None, *args, **kwargs):

        self.server_id = server_id
        self.items = items
        self.index = None

        mode = mode or PLAY['PlayNow']

        self.play(mode, seektime, mediasource_id, audio, subtitle)
        self.play_playlist()

    def play(self, mode, seektime=None, mediasource_id=None, audio=None, subtitle=None, *args, **kwargs):

        ''' Clear Playlist and start playback for PlayNow mode.
        '''
        params = {
            'Id': self.items.pop(0),
            'AudioIndex': audio,
            'Subtitle': subtitle,
            'MediaSourceId': mediasource_id
        }

        if seektime:
            window('emby.resume.bool', True)

        play = PlayStrm(params, self.server_id)

        if mode == PLAY['PlayNow']:

            if play.info['Item']['MediaType'] == 'Video' or play.info['Item']['Type'] == 'AudioBook':
                xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
            else:
                xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
                play.info['KodiPlaylist'] = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        pl_size = max(play.info['KodiPlaylist'].size(), 0)
        start_position = max(play.info['KodiPlaylist'].getposition(), 0)

        if mode == PLAY['PlayNext']:
            start_position += int(bool(pl_size))
        elif mode == PLAY['PlayLast']:
            start_position = pl_size

        self.index = play.play(start_position, delayed=start_position)

    def play_playlist(self, ):

        for item in self.items:

            play = PlayStrm({'Id': item}, self.server_id)
            self.index = play.play_folder(self.index)
