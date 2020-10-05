# -*- coding: utf-8 -*-

##################################################################################################

import json
import logging
import sqlite3
import urllib
from ntpath import dirname

import downloader as server
from objects.core import Objects
from objects.kodi import TVShows as KodiDb, queries as QU
from database import emby_db, queries as QUEM
from helper import api, catch, stop, validate, emby_item, library_check, settings, values, Local

##################################################################################################

LOG = logging.getLogger("EMBY."+__name__)

##################################################################################################


class TVShows(KodiDb):

    def __init__(self, server, embydb, videodb, direct_path, update_library=False, *args, **kwargs):

        self.server = server
        self.emby = embydb
        self.video = videodb
        self.direct_path = direct_path
        self.update_library = update_library

        self.emby_db = emby_db.EmbyDatabase(embydb.cursor)
        self.objects = Objects()
        self.item_ids = []
        self.display_specials = settings('SeasonSpecials.bool')
        self.display_multiep = settings('displayMultiEpLabel.bool')

        KodiDb.__init__(self, videodb.cursor)

    def __getitem__(self, key):

        if key == 'Series':
            return self.tvshow
        elif key == 'Season':
            return self.season
        elif key == 'Episode':
            return self.episode
        elif key == 'UserData':
            return self.userdata
        elif key in 'Removed':
            return self.remove

    @stop()
    @emby_item()
    @library_check()
    def tvshow(self, item, e_item, library, pooling=None, redirect=False, *args, **kwargs):

        ''' If item does not exist, entry will be added.
            If item exists, entry will be updated.

            If the show is empty, try to remove it.
            Process seasons.
            Apply series pooling.
        '''
        API = api.API(item, self.server['auth/server-address'])
        obj = self.objects.map(item, 'Series')
        obj['Item'] = item
        obj['Library'] = library
        obj['LibraryId'] = library['Id']
        obj['LibraryName'] = library['Name']
        update = True

        if not settings('syncEmptyShows.bool') and not obj['RecursiveCount']:

            LOG.info("Skipping empty show %s: %s", obj['Title'], obj['Id'])
            TVShows(self.server, self.emby, self.video, self.direct_path, False).remove(obj['Id'])

            return False

        if pooling is None:
            verify = False

            if obj['PresentationKey']: # 4.2.0.23+

                verify = True
                obj['Item']['Id'] = self.emby_db.get_stack(obj['PresentationKey']) or obj['Id']

            elif not self.update_library: # older server

                verify = True
                obj['Item']['Id'] = self.server['api'].is_valid_series(obj['LibraryId'], obj['Title'], obj['Id'])

            if verify:

                if str(obj['Item']['Id']) != obj['Id']:
                    return TVShows(self.server, self.emby, self.video, self.direct_path, False).tvshow(obj['Item'], library=obj['Library'], pooling=obj['Id'])

        try:
            obj['ShowId'] = e_item[0]
            obj['PathId'] = e_item[2]
        except TypeError as error:
            update = False
            LOG.debug("ShowId %s not found", obj['Id'])
            obj['ShowId'] = self.create_entry()
        else:
            if self.get(*values(obj, QU.get_tvshow_obj)) is None:

                update = False
                LOG.info("ShowId %s missing from kodi. repairing the entry.", obj['ShowId'])


        obj['Path'] = API.get_file_path(obj['Path'])
        obj['Genres'] = obj['Genres'] or []
        obj['People'] = obj['People'] or []
        obj['Mpaa'] = API.get_mpaa(obj['Mpaa'])
        obj['Studios'] = [API.validate_studio(studio) for studio in (obj['Studios'] or [])]
        obj['Genre'] = " / ".join(obj['Genres'])
        obj['People'] = API.get_people_artwork(obj['People'])
        obj['Plot'] = API.get_overview(obj['Plot'])
        obj['Studio'] = " / ".join(obj['Studios'])
        obj['Artwork'] = API.get_all_artwork(self.objects.map(item, 'Artwork'))

        if obj['Status'] != 'Ended':
            obj['Status'] = None

        if not self.get_path_filename(obj):
            return

        if obj['Premiere']:
            obj['Premiere'] = str(Local(obj['Premiere'])).split('.')[0].replace('T', " ")

        tags = []
        tags.extend(obj['TagItems'] or obj['Tags'] or [])
        tags.append(obj['LibraryName'])

        if obj['Favorite']:
            tags.append('Favorite tvshows')

        obj['Tags'] = tags


        if update:
            self.tvshow_update(obj)
        else:
            self.tvshow_add(obj)


        if pooling:

            obj['SeriesId'] = pooling
            LOG.info("POOL %s [%s/%s]", obj['Title'], obj['Id'], obj['SeriesId'])
            self.emby_db.add_reference(*values(obj, QUEM.add_reference_pool_obj))

            return

        self.link(*values(obj, QU.update_tvshow_link_obj))
        self.update_path(*values(obj, QU.update_path_tvshow_obj))
        self.add_tags(*values(obj, QU.add_tags_tvshow_obj))
        self.add_people(*values(obj, QU.add_people_tvshow_obj))
        self.add_genres(*values(obj, QU.add_genres_tvshow_obj))
        self.add_studios(*values(obj, QU.add_studios_tvshow_obj))
        self.artwork.add(obj['Artwork'], obj['ShowId'], "tvshow")
        self.item_ids.append(obj['Id'])

        if redirect:
            LOG.info("tvshow added as a redirect")

            return

        season_episodes = {}

        try:
            all_seasons = self.server['api'].get_seasons(obj['Id'])['Items']
        except Exception as error:

            LOG.error("Unable to pull seasons for %s", obj['Title'])
            LOG.error(error)

            return

        for season in all_seasons:

            if (self.update_library and season['SeriesId'] != obj['Id']) or (not update and not self.update_library):
                season_episodes[season['Id']] = season.get('SeriesId', obj['Id'])

            try:
                self.emby_db.get_item_by_id(season['Id'])[0]
                self.item_ids.append(season['Id'])
            except TypeError:
                self.season(season, obj['ShowId'])
        else:
            season_id = self.get_season(*values(obj, QU.get_season_special_obj))
            self.artwork.add(obj['Artwork'], season_id, "season")

        for season in season_episodes:
            for episodes in server.get_episode_by_season(season_episodes[season], season):

                for episode in episodes['Items']:
                    self.episode(episode)

    def tvshow_add(self, obj):

        ''' Add object to kodi.
        '''
        obj['RatingId'] = self.create_entry_rating()
        self.add_ratings(*values(obj, QU.add_rating_tvshow_obj))

        obj['Unique'] = self.create_entry_unique_id()
        self.add_unique_id(*values(obj, QU.add_unique_id_tvshow_obj))

        for provider in obj['UniqueIds'] or {}:

            unique_id = obj['UniqueIds'][provider]
            provider = provider.lower()

            if provider != 'tvdb':
                temp_obj = dict(obj, ProviderName=provider, UniqueId=unique_id, Unique=self.create_entry_unique_id())
                self.add_unique_id(*values(temp_obj, QU.add_unique_id_tvshow_obj))

        obj['TopPathId'] = self.add_path(obj['TopLevel'])
        self.update_path(*values(obj, QU.update_path_toptvshow_obj))

        obj['PathId'] = self.add_path(*values(obj, QU.get_path_obj))

        self.add(*values(obj, QU.add_tvshow_obj))
        self.emby_db.add_reference(*values(obj, QUEM.add_reference_tvshow_obj))
        LOG.info("ADD tvshow [%s/%s/%s] %s: %s", obj['TopPathId'], obj['PathId'], obj['ShowId'], obj['Id'], obj['Title'])

    def tvshow_update(self, obj):
        
        ''' Update object to kodi.
        '''
        obj['RatingId'] = self.get_rating_id(*values(obj, QU.get_rating_tvshow_obj))
        self.update_ratings(*values(obj, QU.update_rating_tvshow_obj))

        self.remove_unique_ids(*values(obj, QU.delete_unique_ids_tvshow_obj))

        obj['Unique'] = self.create_entry_unique_id()
        self.add_unique_id(*values(obj, QU.add_unique_id_tvshow_obj))

        for provider in obj['UniqueIds'] or {}:

            unique_id = obj['UniqueIds'][provider]
            provider = provider.lower()

            if provider != 'tvdb':
                temp_obj = dict(obj, ProviderName=provider, UniqueId=unique_id, Unique=self.create_entry_unique_id())
                self.add_unique_id(*values(temp_obj, QU.add_unique_id_tvshow_obj))

        self.update(*values(obj, QU.update_tvshow_obj))
        self.emby_db.update_reference(*values(obj, QUEM.update_reference_obj))
        LOG.info("UPDATE tvshow [%s/%s] %s: %s", obj['PathId'], obj['ShowId'], obj['Id'], obj['Title'])

    def get_path_filename(self, obj):

        ''' Get the path and build it into protocol://path
        '''
        if not obj['Path']:
            LOG.info("Path is missing")

            return False

        if self.direct_path:

            if '\\' in obj['Path']:
                obj['Path'] = "%s\\" % obj['Path']
                obj['TopLevel'] = "%s\\" % dirname(dirname(obj['Path']))
            else:
                obj['Path'] = "%s/" % obj['Path']
                obj['TopLevel'] = "%s/" % dirname(dirname(obj['Path']))

            if not validate(obj['Path']):
                raise Exception("Failed to validate path. User stopped.")
        else:
            obj['TopLevel'] = "http://127.0.0.1:57578/emby/kodi/tvshows/"
            obj['Path'] = "%s%s/" % (obj['TopLevel'], obj['Id'])

        return True


    @stop()
    def season(self, item, show_id=None, *args, **kwargs):

        ''' If item does not exist, entry will be added.
            If item exists, entry will be updated.

            If the show is empty, try to remove it.
        '''
        API = api.API(item, self.server['auth/server-address'])
        obj = self.objects.map(item, 'Season')

        obj['ShowId'] = show_id
        if obj['ShowId'] is None:

            if not self.get_show_id(obj):
                return False

        obj['SeasonId'] = self.get_season(*values(obj, QU.get_season_obj))
        obj['Artwork'] = API.get_all_artwork(self.objects.map(item, 'Artwork'))

        if obj['Location'] != 'Virtual':

            self.emby_db.add_reference(*values(obj, QUEM.add_reference_season_obj))
            self.item_ids.append(obj['Id'])

        self.artwork.add(obj['Artwork'], obj['SeasonId'], "season")
        LOG.info("UPDATE season [%s/%s] %s: %s", obj['ShowId'], obj['SeasonId'], obj['Title'] or obj['Index'], obj['Id'])


    @stop()
    @emby_item()
    def episode(self, item, e_item, *args, **kwargs):

        ''' If item does not exist, entry will be added.
            If item exists, entry will be updated.

            Create additional entry for widgets.
            This is only required for plugin/episode.
        '''
        API = api.API(item, self.server['auth/server-address'])
        obj = self.objects.map(item, 'Episode')
        obj['Item'] = item
        update = True
        verify = False

        if obj['Location'] == 'Virtual':
            LOG.info("Skipping virtual episode %s: %s", obj['Title'], obj['Id'])

            return

        elif obj['SeriesId'] is None:
            LOG.info("Skipping episode %s with missing SeriesId", obj['Id'])

            return

        if obj['PresentationKey']: # 4.2.0.23+

            verify = True
            obj['Item']['Id'] = self.emby_db.get_stack(obj['PresentationKey']) or obj['Id']

        elif not self.update_library: # older server

            verify = True
            obj['Item']['Id'] = self.server['api'].is_valid_episode(obj['SeriesId'], obj['Title'], obj['Id'])

        if verify:
            if str(obj['Item']['Id']) != obj['Id']:

                LOG.info("Skipping stacked episode %s [%s]", obj['Title'], obj['Id'])
                TVShows(self.server, self.emby, self.video, self.direct_path, False).remove(obj['Id'])

                return False

        try:
            obj['EpisodeId'] = e_item[0]
            obj['FileId'] = e_item[1]
            obj['PathId'] = e_item[2]
        except TypeError as error:
            update = False
            LOG.debug("EpisodeId %s not found", obj['Id'])
            obj['EpisodeId'] = self.create_entry_episode()
        else:
            if self.get_episode(*values(obj, QU.get_episode_obj)) is None:

                update = False
                LOG.info("EpisodeId %s missing from kodi. repairing the entry.", obj['EpisodeId'])


        obj['Path'] = API.get_file_path(obj['Path'])
        obj['Index'] = obj['Index'] or -1
        obj['Writers'] = " / ".join(obj['Writers'] or [])
        obj['Directors'] = " / ".join(obj['Directors'] or [])
        obj['Plot'] = API.get_overview(obj['Plot'])
        obj['Resume'] = API.adjust_resume((obj['Resume'] or 0) / 10000000.0)
        obj['Runtime'] = round(float((obj['Runtime'] or 0) / 10000000.0), 6)
        obj['People'] = API.get_people_artwork(obj['People'] or [])
        obj['DateAdded'] = Local(obj['DateAdded']).split('.')[0].replace('T', " ")
        obj['DatePlayed'] = None if not obj['DatePlayed'] else Local(obj['DatePlayed']).split('.')[0].replace('T', " ")
        obj['PlayCount'] = API.get_playcount(obj['Played'], obj['PlayCount'])
        obj['Artwork'] = API.get_all_artwork(self.objects.map(item, 'Artwork'))
        obj['Video'] = API.video_streams(obj['Video'] or [], obj['Container'])
        obj['Audio'] = API.audio_streams(obj['Audio'] or [])
        obj['Streams'] = API.media_streams(obj['Video'], obj['Audio'], obj['Subtitles'])

        if not self.get_episode_path_filename(obj):
            return

        if obj['Premiere']:
            obj['Premiere'] = Local(obj['Premiere']).split('.')[0].replace('T', " ")

        if obj['Season'] is None:
            if obj['AbsoluteNumber']:

                obj['Season'] = 1
                obj['Index'] = obj['AbsoluteNumber']
            else:
                obj['Season'] = 0

        if self.display_specials and not obj['Season']: # Only add for special episodes
            if obj['AirsAfterSeason']:

                obj['AirsBeforeSeason'] = obj['AirsAfterSeason']
                obj['AirsBeforeEpisode'] = 4096 # Kodi default number for afterseason ordering
        else:
            obj['AirsBeforeSeason'] = None
            obj['AirsBeforeEpisode'] = None

        if obj['MultiEpisode'] and self.display_multiep:
            obj['Title'] = "| %02d | %s" % (obj['MultiEpisode'], obj['Title'])

        if not self.get_show_id(obj):
            LOG.info("No series id associated")

            return False

        obj['SeasonId'] = self.get_season(*values(obj, QU.get_season_episode_obj))


        if update:
            self.episode_update(obj)
        else:
            self.episode_add(obj)


        self.update_path(*values(obj, QU.update_path_episode_obj))
        self.update_file(*values(obj, QU.update_file_obj))
        self.add_people(*values(obj, QU.add_people_episode_obj))
        self.add_streams(*values(obj, QU.add_streams_obj))
        self.add_playstate(*values(obj, QU.add_bookmark_obj))
        self.artwork.update(obj['Artwork']['Primary'], obj['EpisodeId'], "episode", "thumb")
        self.item_ids.append(obj['Id'])

        return not update

    def episode_add(self, obj):
        
        ''' Add object to kodi.
        '''
        obj['RatingId'] = self.create_entry_rating()
        self.add_ratings(*values(obj, QU.add_rating_episode_obj))

        obj['Unique'] = self.create_entry_unique_id()
        self.add_unique_id(*values(obj, QU.add_unique_id_episode_obj))

        for provider in obj['UniqueIds'] or {}:

            unique_id = obj['UniqueIds'][provider]
            provider = provider.lower()

            if provider != 'tvdb':
                temp_obj = dict(obj, ProviderName=provider, UniqueId=unique_id, Unique=self.create_entry_unique_id())
                self.add_unique_id(*values(temp_obj, QU.add_unique_id_episode_obj))

        obj['PathId'] = self.add_path(*values(obj, QU.add_path_obj))
        obj['FileId'] = self.add_file(*values(obj, QU.add_file_obj))

        try: # TODO Remove as it's not needed, but make sure first.
            self.add_episode(*values(obj, QU.add_episode_obj))
        except sqlite3.IntegrityError as error:

            LOG.error("IntegrityError for %s", obj)
            obj['EpisodeId'] = self.create_entry_episode()

            return self.episode_add(obj)

        self.emby_db.add_reference(*values(obj, QUEM.add_reference_episode_obj))
        LOG.info("ADD episode [%s/%s/%s/%s] %s: %s", obj['ShowId'], obj['SeasonId'], obj['EpisodeId'], obj['FileId'], obj['Id'], obj['Title'])

    def episode_update(self, obj):
        
        ''' Update object to kodi.
        '''        
        obj['RatingId'] = self.get_rating_id(*values(obj, QU.get_rating_episode_obj))
        self.update_ratings(*values(obj, QU.update_rating_episode_obj))

        self.remove_unique_ids(*values(obj, QU.delete_unique_ids_episode_obj))

        obj['Unique'] = self.create_entry_unique_id()
        self.add_unique_id(*values(obj, QU.add_unique_id_episode_obj))

        for provider in obj['UniqueIds'] or {}:

            unique_id = obj['UniqueIds'][provider]
            provider = provider.lower()

            if provider != 'tvdb':
                temp_obj = dict(obj, ProviderName=provider, UniqueId=unique_id, Unique=self.create_entry_unique_id())
                self.add_unique_id(*values(temp_obj, QU.add_unique_id_episode_obj))

        self.update_episode(*values(obj, QU.update_episode_obj))

        self.emby_db.update_reference(*values(obj, QUEM.update_reference_obj))
        self.emby_db.update_parent_id(*values(obj, QUEM.update_parent_episode_obj))
        LOG.info("UPDATE episode [%s/%s/%s/%s] %s: %s", obj['ShowId'], obj['SeasonId'], obj['EpisodeId'], obj['FileId'], obj['Id'], obj['Title'])

    def get_episode_path_filename(self, obj):

        ''' Get the path and build it into protocol://path
        '''
        if not obj['Path']:
            LOG.info("Path is missing")

            return False

        if '\\' in obj['Path']:
            obj['Filename'] = obj['Path'].rsplit('\\', 1)[1]
        else:
            obj['Filename'] = obj['Path'].rsplit('/', 1)[1]

        if self.direct_path:

            if not validate(obj['Path']):
                raise Exception("Failed to validate path. User stopped.")

            obj['Path'] = obj['Path'].replace(obj['Filename'], "")
        else:
            obj['Path'] = "http://127.0.0.1:57578/emby/kodi/tvshows/%s/" % obj['SeriesId']
            params = {
                'Name': obj['Filename'].encode('utf-8'),
                'KodiId': obj['EpisodeId'],
                'Id': obj['Id']
            }
            obj['Filename'] = "%s/file.strm?%s" % (obj['Id'], urllib.urlencode(params))

        return True

    def get_show_id(self, obj):

        if obj.get('ShowId'):
            return True

        obj['ShowId'] = self.emby_db.get_item_by_id(*values(obj, QUEM.get_item_series_obj))
        if obj['ShowId'] is None:

            try:
                TVShows(self.server, self.emby, self.video, self.direct_path, False).tvshow(self.server['api'].get_item(obj['SeriesId']), library=None, redirect=True)
                obj['ShowId'] = self.emby_db.get_item_by_id(*values(obj, QUEM.get_item_series_obj))[0]
            except (TypeError, KeyError):
                LOG.error("Unable to add series %s", obj['SeriesId'])

                return False
        else:
            obj['ShowId'] = obj['ShowId'][0]

        self.item_ids.append(obj['SeriesId'])

        return True


    @stop()
    @emby_item()
    def userdata(self, item, e_item, *args, **kwargs):
        
        ''' This updates: Favorite, LastPlayedDate, Playcount, PlaybackPositionTicks
            Poster with progress bar

            Make sure there's no other bookmarks created by widget.
            Create additional entry for widgets. This is only required for plugin/episode.
        '''
        API = api.API(item, self.server['auth/server-address'])
        obj = self.objects.map(item, 'EpisodeUserData')

        try:
            obj['KodiId'] = e_item[0]
            obj['FileId'] = e_item[1]
            obj['Media'] = e_item[4]
        except TypeError:
            return

        if obj['Media'] == "tvshow":

            if obj['Favorite']:
                self.get_tag(*values(obj, QU.get_tag_episode_obj))
            else:
                self.remove_tag(*values(obj, QU.delete_tag_episode_obj))

        elif obj['Media'] == "episode":
            
            obj['Resume'] = API.adjust_resume((obj['Resume'] or 0) / 10000000.0)
            obj['Runtime'] = round(float((obj['Runtime'] or 0) / 10000000.0), 6)
            obj['PlayCount'] = API.get_playcount(obj['Played'], obj['PlayCount'])

            if obj['DatePlayed']:
                obj['DatePlayed'] = Local(obj['DatePlayed']).split('.')[0].replace('T', " ")

            if obj['DateAdded']:
                obj['DateAdded'] = Local(obj['DateAdded']).split('.')[0].replace('T', " ")

            self.add_playstate(*values(obj, QU.add_bookmark_obj))

        self.emby_db.update_reference(*values(obj, QUEM.update_reference_obj))
        LOG.info("USERDATA %s [%s/%s] %s: %s", obj['Media'], obj['FileId'], obj['KodiId'], obj['Id'], obj['Title'])

    @stop()
    @emby_item()
    def remove(self, item_id, e_item, *args, **kwargs):
        
        ''' Remove showid, fileid, pathid, emby reference.
            There's no episodes left, delete show and any possible remaining seasons
        '''
        obj = {'Id': item_id}

        try:
            obj['KodiId'] = e_item[0]
            obj['FileId'] = e_item[1]
            obj['ParentId'] = e_item[3]
            obj['Media'] = e_item[4]
        except TypeError:
            return

        if obj['Media'] == 'episode':

            temp_obj = dict(obj)
            self.remove_episode(obj['KodiId'], obj['FileId'], obj['Id'])
            season = self.emby_db.get_full_item_by_kodi_id(*values(obj, QUEM.delete_item_by_parent_season_obj))

            try:
                temp_obj['Id'] = season[0]
                temp_obj['ParentId'] = season[1]
            except TypeError:
                return

            if not self.emby_db.get_item_by_parent_id(*values(obj, QUEM.get_item_by_parent_episode_obj)):

                self.remove_season(obj['ParentId'], obj['Id'])
                self.emby_db.remove_item(*values(temp_obj, QUEM.delete_item_obj))

            temp_obj['Id'] = self.emby_db.get_item_by_kodi_id(*values(temp_obj, QUEM.get_item_by_parent_tvshow_obj))

            if not self.get_total_episodes(*values(temp_obj, QU.get_total_episodes_obj)):

                for season in self.emby_db.get_item_by_parent_id(*values(temp_obj, QUEM.get_item_by_parent_season_obj)):
                    self.remove_season(season[1], obj['Id'])
                else:
                    self.emby_db.remove_items_by_parent_id(*values(temp_obj, QUEM.delete_item_by_parent_season_obj))

                self.remove_tvshow(temp_obj['ParentId'], obj['Id'])
                self.emby_db.remove_item(*values(temp_obj, QUEM.delete_item_obj))

        elif obj['Media'] == 'tvshow':
            obj['ParentId'] = obj['KodiId']

            for season in self.emby_db.get_item_by_parent_id(*values(obj, QUEM.get_item_by_parent_season_obj)):
                temp_obj = dict(obj)
                temp_obj['ParentId'] = season[1]

                for episode in self.emby_db.get_item_by_parent_id(*values(temp_obj, QUEM.get_item_by_parent_episode_obj)):
                    self.remove_episode(episode[1], episode[2], obj['Id'])
                else:
                    self.emby_db.remove_items_by_parent_id(*values(temp_obj, QUEM.delete_item_by_parent_episode_obj))
            else:
                self.emby_db.remove_items_by_parent_id(*values(obj, QUEM.delete_item_by_parent_season_obj))

            self.remove_tvshow(obj['KodiId'], obj['Id'])

        elif obj['Media'] == 'season':
            obj['ParentId'] = obj['KodiId']

            for episode in self.emby_db.get_item_by_parent_id(*values(obj, QUEM.get_item_by_parent_episode_obj)):
                self.remove_episode(episode[1], episode[2], obj['Id'])
            else:
                self.emby_db.remove_items_by_parent_id(*values(obj, QUEM.delete_item_by_parent_episode_obj))

            self.remove_season(obj['KodiId'], obj['Id'])

            if not self.emby_db.get_item_by_parent_id(*values(obj, QUEM.delete_item_by_parent_season_obj)):

                self.remove_tvshow(obj['ParentId'], obj['Id'])
                self.emby_db.remove_item_by_kodi_id(*values(obj, QUEM.delete_item_by_parent_tvshow_obj))

        # Remove any series pooling episodes
        for episode in self.emby_db.get_media_by_parent_id(obj['Id']):
            self.remove_episode(episode[2], episode[3], obj['Id'])
        else:
            self.emby_db.remove_media_by_parent_id(obj['Id'])

        self.emby_db.remove_item(*values(obj, QUEM.delete_item_obj))

    def remove_tvshow(self, kodi_id, item_id):
        
        self.artwork.delete(kodi_id, "tvshow")
        self.delete_tvshow(kodi_id)
        self.emby_db.remove_item_by_kodi_id(kodi_id, "tvshow")
        LOG.info("DELETE tvshow [%s] %s", kodi_id, item_id)

    def remove_season(self, kodi_id, item_id):

        self.artwork.delete(kodi_id, "season")
        self.delete_season(kodi_id)
        self.emby_db.remove_item_by_kodi_id(kodi_id, "season")
        LOG.info("DELETE season [%s] %s", kodi_id, item_id)

    def remove_episode(self, kodi_id, file_id, item_id):

        self.artwork.delete(kodi_id, "episode")
        self.delete_episode(kodi_id, file_id)
        self.emby_db.remove_item_by_kodi_id(kodi_id, "episode")
        LOG.info("DELETE episode [%s/%s] %s", file_id, kodi_id, item_id)

    @emby_item()
    def get_child(self, item_id, e_item, *args, **kwargs):

        ''' Get all child elements from tv show emby id.
        '''
        obj = {'Id': item_id}
        child = []

        try:
            obj['KodiId'] = e_item[0]
            obj['FileId'] = e_item[1]
            obj['ParentId'] = e_item[3]
            obj['Media'] = e_item[4]
        except TypeError:
            return child

        obj['ParentId'] = obj['KodiId']

        for season in self.emby_db.get_item_by_parent_id(*values(obj, QUEM.get_item_by_parent_season_obj)):
            
            temp_obj = dict(obj)
            temp_obj['ParentId'] = season[1]
            child.append(season[0])

            for episode in self.emby_db.get_item_by_parent_id(*values(temp_obj, QUEM.get_item_by_parent_episode_obj)):
                child.append(episode[0])

        for episode in self.emby_db.get_media_by_parent_id(obj['Id']):
            child.append(episode[0])

        return child
