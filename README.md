# Emby for Kodi: objects

[![EmbyKodi_Banner](https://i.imgur.com/Qu6ee1w.png)](https://emby.media/community/index.php?/forum/99-kodi/) 

[![Wiki](https://img.shields.io/badge/main-emby%20for%20kodi-brightgreen.svg)](https://github.com/MediaBrowser/plugin.video.emby)

___
This repo contains everything to do with running Emby for Kodi on targetted Kodi versions, such as database queries, playback elements and Emby to Kodi content translation.

### Important files 
**obj_map.json**: Contains the assigned Emby value to Kodi database keys.  
**obj.py**: Reads obj_map.json. Essentially, takes an Emby item and converts it into an Objects filled with needed values.
**movies.py, tvshows.py, music.py, musicvideos.py**: Contains functions called when Emby content is updated, use objects and database functions.  
**/kodi/queries(_music,_texture).py**: Contains the database queries and mapping of database fields.
___

### Supported

- Krypton (17.6)
- Leia (18.1+)
