# -*- coding: utf-8 -*-

#################################################################################################

import logging
import os
import xml.etree.ElementTree as etree

import xbmc

from helper import JSONRPC

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################

def get_play_action():

    ''' I could not figure out a way to listen to kodi setting changes?
        For now, verify the play action every time play is called.
    '''
    options = ['Choose', 'Play', 'Resume', 'Show information']
    result = JSONRPC('Settings.GetSettingValue').execute({'setting': "myvideos.selectaction"})
    try:
        return options[result['result']['value']]
    except Exception as error:
        log.error("Returning play action due to error: %s", error)

        return options[1]

def get_grouped_set():

    ''' Get if boxsets should be grouped
    '''
    result = JSONRPC('Settings.GetSettingValue').execute({'setting': "videolibrary.groupmoviesets"})
    try:
        return result['result']['value']
    except Exception as error:
        return False

def get_web_server():

    result = JSONRPC('Settings.GetSettingValue').execute({'setting': "services.webserver"})

    try:
        return result['result']['value']
    except (KeyError, TypeError):
        return False

def enable_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

def disable_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def default_settings_default():

    ''' Settings table for audio and subtitle tracks.
    '''
    path = xbmc.translatePath('special://profile/').decode('utf-8')
    file = os.path.join(path, 'guisettings.xml').decode('utf-8')

    try:
        xml = etree.parse(file).getroot()
    except Exception:
        return

    default = xml.find('defaultvideosettings')

    return {
        'Deinterlace': default.find('interlacemethod').text,
        'ViewMode': default.find('viewmode').text,
        'ZoomAmount': default.find('zoomamount').text,
        'PixelRatio': default.find('pixelratio').text,
        'VerticalShift': default.find('verticalshift').text,
        'SubtitleDelay': default.find('subtitledelay').text,
        'ShowSubtitles': default.find('showsubtitles').text == 'true',
        'Brightness': default.find('brightness').text,
        'Contrast': default.find('contrast').text,
        'Gamma': default.find('gamma').text,
        'VolumeAmplification': default.find('volumeamplification').text,
        'AudioDelay': default.find('audiodelay').text,
        'Sharpness': default.find('sharpness').text,
        'NoiseReduction': default.find('noisereduction').text,
        'NonLinStretch': int(default.find('nonlinstretch').text == 'true'),
        'PostProcess': int(default.find('postprocess').text == 'true'),
        'ScalingMethod': default.find('scalingmethod').text,
        'StereoMode': default.find('stereomode').text,
        'CenterMixLevel': default.find('centermixlevel').text
    }
