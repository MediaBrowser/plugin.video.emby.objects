# Emby for Kodi: objects

[![EmbyKodi_Banner](https://i.imgur.com/Qu6ee1w.png)](https://emby.media/community/index.php?/forum/99-kodi/) 

[![Wiki](https://img.shields.io/badge/main-emby%20for%20kodi-brightgreen.svg)](https://github.com/MediaBrowser/plugin.video.emby)

___
This repo contains everything to do with running Emby for Kodi on targetted Kodi versions, such as database queries, playback elements and Emby to Kodi content translation.
___

### Supported

- Krypton (17.6)
- Leia (18.1+)

___

## Installation

Emby for Kodi will automatically download what it needs to work with your Kodi version.

### Manual installation

#### Grab the right release
Grab the release you need based on [this](https://github.com/MediaBrowser/plugin.video.emby.objects/blob/master/objects.json).
```
{KodiVersion}{VideoDatabase#}{MusicDatabase#}{ObjectsVersion}-{MinimumEmbyForKodiVersion}-{DownloadLink}
```

You can manually download the objects zip using the download link. Grab the **objects folder within the zip** and place it here:
```
/Kodi/userdata/%PROFILE%/addon_data/plugin.video.emby/emby/
```
The directory should align like this:
```
/plugin.video.emby/
|-- emby/
|   |-- objects/
|   |   |-- __init__.py
```
