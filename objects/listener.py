# -*- coding: utf-8 -*-

#################################################################################################

import logging

import xbmc
import xbmcgui

from helper import window

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################

def listener():

    ''' Corner cases that needs to be listened to.
        This is run in a loop within monitor.py
    '''
    player = xbmc.Player()
    isPlaying = player.isPlaying()
    count = int(window('emby.external_count') or 0)

    if (not isPlaying and xbmc.getCondVisibility('Window.IsVisible(DialogContextMenu.xml)') and
        xbmc.getInfoLabel('Control.GetLabel(1002)') == xbmc.getLocalizedString(12021)):

        control = int(xbmcgui.Window(10106).getFocusId())

        if control == 1002: # Start from beginning

            LOG.info("Resume dialog: Start from beginning selected.")
            window('emby.resume.bool', False)
        else:
            LOG.info("Resume dialog: Resume selected.")
            window('emby.resume.bool', True)

    elif isPlaying and not window('emby.external_check'):
        time = player.getTime()

        if time > 1: # Not external player.

            window('emby.external_check', value="true")
            window('emby.external_count', value="0")
        elif count == 120:

            LOG.info("External player detected.")
            window('emby.external.bool', True)
            window('emby.external_check.bool', True)
            window('emby.external_count', value="0")

        elif time == 0:
            window('emby.external_count', value=str(count + 1))
