# -*- coding: utf-8 -*-

#################################################################################################

import logging

import xbmc
import xbmcgui
import xbmcvfs

from objects.play import Play
from helper import _, settings, api, playutils, dialog, window, JSONRPC
from emby import Emby

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################


class PlayStrm(Play):


    def __init__(self, params, server_id=None, *args, **kwargs):

        ''' Workflow: Strm that calls our webservice in database. When played,
            the webserivce returns a dummy file to play. Meanwhile,
            PlayStrm adds the real listitems for items to play to the playlist.
        '''
        self.info = {
            'Intros': None,
            'Item': None,
            'Id': params.get('Id'),
            'DbId': params.get('KodiId'),
            'Transcode': params.get('transcode'),
            'AdditionalParts': None,
            'ServerId': server_id,
            'KodiPlaylist': xbmc.PlayList(xbmc.PLAYLIST_VIDEO),
            'Server': Emby(server_id).get_client(),
            'MediaType': params.get('MediaType'),
            'ServerAddress': Emby(server_id)['auth/server-address'],
            'AudioIndex': params.get('AudioIndex'),
            'SubtitleIndex': params.get('SubtitleIndex'),
            'MediaSourceId': params.get('MediaSourceId')
        }
        if self.info['Transcode'] is None:
             self.info['Transcode'] = settings('playFromTranscode.bool') if settings('playFromStream.bool') else None

        Play.__init__(self, self.info['ServerId'], self.info['ServerAddress'])
        self._detect_play()

        LOG.info("--[ play strm ]")

    def _get_intros(self):
        self.info['Intros'] = self.info['Server']['api'].get_intros(self.info['Id'])

    def _get_additional_parts(self):
        self.info['AdditionalParts'] = self.info['Server']['api'].get_additional_parts(self.info['Id'])

    def _get_item(self):
        self.info['Item'] = self.info['Server']['api'].get_item(self.info['Id'])

    def _detect_play(self):

        ''' Download all information needed to build the playlist for item requested.
        '''
        if self.info['Id']:

            self._get_intros()
            self._get_item()
            self._get_additional_parts()

    def play(self, clear_playlist=False, start_position=None):

        ''' Create and add listitems to the Kodi playlist.
        '''
        self.info['KodiPlaylist'] = self.set_playlist()
        
        if clear_playlist:

            LOG.info("[ clear playlist ]")
            self.info['KodiPlaylist'].clear()
            xbmc.sleep(200)

        self.info['StartIndex'] = start_position if start_position is not None else max(self.info['KodiPlaylist'].getposition(), 0)
        self.info['Index'] = self.info['StartIndex']
        LOG.info("[ play/%s/%s ]", self.info['Id'], self.info['Index'])

        listitem = xbmcgui.ListItem()
        self._set_playlist(listitem)

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
            url = "http://127.0.0.1:57578/emby/play/file.strm?mode=play&Id=%s" % self.info['Id']

            if self.info['DbId']:
                url += "&KodiId=%s" % self.info['DbId']

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
            self._set_intros()

        LOG.info("[ main/%s/%s ] %s", self.info['Item']['Id'], self.info['Index'], self.info['Item']['Name'])
        play = playutils.PlayUtilsStrm(self.info['Item'], self.info['Transcode'], self.info['ServerId'], self.info['Server'])
        source = play.select_source(play.get_sources(self.info['MediaSourceId']), self.info['AudioIndex'], self.info['SubtitleIndex'])

        if not source:
            raise Exception("SelectionCancel")

        play.set_external_subs(source, listitem)

        if self.info['Item']['PlaybackInfo']['Method'] != 'Transcode':
            play.set_subtitles_in_database(source, self.info['Item']['PlaybackInfo'].get('Subtitles', {}))

        self.set_listitem(self.info['Item'], listitem, self.info['DbId'], False, seektime)
        listitem.setPath(self.info['Item']['PlaybackInfo']['Path'])
        playutils.set_properties(self.info['Item'], self.info['Item']['PlaybackInfo']['Method'], self.info['ServerId'])

        self.add_listitem(self.info['Item']['PlaybackInfo']['Path'], listitem, self.info['Index'])
        self.info['Index'] += 1

        if self.info['Item'].get('PartCount'):
            self._set_additional_parts()

    def _set_intros(self):

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

                    play = playutils.PlayUtilsStrm(intro, False, self.info['ServerId'], self.info['Server'])
                    source = play.select_source(play.get_sources())
                    self.set_listitem(intro, listitem, intro=True)
                    listitem.setPath(intro['PlaybackInfo']['Path'])
                    playutils.set_properties(intro, intro['PlaybackInfo']['Method'], self.info['ServerId'])

                    self.add_listitem(intro['PlaybackInfo']['Path'], listitem, self.info['Index'])
                    self.info['Index'] += 1

                    window('emby.skip.%s.bool' % intro['Id'], True)

    def _set_additional_parts(self):

        ''' Create listitems and add them to the stack of playlist.
        '''
        for part in self.info['AdditionalParts']['Items']:

            listitem = xbmcgui.ListItem()
            LOG.info("[ part/%s/%s ] %s", part['Id'], self.info['Index'], part['Name'])

            play = playutils.PlayUtilsStrm(part, False, self.info['ServerId'], self.info['Server'])
            source = play.select_source(play.get_sources())
            play.set_external_subs(source, listitem)

            if part['PlaybackInfo']['Method'] != 'Transcode':
                play.set_subtitles_in_database(source, part['PlaybackInfo'].get('Subtitles', {}))

            self.set_listitem(part, listitem)
            listitem.setPath(part['PlaybackInfo']['Path'])
            playutils.set_properties(part, part['PlaybackInfo']['Method'], self.info['ServerId'])

            self.add_listitem(part['PlaybackInfo']['Path'], listitem, self.info['Index'])
            self.info['Index'] += 1
