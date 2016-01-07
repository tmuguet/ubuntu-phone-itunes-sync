#!/usr/bin/python

# Main script to call to synchronize the iTunes library on the Ubuntu phone

import ConfigParser
import xml.etree.ElementTree as ET
import os
import os.path
import shutil
import urllib
import subprocess
import pickle
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

steam_handler = logging.StreamHandler()
steam_handler.setLevel(logging.DEBUG)
logger.addHandler(steam_handler)


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


logger.info("Loading library...")

tree = ET.parse(os.path.expanduser(itunes_music_library))
root = tree.getroot()

tracks = {}
playlists = []
tracks_used = {}
tracks_ignored = {}
total_size = 0

logger.info("Analyzing library...")

# Find root of music folder
for dicts in root.findall(".//dict[key='Music Folder']"):
    it = dicts.iter()
    prev = it.next()

    for current in it:
        if prev.text == 'Music Folder':
            library_root = current.text.replace('file://', '')
        prev = current
logger.debug("Found library root: " + library_root)
if not os.path.isdir(library_root):
    logger.error("Library root does not exist")
    sys.exit(1)

# Find all tracks in library
for dicts in root.findall(".//dict[key='Location']"):
    track = {
        'name': "",
        'artist': "",
        'album': "",
        'size': 0,
    }

    # Load data from XML
    it = dicts.iter()
    prev = it.next()
    for current in it:
        if prev.text == 'Track ID':
            track['id'] = current.text
        elif prev.text == 'Name':
            track['name'] = current.text
        elif prev.text == 'Artist':
            track['artist'] = current.text
        elif prev.text == 'Album':
            track['album'] = current.text
        elif prev.text == 'Location':
            track['location_full_path'] = current.text.replace('file://', '')
        elif prev.text == 'Size':
            track['size'] = int(current.text)
        prev = current

    # Sanity checks: all essential fields found?
    if 'id' not in track and 'location_full_path' not in track:
        logger.warning("Ignoring file: missing id and path (library corrupted?)")
        logger.debug(track)
        continue

    if 'id' not in track:
        logger.warning("Ignoring file at " + track['location_full_path'] + ": missing id (library corrupted?)")
        logger.debug(track)
        continue

    if 'location_full_path' not in track:
        logger.warning("Ignoring file #" + track['id'] + ": missing path (library corrupted?)")
        logger.debug(track)
        continue

    # Sanity check: ignore applications
    if track['location_full_path'].endswith('.ipa'):
        tracks_ignored[track['id']] = track
        continue

    # Sanity check: ignore files that are not in a subdirectory of the library root
    # This is a convenience to avoid finding a unique file path on the phone
    if not track['location_full_path'].startswith(library_root):
        logger.warning("Ignoring file #" + track['id'] + " at " + track['location_full_path'] + ": outside library")
        logger.debug(track)
        tracks_ignored[track['id']] = track
        continue

    # Compute some paths
    track['location_full_path'] = os.path.abspath(urllib.unquote(track['location_full_path']))    # Location of file on this FS
    track['location_relative'] = unicode(track['location_full_path'].replace(library_root, ''), 'utf-8')  # Location of file relative to music folder
    track['location_on_phone'] = unicode(music_destination + 'itunes-sync/', 'utf-8') + track['location_relative']  # Final location on the phone

    # Valid track: store its data
    # File may not exist, that will be checked later if the track is included in a synchronized playlist
    tracks[track['id']] = track

logger.info("Found " + str(len(tracks)) + " tracks")

# Find all playlists
for dicts in root.findall(".//dict[key='Playlist ID']"):
    playlist = {
        'tracks': [],
    }

    # Load data from XML
    it = dicts.iter()
    prev = it.next()
    for current in it:
        if prev.text == 'Name':
            playlist['name'] = current.text
            break
        prev = current

    # Sanity checks: all essential fields found?
    if 'name' not in playlist:
        logger.debug("Ignoring playlist: missing name (library corrupted?)")
        continue

    # If we don't want to synchronize this playlist, don't bother parse its tracks
    if playlist['name'] not in playlists_to_synchronize:
        logger.debug("Found playlist " + playlist['name'] + " (ignored)")
        continue

    # Playlist to synchronize: get the tracks it contains
    for t in dicts.findall(".//dict[key='Track ID']/integer"):
        id = t.text
        if id not in tracks:
            if id in tracks_ignored:
                logger.warning("Ignoring track #" + id + ": previously ignored (see previous warning)")
                logger.debug(tracks_ignored[id])
            else:
                logger.warning("Ignoring track #" + id + ": not found in library (library corrupted?)")
            continue

        playlist['tracks'].append(t.text)
        if id not in tracks_used:
            tracks_used[id] = tracks[id]
            total_size += tracks[id]['size']


    logger.info("Found playlist " + playlist['name'] + " (" + str(len(playlist['tracks'])) + " tracks)")
    playlists.append(playlist)


logger.info("Preparing transfer of " + str(len(tracks_used)) + " tracks - " + str(total_size/(1024*1024)) + "MB...")

# Export data to send to the phone for creating playlists
output = open('itunes-sync.pkl', 'wb')
pickle.dump(playlists, output)
pickle.dump(tracks_used, output, -1)
output.close()

# Clean and re-create a fake music folder with symlinks to synchronize on the phone
if os.path.isdir("itunes-sync"):
    shutil.rmtree('itunes-sync')

for id,track in tracks_used.iteritems():
    filename = os.path.basename(track['location_relative'])
    dir = os.path.dirname(track['location_relative'])
    full_dir = "itunes-sync/" + dir
    full_filename = full_dir + "/" + filename

    if not os.path.exists(track['location_full_path']):
        logger.warning("Ignoring track #" + track['id'] + ": file " + track['location_full_path'] + " could not be found")
        logger.debug(track)
        continue

    if not os.path.isdir(full_dir):
        os.makedirs(full_dir)
    if os.path.exists(full_filename):
        # Can happen if a file is imported twice in iTunes, or if library is corrupted
        logger.warning("Ignoring track #" + track['id'] + ": file " + full_filename + " already exists (imported twice, or library corrupted?)")
        logger.debug(track)
        continue

    os.symlink(track['location_full_path'], full_filename)


# Folder is ready to synchronize

def call(args, log):
    s = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        line = s.stdout.readline()
        if not line:
            break
        log.info("[" + args[0] + "] " + line.strip())


logger.info("Transferring to " + ssh_destination + ":" + music_destination + "...")
call(["rsync", "-ruLvz", "--delete", "--progress", "--stats", "--exclude='.DS_Store'", "itunes-sync", ssh_destination + ":" + music_destination], logger)

# If mediascanner is too slow, this will fail...
logger.info("Creating playlists...")
time.sleep(10)

# Send the data, the script to create playlists and run it
call(["scp", "itunes-sync.pkl", ssh_destination + ":~/"], logger)
call(["scp", "create-playlists.py", ssh_destination + ":~/"], logger)
call(["ssh", ssh_destination, "python3", "create-playlists.py"], logger)

# Clean intermediate files
logger.info("Cleaning...")
shutil.rmtree('itunes-sync')
os.remove('itunes-sync.pkl')
