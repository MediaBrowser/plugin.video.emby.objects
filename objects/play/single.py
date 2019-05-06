# -*- coding: utf-8 -*-

#################################################################################################

import logging
import sys

import xbmc
import xbmcgui
import xbmcvfs

from objects.play import Play
from downloader import TheVoid
from helper import _, settings, api, playutils, dialog, window
from emby import Emby

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################


class PlaySingle(Play):


    def __init__(self, params, server_id=None, *args, **kwargs):

        ''' Play the main item only. Useful for external players.
        '''
        self.info = {
            'Item': None,
            'Id': params.get('id'),
            'DbId': params.get('dbid'),
            'Transcode': params.get('transcode') == 'true',
            'ServerId': server_id,
            'ServerAddress': TheVoid('GetServerAddress', {'ServerId': server_id}).get(),
        }
        if self.info['Transcode'] is None:
             self.info['Transcode'] = settings('playFromTranscode.bool') if settings('playFromStream.bool') else None

        Play.__init__(self, self.info['ServerId'], self.info['ServerAddress'])
        self._detect_play()

        LOG.info("--[ play single ]")

    def _get_item(self):
        self.info['Item'] = TheVoid('GetItem', {'Id': self.info['Id'], 'ServerId': self.info['ServerId']}).get()

    def _detect_play(self):

        ''' Download all information needed to build the playlist for item requested.
        '''
        if self.info['Id']:
            self._get_item()

    def play(self):

        ''' Create and add listitems to the Kodi playlist.
        '''
        LOG.info("[ play/%s ]", self.info['Id'])

        listitem = xbmcgui.ListItem()
        self._set_playlist(listitem)

        return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

    def _set_playlist(self, listitem):

        ''' Verify seektime, set intros, set main item and set additional parts.
            Detect the seektime for video type content.
            Verify the default video action set in Kodi for accurate resume behavior.
        '''
        seektime = self.get_seektime()

        LOG.info("[ main/%s ] %s", self.info['Item']['Id'], self.info['Item']['Name'])
        play = playutils.PlayUtils(self.info['Item'], self.info['Transcode'], self.info['ServerId'], self.info['ServerAddress'])
        source = play.select_source(play.get_sources())

        if not source:
            raise Exception("Playback selection cancelled")

        play.set_external_subs(source, listitem)
        self.set_listitem(self.info['Item'], listitem, self.info['DbId'], seektime)
        listitem.setPath(self.info['Item']['PlaybackInfo']['Path'])
        playutils.set_properties(self.info['Item'], self.info['Item']['PlaybackInfo']['Method'], self.info['ServerId'])
