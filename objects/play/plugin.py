# -*- coding: utf-8 -*-

#################################################################################################

import json
import logging
import threading
import sys
from datetime import timedelta

import xbmc
import xbmcgui
import xbmcplugin

from objects.play import Play
from emby import Emby
from helper import _, playutils, api, window, settings, dialog, JSONRPC

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################


class PlayPlugin(Play):


    def __init__(self, params, server_id=None, *args, **kwargs):

        self.info = {
            'Intros': None,
            'Item': None,
            'Id': params.get('id', params.get('Id')),
            'DbId': params.get('dbid'),
            'Transcode': params.get('transcode') == 'true',
            'AdditionalParts': None,
            'ServerId': server_id,
            'KodiPlaylist': xbmc.PlayList(xbmc.PLAYLIST_VIDEO),
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

        LOG.info("--[ play plugin ]")

    def _detect_play(self):

        ''' Download all information needed to build the playlist for item requested.
        '''
        if self.info['Id']:

            self.get_intros()
            self.get_item()
            self.get_additional_parts()

    def play(self, clear_playlist=False, start_position=None):

        ''' Create and add listitems to the Kodi playlist. 
            Base PlayMedia scenario on playlist size.
        '''
        self.info['KodiPlaylist'] = self.set_playlist()

        if clear_playlist or window('emby.playlist.clear.bool'):

            LOG.info("[ clear playlist ]")
            self.info['KodiPlaylist'].clear()
            window('emby.playlist.clear', clear=True)
            window('emby.autoplay', clear=True)

        pl_size = int(bool(self.info['KodiPlaylist'].size()))
        self.info['StartIndex'] = start_position if start_position is not None else max(self.info['KodiPlaylist'].getposition(), 0)
        self.info['Index'] = self.info['StartIndex'] + pl_size
        LOG.info("[ play/%s/%s ]", self.info['Id'], self.info['Index'])
        window('emby.playlist.start', str(self.info['Index']))

        listitem = xbmcgui.ListItem()
        self._set_playlist(listitem)

        count = 20

        if xbmc.getCondVisibility('VideoPlayer.Content(livetv)'):
            xbmc.Player().stop()

        while not window('emby.playlist.ready.bool'):
            xbmc.sleep(50)

            if not count:
                LOG.info("[ playback aborted ]")

                raise Exception("PlaybackAborted")

            count -= 1
        else:
            try:
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            except Exception:
                pass

            if not pl_size:
                self.start_playback(self.info['StartIndex'])
            else:
                xbmc.sleep(2000)
                self.remove_from_playlist(self.info['StartIndex'])

        return self.info['Index']

    def play_folder(self, position=None):

        ''' When an entire queue is requested, 
            If requested from Kodi, MediaType is provided, add as Kodi would,
            otherwise queue playlist items using strm links to setup playback later.
        '''
        self.info['StartIndex'] = position or max(self.info['KodiPlaylist'].size(), 0)
        self.info['Index'] = self.info['StartIndex']
        LOG.info("[ play folder/%s/%s ]", self.info['Id'], self.info['Index'])

        if self.info['DbId'] and self.info['MediaType']:
            self.add_to_playlist(self.info['MediaType'], self.info['DbId'], self.info['Index'])
            self.info['Index'] += 1

        elif self.info['Item']['MediaType'] == 'Audio':
            listitem = xbmcgui.ListItem()
            self._set_playlist(listitem)
        else:
            listitem = xbmcgui.ListItem()
            self.set_listitem(self.info['Item'], listitem, self.info['DbId'])
            url = "plugin://plugin.video.emby?mode=play&id=%s" % self.info['Id']

            if self.info['DbId']:
                url += "&dbid=%s" % self.info['DbId']

            if self.info['ServerId']:
                url += "&server=%s" % self.info['ServerId']

            if self.info['Transcode']:
                url += "&transcode=true"

            listitem.setPath(url)
            self.add_listitem(url, listitem, self.info['Index'])
            self.info['Index'] += 1

        return self.info['Index']

    def _set_playlist(self, listitem):

        ''' Verify seektime, set intros, set main item and set additional parts.
            Detect the seektime for video type content.
            Verify the default video action set in Kodi for accurate resume behavior.
        '''
        seektime = self.get_seektime()

        if settings('enableCinema.bool') and not seektime:
            self.set_intros()

        LOG.info("[ main/%s/%s ] %s", self.info['Item']['Id'], self.info['Index'], self.info['Item']['Name'])
        play = playutils.PlayUtils(self.info['Item'], self.info['Transcode'], self.info['Server'])
        source = play.select_source(play.get_sources(self.info['MediaSourceId']), self.info['AudioIndex'], self.info['SubtitleIndex'])

        if not source:
            raise Exception("SelectionCancel")

        play.set_external_subs(source, listitem)

        if self.info['Item']['PlaybackInfo']['Method'] != 'Transcode':
            play.set_subtitles_in_database(source, self.info['Item']['PlaybackInfo'].get('Subtitles'))

        self.set_listitem(self.info['Item'], listitem, self.info['DbId'], False, seektime)
        listitem.setPath(self.info['Item']['PlaybackInfo']['Path'])
        playutils.set_properties(self.info['Item'], self.info['Item']['PlaybackInfo']['Method'], self.info['ServerId'])

        self.add_listitem(self.info['Item']['PlaybackInfo']['Path'], listitem, self.info['Index'])
        self.info['Index'] += 1

        if self.info['Item'].get('PartCount'):
            self.set_additional_parts()

    def set_intros(self):

        ''' if we have any play them when the movie/show is not being resumed.
        '''
        if self.info['Intros']['Items']:
            enabled = True

            if settings('askCinema') == "true":

                resp = dialog("yesno", heading="{emby}", line1=_(33016))
                if not resp:

                    enabled = False
                    LOG.info("Skip trailers.")

            if enabled:
                for intro in self.info['Intros']['Items']:

                    listitem = xbmcgui.ListItem()
                    LOG.info("[ intro/%s/%s ] %s", intro['Id'], self.info['Index'], intro['Name'])

                    play = playutils.PlayUtils(intro, False, self.info['Server'])
                    source = play.select_source(play.get_sources())
                    self.set_listitem(intro, listitem, intro=True)
                    listitem.setPath(intro['PlaybackInfo']['Path'])
                    playutils.set_properties(intro, intro['PlaybackInfo']['Method'], self.info['ServerId'])

                    self.add_listitem(intro['PlaybackInfo']['Path'], listitem, self.info['Index'])
                    self.info['Index'] += 1

                    window('emby.skip.%s.bool' % intro['Id'], True)

    def set_additional_parts(self):

        ''' Create listitems and add them to the stack of playlist.
        '''
        for part in self.info['AdditionalParts']['Items']:

            listitem = xbmcgui.ListItem()
            LOG.info("[ part/%s/%s ] %s", part['Id'], self.info['Index'], part['Name'])

            play = playutils.PlayUtils(part, False, self.info['Server'])
            source = play.select_source(play.get_sources())
            play.set_external_subs(source, listitem)

            if part['PlaybackInfo']['Method'] != 'Transcode':
                play.set_subtitles_in_database(source, part['PlaybackInfo'].get('Subtitles'))

            self.set_listitem(part, listitem)
            listitem.setPath(part['PlaybackInfo']['Path'])
            playutils.set_properties(part, part['PlaybackInfo']['Method'], self.info['ServerId'])

            self.add_listitem(part['PlaybackInfo']['Path'], listitem, self.info['Index'])
            self.info['Index'] += 1
