# -*- coding: utf-8 -*-

#################################################################################################

import logging
from datetime import timedelta

import xbmc
import xbmcaddon

from objects import ListItem
from objects.utils import get_play_action
from dialogs import resume
from helper import _, window, api, JSONRPC

#################################################################################################

LOG = logging.getLogger("EMBY.play")

#################################################################################################


class Play(object):

    def __init__(self, server_id, server, *args, **kwargs):
        self.set_listitem = ListItem(server, server_id).set

    def set_playlist(self):

        if self.info['Item']['MediaType'] == 'Audio':
            LOG.info("using music playlist")
            return xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        return xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    def add_listitem(self, url, listitem, index):
        self.info['KodiPlaylist'].add(url=url, listitem=listitem, index=self.info['Index'])

    def remove_from_playlist(self, index):

        LOG.debug("[ removing ] %s", index)
        JSONRPC('Playlist.Remove').execute({'playlistid': self.info['KodiPlaylist'].getPlayListId(), 'position': index})

    def get_seektime(self):

        ''' Resume item if available. Will call the user resume dialog.
            Returns bool or raise an exception if resume was cancelled by user.
        '''
        seektime = window('emby.resume')
        seektime = seektime == 'true' if seektime else None
        auto_play = window('emby.autoplay.bool')
        window('emby.resume', clear=True)

        if auto_play:

            seektime = False
            LOG.info("[ skip resume for auto play ]")

        elif seektime is None and self.info['Item']['MediaType'] in ('Video', 'Audio'):
            resume = self.info['Item']['UserData'].get('PlaybackPositionTicks')

            if resume:

                if get_play_action() == "Resume":
                    seektime = True

                if seektime is None:

                    adjusted = api.API(self.info['Item'], self.info['ServerAddress']).adjust_resume((resume or 0) / 10000000.0)
                    seektime = self.resume_dialog(adjusted, self.info['Item'])
                    LOG.info("Resume: %s", adjusted)

                    if seektime is None:
                        raise Exception("User backed out of resume dialog.")

            window('emby.autoplay.bool', True)

        return seektime

    def resume_dialog(self, seektime, item, *args, **kwargs):

        ''' Base resume dialog based on Kodi settings.
        '''
        LOG.info("Resume dialog called.")
        XML_PATH = (xbmcaddon.Addon('plugin.video.emby').getAddonInfo('path'), "default", "1080i")

        dialog = resume.ResumeDialog("script-emby-resume.xml", *XML_PATH)
        dialog.set_resume_point(_(12022) % str(timedelta(seconds=seektime)).split(".")[0])
        dialog.doModal()

        if dialog.is_selected():

            if not dialog.get_selected(): # Start from beginning selected.
                return False
        else: # User backed out
            LOG.info("User exited without a selection.")

            return

        return True
