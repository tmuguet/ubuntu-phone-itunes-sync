# iTunes synchronization for the Ubuntu phone

Scripts to synchronize the iTunes library with an Ubuntu Phone, including music files and playlists.


By selecting which iTunes playlists you want to synchronize, the script automatically synchronizes all the tracks from these playlists to your phone and creates the playlists in the Music application.

![Synchronizing](http://thomasmuguet.info/img/pages/projects-2015-04-06-itunes-synchronization-for-the-ubuntu-phone/syncing.png)

![Playlists in the Music app](http://thomasmuguet.info/img/pages/projects-2015-04-06-itunes-synchronization-for-the-ubuntu-phone/screenshot.png)

This script has been tested with latest iTunes (12.3) with a BQ Aquaris 4.5 Ubuntu Edition running OTA 8.5 and Music app 2.2.945. Should work with previous versions (at least iTunes 12.0, Ubuntu r20 and Music app 2.0).


## Requirements

* Network enabled on your computer and on your phone (no need for your phone to be plugged in your computer)
* SSH access to the phone

## Warnings

* This is a one-way sync: playlists created on the phone with the same name as synchronized ones are erased.
* Don't run the Music app during the synchronization, especially when creating the playlists, this can mess up the database
* If lots of files are added (especially true for the first import), `mediascanner-se` can be very slow. Until `mediascanner-se` is finished, playlists may appear broken. Try resyncing later.

## Usage

First, create a `settings.ini` file based on `settings.ini.example` and edit it with a text editor to set the parameters:
* `music_library`: location of your iTunes music library file (default value should be OK)
* `playlists`: names of the playlists you want to synchronize (one per line)
* `check_artwork` (`False`/`True`): whether to check or not if the tracks embed some artwork - requires [mutagen](https://bitbucket.org/lazka/mutagen)
* `music_destination`: destination on your phone for the tracks; a `itunes-sync` subfolder will be created
* `ssh_destination`: SSH user and hostname of your phone (default value should be OK)

Once done, you're ready to go:

* Run in a terminal `./itunes-sync.py`

