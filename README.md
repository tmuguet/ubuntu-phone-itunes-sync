# iTunes synchronization for the Ubuntu phone

Scripts to synchronize the iTunes library with an Ubuntu Phone, including music files and playlists.


By selecting which iTunes playlists you want to synchronize, the script automatically synchronizes all the tracks from these playlists to your phone and creates the playlists in the Music application.

![Synchronizing](http://thomasmuguet/img/pages/projects-2015-04-06-itunes-synchronization-for-the-ubuntu-phone/syncing.png)

![Playlists in the Music app](http://thomasmuguet/img/pages/projects-2015-04-06-itunes-synchronization-for-the-ubuntu-phone/screenshot.png)

This script has been tested with the latest iTunes on Mac OS X 10.9.5 with a BQ Aquaris 4.5 Ubuntu Edition running Ubuntu 14.10 (r20) and Music app 2.0.846.


## Requirements

* Network enabled on your computer and on your phone (no need for your phone to be plugged in your computer)
* SSH access to the phone

## Warnings

* This is a one-way sync: playlists created on the phone with the same name as synchronized ones are erased.
* Don't run the Music app during the synchronization, especially when creating the playlists, this can mess up the database
* If lots of files are added (especially true for the first import), `mediascanner-se` can be very slow. Until `mediascanner-se` is finished, playlists may appear broken. Try resyncing later.

## Usage

First, edit the `itunes-sync.py` with a text editor to set the parameters:
* `itunes_music_library`: location of your iTunes music library file (default value should be OK)
* `playlists_to_synchronize`: names of the playlists you want to synchronize
* `music_destination`: destination on your phone for the tracks; a `itunes-sync` subfolder will be created
* `ssh_destination`: SSH user and hostname of your phone

Once done, you're ready to go:

* Run in a terminal `./itunes-sync.py`

