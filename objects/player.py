# -*- coding: utf-8 -*-

#################################################################################################

import logging

from objects.core import Objects
from hooks import player
from helper import _, api, window, event, silent_catch, JSONRPC

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################


class Player(player.Player):

    played = {}
    up_next = False

    def __init__(self, monitor=None):

        self.monitor = monitor
        player.Player.__init__(self, monitor)

    @silent_catch()
    def get_playing_file(self):
        return self.getPlayingFile()

    def get_available_audio_streams(self):
        return self.getAvailableAudioStreams()

    def get_current_streams(self):

        params = {
            'playerid': self.monitor.playlistid,
            'properties': ["currentsubtitle","currentaudiostream","subtitleenabled"]
        }
        result = JSONRPC('Player.GetProperties').execute(params)
        result = result.get('result')

        try: # Audio tracks
            audio = result['currentaudiostream']['index']
        except (KeyError, TypeError):
            audio = 0
        
        try: # Subtitles tracks
            subs = result['currentsubtitle']['index']
        except (KeyError, TypeError):
            subs = 0

        try: # If subtitles are enabled
            subs_enabled = result['subtitleenabled']
        except (KeyError, TypeError):
            subs_enabled = False

        return audio, subs, subs_enabled

    def get_volume(self):

        result = JSONRPC('Application.GetProperties').execute({'properties': ["volume", "muted"]})
        result = result.get('result', {})
        volume = result.get('volume')
        muted = result.get('muted')

        return volume, muted

    def get_time(self):
        return int(self.getTime())

    def get_total_time(self):
        return int(self.getTotalTime())

    def set_audio_stream(self, index):
        self.setAudioStream(int(index))

    def set_subtitle_stream(self, index):
        self.setSubtitleStream(int(index))

    def set_subtitle(self, enable):
        self.showSubtitles(enable)

    def get_current_file(self, count=0): 
 
        ''' Each count is approx 1s. 
        ''' 
        try: 
            return self.getPlayingFile() 
        except Exception: 
 
            while count > 0: 
                try: 
                    return self.getPlayingFile() 
                except Exception: 
                    count -= 1 
 
                if self.monitor.waitForAbort(1): 
                    return 
            else: 
                raise Exception("FileNotFound") 
 
    def onPlayBackStarted(self):

        LOG.info("[ onPlayBackStarted ]")
        self.up_next = False

        try:
            current_file = self.get_current_file(5)
        except Exception as error:
            LOG.error(error)

            return

        self.stop_playback()
        item = self.set_item(current_file)

        if not item:
            return

        window('emby.skip.%s.bool' % item['Id'], True)

    def next_up(self):

        item = self.get_file_info(self.get_playing_file())
        next_item = self.get_next_up(item)
        objects = Objects()

        API = api.API(next_item, item['Server']['auth/server-address'])
        data = objects.map(next_item, "UpNext")
        artwork = API.get_all_artwork(objects.map(next_item, 'ArtworkParent'), True)
        data['art'] = {
            'tvshow.poster': artwork.get('Series.Primary'),
            'tvshow.fanart': None,
            'thumb': artwork.get('Primary')
        }
        if artwork['Backdrop']:
            data['art']['tvshow.fanart'] = artwork['Backdrop'][0]

        next_info = {
            'play_info': {'ItemIds': [data['episodeid']], 'ServerId': item['ServerId'], 'PlayCommand': 'PlayNow'},
            'current_episode': item['CurrentEpisode'],
            'next_episode': data
        }

        LOG.info("--[ next up ] %s", next_info)
        event("upnext_data", next_info, hexlify=True)

    def onPlayBackPaused(self):
        current_file = self.get_playing_file()

        if self.is_playing_file(current_file):

            self.get_file_info(current_file)['Paused'] = True
            self.report_playback()
            LOG.debug("-->[ paused ]")

    def onPlayBackResumed(self):
        current_file = self.get_playing_file()

        if self.is_playing_file(current_file):

            self.get_file_info(current_file)['Paused'] = False
            self.report_playback()
            LOG.debug("--<[ paused ]")

    def onPlayBackSeek(self, time, seekOffset):

        ''' Does not seem to work in Leia??
        '''
        if self.is_playing_file(self.get_playing_file()):

            self.report_playback()
            LOG.info("--[ seek ]")
