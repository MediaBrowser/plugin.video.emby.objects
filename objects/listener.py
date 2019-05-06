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

    if not isPlaying and xbmc.getCondVisibility('Window.IsVisible(DialogContextMenu.xml)'):
        control = int(xbmcgui.Window(10106).getFocusId())

        if xbmc.getInfoLabel('Control.GetLabel(1002)') == xbmc.getLocalizedString(12021):
            if control == 1002: # Start from beginning

                LOG.info("Resume dialog: Start from beginning selected.")
                window('emby.resume.bool', False)
                window('emby.context.widget.bool', True)
            elif control == 1001:

                LOG.info("Resume dialog: Resume selected.")
                window('emby.resume.bool', True)
                window('emby.context.widget.bool', True)
            elif control == 1005:

                LOG.info("Reset resume point selected.")
                window('emby.context.resetresume.bool', True)
            else:
                window('emby.resume', clear=True)
                window('emby.context.resetresume', clear=True)
                window('emby.context.widget', clear=True)
        else: # Item without a resume point
            if control == 1001:

                LOG.info("Play dialog selected.")
                window('emby.context.widget.bool', True)
            else:
                window('emby.context.widget', clear=True)

    elif isPlaying and not window('emby.external_check'):

        window('emby.external.bool', player.isExternalPlayer())
        window('emby.external_check.bool', True)
