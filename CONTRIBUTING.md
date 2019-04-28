# How to contribute

Thanks you for contributing to Emby for Kodi!

* Make pull requests towards the **develop** branch to apply changes to the latest Kodi version;
* Make pull requests towards the appropriate branch to apply changes to older Kodi versions only;
* Keep the maximum line length shorter than 120 characters to keep things clean and readable;
* Follow pep8 style as closely as possible: https://www.python.org/dev/peps/pep-0008/
* Add comments if necessary.

### Workflow
TODO

### Important files
TODO
obj_map.json: Contains the assigned Emby value to Kodi database keys.  
obj.py: Reads obj_map.json. Essentially, takes an Emby item and converts it into an Objects filled with needed values.  
movies.py, tvshows.py, music.py, musicvideos.py: Contains functions called when Emby content is updated, use objects and database functions.  
/kodi/queries(_music,_texture).py: Contains the database queries and mapping of database fields.
