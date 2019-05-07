# -*- coding: utf-8 -*-

#################################################################################################

import logging

import xbmc
import xbmcgui

from objects.core import Objects
from helper import _, api

#################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

#################################################################################################


class BaseListItem(object):

    def __init__(self, obj_type, art_type, art_parent, listitem, item, *args, **kwargs):

        self.li = listitem
        self.item = item
        self.objects = Objects()
        self.api = api.API(item, item['LI']['Server'])

        self.obj = self._get_objects(obj_type)
        self.obj['Artwork'] = self._get_artwork(art_type, art_parent)

        self.format()
        self.set()

    def __getitem__(self, key):
        return self.obj[key]

    def __setitem__(self, key, value):
        self.obj[key] = value

    def _get_objects(self, key):
        return  self.objects.map(self.item, key)

    def _get_artwork(self, key, parent=False):
        return  self.api.get_all_artwork(self.objects.map(self.item, key), parent)

    def format(self):

        ''' Format object values. Override.
        '''
        pass

    def set(self):

        ''' Set the listitem values based on object. Override.
        '''
        pass

    @classmethod
    def art(cls):

        ''' Return artwork mapping for object. Override if needed.
        '''
        return  {
            'poster': "Primary",
            'clearart': "Art",
            'clearlogo': "Logo",
            'discart': "Disc",
            'fanart_image': "Backdrop",
            'landscape': "Thumb",
            'thumb': "Primary",
            'fanart': "Backdrop"
        }

    def set_art(self):

        artwork = self['Artwork']
        art = self.art()

        for kodi, emby in art.items():

            if emby == 'Backdrop':
                self._set_art(kodi, artwork[emby][0] if artwork[emby] else " ")
            else:
                self._set_art(kodi, artwork.get(emby, " "))

    def _set_art(self, art, path, *args, **kwargs):
        LOG.debug(" [ art/%s ] %s", art, path)

        if art in ('fanart_image', 'small_poster', 'tiny_poster',
                   'medium_landscape', 'medium_poster', 'small_fanartimage',
                   'medium_fanartimage', 'fanart_noindicators', 'discart',
                   'tvshow.poster'):

            self.li.setProperty(art, path)
        else:
            self.li.setArt({art: path})


class Playlist(BaseListItem):

    def __init__(self, *args, **kwargs):
        BaseListItem.__init__(self, 'BrowseFolder', 'Artwork', False, *args, **kwargs)

    def set(self):

        self.li.setProperty('path', self['Artwork']['Primary'])
        self.li.setProperty('IsFolder', 'true')
        self.li.setThumbnailImage(self['Artwork']['Primary'])
        self.li.setIconImage('DefaultFolder.png')

        self.li.setProperty('IsPlayable', 'false')
        self.li.setLabel(self['Title'])
        self.li.setContentLookup(False)


class Channel(BaseListItem):

    def __init__(self, *args, **kwargs):
        BaseListItem.__init__(self, 'BrowseChannel', 'Artwork', False, *args, **kwargs)

    @staticmethod
    def art():
        return  {
            'fanart_image': "Backdrop",
            'thumb': "Primary",
            'fanart': "Backdrop"
        }

    def format(self):

        self['Title'] = "%s - %s" % (self['Title'], self['ProgramName'])
        self['Runtime'] = round(float((self['Runtime'] or 0) / 10000000.0), 6)
        self['PlayCount'] = self.api.get_playcount(self['Played'], self['PlayCount']) or 0
        self['Overlay'] = 7 if self['Played'] else 6
        self['Artwork']['Primary'] = self['Artwork']['Primary'] or "special://home/addons/plugin.video.emby/icon.png"
        self['Artwork']['Thumb'] = self['Artwork']['Thumb'] or "special://home/addons/plugin.video.emby/icon.jpg"
        self['Artwork']['Backdrop'] = self['Artwork']['Backdrop'] or ["special://home/addons/plugin.video.emby/fanart.jpg"]

    def set(self):

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay']
        }
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])
        self.set_art()

        if not self['Artwork']['Backdrop']:
            self.li.setArt({'fanart':self['Artwork']['Primary']})

        self.li.setProperty('totaltime', str(self['Runtime']))
        self.li.setProperty('IsPlayable', 'true')
        self.li.setProperty('IsFolder', 'false')

        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)


class Photo(BaseListItem):

    def __init__(self, *args, **kwargs):
        BaseListItem.__init__(self, 'BrowsePhoto', 'Artwork', False, *args, **kwargs)

    def format(self):

        self['Overview'] = self.api.get_overview(self['Overview'])
        self['FileDate'] = "%s.%s.%s" % tuple(reversed(self['FileDate'].split('T')[0].split('-')))

    def set(self):

        metadata = {
            'title': self['Title'],
            'picturepath': self['Artwork']['Primary'],
            'date': self['FileDate'],
            'exif:width': str(self.obj.get('Width', 0)),
            'exif:height': str(self.obj.get('Height', 0)),
            'size': self['Size'],
            'exif:cameramake': self['CameraMake'],
            'exif:cameramodel': self['CameraModel'],
            'exif:exposuretime': str(self['ExposureTime']),
            'exif:focallength': str(self['FocalLength'])
        }
        self.li.setProperty('path', self['Artwork']['Primary'])
        self.li.setThumbnailImage(self['Artwork']['Primary'])
        self.li.setProperty('plot', self['Overview'])
        self.li.setProperty('IsFolder', 'false')
        self.li.setIconImage('DefaultPicture.png')
        self.li.setProperty('IsPlayable', 'false')
        self.li.setLabel(self['Title'])
        self.li.setInfo('pictures', metadata)
        self.li.setContentLookup(False)


class Music(BaseListItem):

    def __init__(self, *args, **kwargs):
        BaseListItem.__init__(self, 'BrowseAudio', 'ArtworkMusic', True, *args, **kwargs)

    @classmethod
    def art(cls):
        return  {
            'clearlogo': "Logo",
            'discart': "Disc",
            'fanart': "Backdrop",
            'fanart_image': "Backdrop", # in case
            'thumb': "Primary"
        }

    def format(self):

        self['Runtime'] = round(float((self['Runtime'] or 0) / 10000000.0), 6)
        self['PlayCount'] = self.api.get_playcount(self['Played'], self['PlayCount']) or 0
        self['Rating'] = self['Rating'] or 0

        if not self['Played']:
            self['DatePlayed'] = None

        if self['FileDate'] or self['DatePlayed']:
            self['DatePlayed'] = (self['DatePlayed'] or self['FileDate']).split('.')[0].replace('T', " ")

        self['FileDate'] = "%s.%s.%s" % tuple(reversed(self['FileDate'].split('T')[0].split('-')))

    def set(self):

        metadata = {
            'title': self['Title'],
            'genre': self['Genre'],
            'year': self['Year'],
            'album': self['Album'],
            'artist': self['Artists'],
            'rating': self['Rating'],
            'comment': self['Comment'],
            'date': self['FileDate'],
            'mediatype': "music"
        }
        self.set_art()


class PhotoAlbum(Photo):

    def __init__(self, *args, **kwargs):
        Photo.__init__(self, *args, **kwargs)

    def set(self):

        metadata = {
            'title': self['Title']
        }
        self.li.setProperty('path', self['Artwork']['Primary'])
        self.li.setThumbnailImage(self['Artwork']['Primary'])
        self.li.setProperty('IsFolder', 'true')
        self.li.setIconImage('DefaultFolder.png')
        self.li.setProperty('IsPlayable', 'false')
        self.li.setLabel(self['Title'])
        self.li.setInfo('pictures', metadata)
        self.li.setContentLookup(False)


class Video(BaseListItem):

    def __init__(self, *args, **kwargs):

        BaseListItem.__init__(self, 'BrowseVideo', 'ArtworkParent', True, *args, **kwargs)

        if 'PlaybackInfo' in self.item:

            if self.item['LI']['Seektime']:
                self.item['PlaybackInfo']['CurrentPosition'] = self['Resume']

            if 'SubtitleUrl' in self.item['PlaybackInfo']:

                LOG.info("[ subtitles ] %s", self.item['PlaybackInfo']['SubtitleUrl'])
                self.li.setSubtitles([self.item['PlaybackInfo']['SubtitleUrl']])

    def format(self):

        self['Genres'] = " / ".join(self['Genres'] or [])
        self['Studios'] = [self.api.validate_studio(studio) for studio in (self['Studios'] or [])]
        self['Studios'] = " / ".join(self['Studios'])
        self['Mpaa'] = self.api.get_mpaa(self['Mpaa'])
        self['People'] = self['People'] or []
        self['Countries'] = " / ".join(self['Countries'] or [])
        self['Directors'] = " / ".join(self['Directors'] or [])
        self['Writers'] = " / ".join(self['Writers'] or [])
        self['Plot'] = self.api.get_overview(self['Plot'])
        self['ShortPlot'] = self.api.get_overview(self['ShortPlot'])
        self['DateAdded'] = self['DateAdded'].split('.')[0].replace('T', " ")
        self['Rating'] = self['Rating'] or 0
        self['FileDate'] = "%s.%s.%s" % tuple(reversed(self['DateAdded'].split('T')[0].split('-')))
        self['Runtime'] = round(float((self['Runtime'] or 0) / 10000000.0), 6)
        self['Resume'] = self.api.adjust_resume((self['Resume'] or 0) / 10000000.0)
        self['PlayCount'] = self.api.get_playcount(self['Played'], self['PlayCount']) or 0
        self['Overlay'] = 7 if self['Played'] else 6
        self['Video'] = self.api.video_streams(self['Video'] or [], self['Container'])
        self['Audio'] = self.api.audio_streams(self['Audio'] or [])
        self['Streams'] = self.api.media_streams(self['Video'], self['Audio'], self['Subtitles'])
        self['ChildCount'] = self['ChildCount'] or 0
        self['RecursiveCount'] = self['RecursiveCount'] or 0
        self['Unwatched'] = self['Unwatched'] or 0
        self['Artwork']['Backdrop'] = self['Artwork']['Backdrop'] or []
        self['Artwork']['Thumb'] = self['Artwork']['Thumb'] or ""
        self['Artwork']['Primary'] = self['Artwork']['Primary'] or "special://home/addons/plugin.video.emby/icon.png"

        if self['Premiere']:
            self['Premiere'] = self['Premiere'].split('T')[0]

        if self['DatePlayed']:
            self['DatePlayed'] = self['DatePlayed'].split('.')[0].replace('T', " ")

    def set(self):

        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "video",
            'lastplayed': self['DatePlayed'],
            'year': self['Year'],
            'duration': self['Runtime']
        }
        self.li.setCast(self.api.get_actors())
        self.set_playable()
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

    def set_playable(self):

        self.li.setProperty('totaltime', str(self['Runtime']))
        self.li.setProperty('IsPlayable', 'true')
        self.li.setProperty('IsFolder', 'false')

        if self['Resume'] and self['Runtime'] and self.item['LI']['Seektime'] != False:

            self.li.setProperty('resumetime', str(self['Resume']))
            self.li.setProperty('StartPercent', str(((self['Resume']/self['Runtime']) * 100) - 0.40))
        else:
            self.li.setProperty('resumetime', '0')

        for track in self['Streams']['video']:
            self.li.addStreamInfo('video', {
                'duration': self['Runtime'],
                'aspect': track['aspect'],
                'codec': track['codec'],
                'width': track['width'],
                'height': track['height']
            })

        for track in self['Streams']['audio']:
            self.li.addStreamInfo('audio', {'codec': track['codec'], 'channels': track['channels']})

        for track in self['Streams']['subtitle']:
            self.li.addStreamInfo('subtitle', {'language': track})


class Audio(Music):

    def __init__(self, *args, **kwargs):
        Music.__init__(self, *args, **kwargs)

    def set(self):

        metadata = {
            'title': self['Title'],
            'genre': self['Genre'],
            'year': self['Year'],
            'album': self['Album'],
            'artist': self['Artists'],
            'rating': self['Rating'],
            'comment': self['Comment'],
            'date': self['FileDate'],
            'mediatype': "song",
            'tracknumber': self['Index'],
            'discnumber': self['Disc'],
            'duration': self['Runtime'],
            'playcount': self['PlayCount'],
            'lastplayed': self['DatePlayed'],
            'musicbrainztrackid': self['UniqueId']
        }
        self.set_art()
        self.li.setProperty('IsPlayable', 'true')
        self.li.setProperty('IsFolder', 'false')
        self.li.setLabel(self['Title'])
        self.li.setInfo('music', metadata)
        self.li.setContentLookup(False)

class Album(Music):

    def __init__(self, *args, **kwargs):
        Music.__init__(self, *args, **kwargs)

    def set(self):

        metadata = {
            'title': self['Title'],
            'genre': self['Genre'],
            'year': self['Year'],
            'album': self['Album'],
            'artist': self['Artists'],
            'rating': self['Rating'],
            'comment': self['Comment'],
            'date': self['FileDate'],
            'mediatype': "album",
            'musicbrainzalbumid': self['UniqueId']
        }
        self.set_art()
        self.li.setLabel(self['Title'])
        self.li.setInfo('music', metadata)
        self.li.setContentLookup(False)

class Artist(Music):

    def __init__(self, *args, **kwargs):
        Music.__init__(self, *args, **kwargs)

    def set(self):

        metadata = {
            'title': self['Title'],
            'genre': self['Genre'],
            'year': self['Year'],
            'album': self['Album'],
            'artist': self['Artists'],
            'rating': self['Rating'],
            'comment': self['Comment'],
            'date': self['FileDate'],
            'mediatype': "artist",
            'musicbrainzartistid': self['UniqueId']
        }
        self.set_art()
        self.li.setLabel(self['Title'])
        self.li.setInfo('music', metadata)
        self.li.setContentLookup(False)


class Episode(Video):

    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    @classmethod
    def art(cls):
        return  {
            'poster': "Series.Primary",
            'tvshow.poster': "Series.Primary",
            'clearart': "Art",
            'tvshow.clearart': "Art",
            'clearlogo': "Logo",
            'tvshow.clearlogo': "Logo",
            'discart': "Disc",
            'fanart_image': "Backdrop",
            'landscape': "Thumb",
            'tvshow.landscape': "Thumb",
            'thumb': "Primary",
            'fanart': "Backdrop"
        }

    def set(self):
        
        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "episode",
            'tvshowtitle': self['SeriesName'],
            'season': self['Season'] or 0,
            'sortseason': self['Season'] or 0,
            'episode': self['Index'] or 0,
            'sortepisode': self['Index'] or 0,
            'lastplayed': self['DatePlayed'],
            'duration': self['Runtime'],
            'aired': self['Premiere']
        }
        self.li.setCast(self.api.get_actors())
        self.set_playable()
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

        if 'PlaybackInfo' in self.item:

            self.item['PlaybackInfo']['CurrentEpisode'] = self.objects.map(self.item, "UpNext")
            self.item['PlaybackInfo']['CurrentEpisode']['art'] = {
                'tvshow.poster': self['Artwork'].get('Series.Primary'),
                'thumb': self['Artwork'].get('Primary'),
                'tvshow.fanart': None
            }
            if self['Artwork']['Backdrop']:
                self.item['PlaybackInfo']['CurrentEpisode']['art']['tvshow.fanart'] = self['Artwork']['Backdrop'][0]

class Season(Video):

    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    def set(self):
        
        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "season",
            'tvshowtitle': self['SeriesName'],
            'season': self['Index'] or 0,
            'sortseason': self['Index'] or 0
        }
        self.li.setCast(self.api.get_actors())
        self.li.setProperty('NumEpisodes', str(self['RecursiveCount']))
        self.li.setProperty('WatchedEpisodes', str(self['RecursiveCount'] - self['Unwatched']))
        self.li.setProperty('UnWatchedEpisodes', str(self['Unwatched']))
        self.li.setProperty('IsFolder', 'true')
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

class Series(Video):

    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    def format(self):
        super(Series, self).format()

        if self['Status'] != 'Ended':
            self['Status'] = None

    def set(self):
        
        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "tvshow",
            'tvshowtitle': self['Title'],
            'status': self['Status']
        }
        self.li.setCast(self.api.get_actors())

        self.li.setProperty('TotalSeasons', str(self['ChildCount']))
        self.li.setProperty('TotalEpisodes', str(self['RecursiveCount']))
        self.li.setProperty('WatchedEpisodes', str(self['RecursiveCount'] - self['Unwatched']))
        self.li.setProperty('UnWatchedEpisodes', str(self['Unwatched']))
        self.li.setProperty('IsFolder', 'true')
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

class Movie(Video):

    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    def set(self):
        
        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "movie",
            'imdbnumber': self['UniqueId'],
            'lastplayed': self['DatePlayed'],
            'duration': self['Runtime'],
            'userrating': self['CriticRating']
        }
        self.li.setCast(self.api.get_actors())
        self.set_playable()
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

class BoxSet(Video):

    def __init__(self,*args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    def set(self):
        
        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "set"
        }
        self.li.setCast(self.api.get_actors())
        self.li.setProperty('IsFolder', 'true')
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

class MusicVideo(Video):

    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    def set(self):
        
        self.set_art()
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'dbid': self.item['LI']['DbId'],
            'mediatype': "musicvideo",
            'album': self['Album'],
            'artist': self['Artists'] or [],
            'lastplayed': self['DatePlayed'],
            'duration': self['Runtime']
        }
        self.li.setCast(self.api.get_actors())
        self.set_playable()
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

class Intro(Video):

    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

    def format(self):

        self['Artwork']['Primary'] = self['Artwork']['Primary'] or self['Artwork']['Thumb'] or (self['Artwork']['Backdrop'][0] if len(self['Artwork']['Backdrop']) else "special://home/addons/plugin.video.emby/fanart.jpg")
        self['Artwork']['Primary'] += "&KodiCinemaMode=true"
        self['Artwork']['Backdrop'] = [self['Artwork']['Primary']]

        super(Intro, self).format()

    def set(self):
        
        self.set_art()
        self.li.setArt({'poster': ""}) # Clear the poster value for intros / trailers to prevent issues in skins
        self.li.setIconImage('DefaultVideo.png')
        self.li.setThumbnailImage(self['Artwork']['Primary'])

        metadata = {
            'title': self['Title'],
            'originaltitle': self['Title'],
            'sorttitle': self['SortTitle'],
            'country': self['Countries'],
            'genre': self['Genres'],
            'year': self['Year'],
            'rating': self['Rating'],
            'playcount': self['PlayCount'],
            'overlay': self['Overlay'],
            'director': self['Directors'],
            'mpaa': self['Mpaa'],
            'plot': self['Plot'],
            'plotoutline': self['ShortPlot'],
            'studio': self['Studios'],
            'tagline': self['Tagline'],
            'writer': self['Writers'],
            'premiered': self['Premiere'],
            'votes': self['Votes'],
            'dateadded': self['DateAdded'],
            'aired': self['Year'],
            'date': self['Premiere'] or self['FileDate'],
            'mediatype': "video",
            'lastplayed': self['DatePlayed'],
            'year': self['Year'],
            'duration': self['Runtime']
        }
        self.li.setCast(self.api.get_actors())
        self.set_playable()
        self.li.setLabel(self['Title'])
        self.li.setInfo('video', metadata)
        self.li.setContentLookup(False)

class Trailer(Intro):

    def __init__(self, *args, **kwargs):
        Intro.__init__(self, *args, **kwargs)

    def format(self):

        self['Artwork']['Primary'] = self['Artwork']['Primary'] or self['Artwork']['Thumb'] or (self['Artwork']['Backdrop'][0] if len(self['Artwork']['Backdrop']) else "special://home/addons/plugin.video.emby/fanart.jpg")
        self['Artwork']['Primary'] += "&KodiTrailer=true"
        self['Artwork']['Backdrop'] = [self['Artwork']['Primary']]

        Video.format(self)


#################################################################################################

MUSIC = {
    'Artist': Artist,
    'MusicArtist': Artist,
    'MusicAlbum': Album,
    'Audio': Audio,
    'Music': Music
}
PHOTO = {
    'Photo': Photo,
    'PhotoAlbum': PhotoAlbum
}
VIDEO = {
    'Episode': Episode,
    'Season': Season,
    'Series': Series,
    'Movie': Movie,
    'MusicVideo': MusicVideo,
    'BoxSet': BoxSet,
    'Trailer': Trailer,
    'AudioBook': Video,
    'Video': Video,
    'Intro': Intro
}
BASIC = {
    'Playlist': Playlist,
    'TvChannel': Channel
}

#################################################################################################


class ListItem(object):

    ''' Translate an emby item into a Kodi listitem.
        Returns the listitem
    '''
    def __init__(self, server_addr, *args, **kwargs):
        self.server = server_addr

    def _detect_type(self, item):
        item_type = item['Type']

        for typ in (VIDEO, MUSIC, PHOTO, BASIC):
            if item_type in typ:
                return typ[item_type]
        else:
            return VIDEO['Video']

    def set(self, item, listitem=None, db_id=None, intro=False, seektime=None, *args, **kwargs):
        
        listitem = listitem or xbmcgui.ListItem()
        item['LI'] = {
            'DbId': db_id,
            'Seektime': seektime,
            'Server': self.server
        }
        if intro:
            func = VIDEO['Trailer'] if item['Type'] == 'Trailer' else VIDEO['Intro']
        else:
            func = self._detect_type(item)

        func(listitem, item, *args, **kwargs)
        item.pop('LI')

        return listitem
