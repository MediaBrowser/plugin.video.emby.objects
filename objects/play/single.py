# -*- coding: utf-8 -*-

#################################################################################################

import logging
import sys

import xbmc
import xbmcgui
import xbmcvfs
import xbmcplugin

from objects.play import Play
from emby import Emby
from helper import _, settings, api, playutils, dialog, window

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
            'Server': Emby(server_id).get_client(),
            'ServerAddress': Emby(server_id)['auth/server-address'],
            'AudioIndex': params.get('AudioIndex'),
            'SubtitleIndex': params.get('SubtitleIndex'),
            'MediaSourceId': params.get('MediaSourceId')
        }
        if self.info['Transcode'] is None:
             self.info['Transcode'] = settings('playFromTranscode.bool') if settings('playFromStream.bool') else None

        Play.__init__(self, self.info['ServerAddress'])
        self._detect_play()

        LOG.info("--[ play single ]")

    def _detect_play(self):

        ''' Download all information needed to build the playlist for item requested.
        '''
        if self.info['Id']:
            self.get_item()

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
        play = playutils.PlayUtils(self.info['Item'], self.info['Transcode'], self.info['Server'])
        source = play.select_source(play.get_sources(self.info['MediaSourceId']), self.info['AudioIndex'], self.info['SubtitleIndex'])

        if not source:
            raise Exception("Playback selection cancelled")

        play.set_external_subs(source, listitem)
        self.set_listitem(self.info['Item'], listitem, self.info['DbId'], seektime=seektime)
        listitem.setPath(self.info['Item']['PlaybackInfo']['Path'])
        playutils.set_properties(self.info['Item'], self.info['Item']['PlaybackInfo']['Method'], self.info['ServerId'])
