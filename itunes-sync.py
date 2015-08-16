#!/usr/bin/python

# Main script to call to synchronize the iTunes library on the Ubuntu phone

import ConfigParser
import xml.etree.ElementTree as ET
import os
import os.path
import shutil
import urllib
from subprocess import call
import pickle
import time

config = ConfigParser.ConfigParser()
config.read('settings.ini')

# Local iTunes library file
itunes_music_library = config.get('itunes', 'music_library')
# List of playlists to synchronize
playlists_to_synchronize = list(filter(None, (x.strip() for x in config.get('itunes', 'playlists').splitlines())))
# Destination of music on the phone
# A 'itunes-sync' subfolder will be created with the synced music
music_destination = config.get('phone', 'music_destination')
# SSH user+host to connect to
ssh_destination = config.get('phone', 'ssh_destination')


print "Loading library"

tree = ET.parse(os.path.expanduser(itunes_music_library))
root = tree.getroot()

tracks = {}
playlists = []
tracks_used = {}
total_size = 0

print "Analyzing library"

# Find root of music folder
for dicts in root.findall(".//dict[key='Music Folder']"):
    it = dicts.iter()
    prev = it.next()

    for current in it:
        if prev.text == 'Music Folder':
            library_root = current.text.replace('file://', '')
        prev = current


# Find all tracks in library
for dicts in root.findall(".//dict[key='Location']"):
    track_id = None
    track_location = None
    track_name = None
    track_artist = None
    track_album = None
    track_size = 0

    it = dicts.iter()
    prev = it.next()

    for current in it:
        if prev.text == 'Track ID':
            track_id = current.text
        elif prev.text == 'Name':
            track_name = current.text
        elif prev.text == 'Artist':
            track_artist = current.text
        elif prev.text == 'Album':
            track_album = current.text
        elif prev.text == 'Location':
            track_location = current.text.replace('file://', '')
        elif prev.text == 'Size':
            track_size = int(current.text)
        prev = current

    if not library_root in track_location:
        print "Ignoring file outside library: " + track_id + " @ " + os.path.basename(track_location)
        continue

    track_location = os.path.abspath(urllib.unquote(track_location))    # Location of file on this FS
    track_location_relative = track_location.replace(library_root, '')  # Location of file relative to music folder
    track_location_on_phone = music_destination + 'itunes-sync/' + track_location_relative  # Final location on the phone

    tracks[track_id] = {
        'location_full_path': track_location,
        'location_relative': unicode(track_location_relative, 'utf-8'),
        'location_on_phone': unicode(track_location_on_phone, 'utf-8'),
        'name': track_name,
        'artist': track_artist,
        'album': track_album,
        'size': track_size
    }

print "Found " + str(len(tracks)) + " tracks"

# Find all playlists
for dicts in root.findall(".//dict[key='Playlist ID']"):
    playlist_name = None
    playlist_tracks = []

    it = dicts.iter()
    prev = it.next()

    for current in it:
        if prev.text == 'Name':
            playlist_name = current.text
            break
        prev = current

    if not playlist_name in playlists_to_synchronize:
        continue

    # Playlist to synchronize: get the tracks it contains
    for t in dicts.findall(".//dict[key='Track ID']/integer"):
        id = t.text
        if not id in tracks:
            print "Could not find track #" + id
            continue

        playlist_tracks.append(t.text)
        if not id in tracks_used:
            tracks_used[id] = tracks[id]
            total_size += tracks[id]['size']

    print "Found playlist " + playlist_name + " (" + str(len(playlist_tracks)) + " tracks)"
    playlists.append({'name': playlist_name, 'tracks': playlist_tracks})



print "Preparing transfer of " + str(len(tracks_used)) + " tracks - " + str(total_size/(1024*1024)) + "MB"

# Export data to send to the phone for creating playlists
output = open('itunes-sync.pkl', 'wb')
pickle.dump(playlists, output)
pickle.dump(tracks_used, output, -1)
output.close()

# Clean and rec-reate a fake music folder to synchronize on the phone
if os.path.isdir("itunes-sync"):
    shutil.rmtree('itunes-sync')

for id,track in tracks_used.iteritems():
    filename = os.path.basename(track['location_relative'])
    dir = os.path.dirname(track['location_relative'])
    full_dir = "itunes-sync/" + dir
    full_filename = full_dir + "/" + filename

    if not os.path.exists(track['location_full_path']):
        print "Could not find file " + track['location_full_path']
        continue

    if not os.path.isdir(full_dir):
        os.makedirs(full_dir)
    if os.path.exists(full_filename):
        # Can happen if a file is imported twice in iTunes
        print "File already exists " + full_filename
        continue

    os.symlink(track['location_full_path'], full_filename)


# Folder is ready to synchronize

print "Transferring..."

call(["rsync", "-ruLvz", "--delete", "--progress", "--stats", "--exclude='.DS_Store'", "itunes-sync", ssh_destination + ":" + music_destination])

# If mediascanner is too slow, this will fail...
print "Creating playlists..."
time.sleep(60)

# Send the data, the script to create playlists and run it
call(["scp", "itunes-sync.pkl", ssh_destination + ":~/"])
call(["scp", "create-playlists.py", ssh_destination + ":~/"])
call(["ssh", ssh_destination, "python3", "create-playlists.py"])
