# -*- coding: utf-8 -*-

#################################################################################################

import logging

import xbmc
import xbmcgui

from objects.play import Play
from objects.play import PlayPlugin, PlayStrm
from helper import window

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)
PLAY = {
    'PlayNow': 0,
    'PlayNext': 1,
    'PlayLast': 2,
    'PlayUpNext': 3
}

#################################################################################################


class Playlist(Play):

    started = False


    def __init__(self, server_id, items, mode=None, seektime=None, mediasource_id=None, 
                 audio=None, subtitle=None, start_index=None, *args, **kwargs):

        self.server_id = server_id
        self.items = items
        self.info = {'StartIndex': start_index or 0}

        mode = mode or PLAY['PlayNow']
        LOG.info("--[ play playlist ]")
        Play.__init__(self, server_id, None)

        self.play(mode, seektime, mediasource_id, audio, subtitle)
        self.play_playlist()

    def _start_playback(self, play):

        if self.started:
            return

        if self.info['Index'] >= self.info['StartIndex']:

            play.start_playback(self.info['StartIndex'])
            self.started = True

    def play(self, mode, seektime=None, mediasource_id=None, audio=None, subtitle=None, *args, **kwargs):

        ''' Clear Playlist and start playback for PlayNow mode.
        '''
        params = {
            'Id': self.items.pop(0),
            'AudioIndex': audio,
            'SubtitleIndex': subtitle,
            'MediaSourceId': mediasource_id
        }
        if seektime:
            window('emby.resume.bool', True)
        else:
            window('emby.resume.bool', False)

        funcs = [self.play_now, self.play_next, self.play_last, self.play_upnext]
        funcs[mode](params, *args, **kwargs)

    def play_now(self, params, *args, **kwargs):

        play = PlayPlugin(params, self.server_id)
        self.info['Index'] = play.play(True)
        self.info['KodiPlaylist'] = play.info['KodiPlaylist']
        self._start_playback(play)

    def play_next(self, params, *args, **kwargs):

        play = PlayPlugin(params, self.server_id)
        pl_size = max(play.info['KodiPlaylist'].size(), 0)
        self.info['StartIndex'] = max(play.info['KodiPlaylist'].getposition(), 0) + int(bool(pl_size))
        self.info['Index'] = play.play(start_position=self.info['StartIndex'])
        self.info['KodiPlaylist'] = play.info['KodiPlaylist']

    def play_last(self, params, *args, **kwargs):

        play = PlayPlugin(params, self.server_id)
        self.info['StartIndex'] = max(play.info['KodiPlaylist'].size(), 0)
        self.info['Index'] = play.play(start_position=self.info['StartIndex'])
        self.info['KodiPlaylist'] = play.info['KodiPlaylist']

    def play_upnext(self, params, *args, **kwargs):

        play = PlayStrm(params, self.server_id)
        pl_size = max(play.info['KodiPlaylist'].size(), 0)
        self.info['StartIndex'] = max(play.info['KodiPlaylist'].getposition(), 0) + int(bool(pl_size))
        self.info['Index'] = play.play(start_position=self.info['StartIndex'])
        self.info['KodiPlaylist'] = play.info['KodiPlaylist']
        self._start_playback(play)

        for i in reversed(range(self.info['KodiPlaylist'].size())):

            if i >= self.info['Index']:
                self.remove_from_playlist(i)

    def play_playlist(self):

        for item in self.items:

            play = PlayPlugin({'Id': item}, self.server_id)
            play.info['KodiPlaylist'] = self.info['KodiPlaylist']
            self.info['Index'] = play.play_folder(self.info['Index'])
            self._start_playback(play)
