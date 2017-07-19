#!/usr/bin/python

# Main script to call to synchronize xspf playlists on the Ubuntu phone

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
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)


config = ConfigParser.ConfigParser()
config.read('settings.ini')

# Local iTunes library file
library_root = config.get('xspf', 'library_root')
# Check artwork?
check_artwork = config.getboolean('checks', 'check_artwork')
# List of playlists to synchronize
playlists_to_synchronize = list(filter(None, (x.strip() for x in config.get('xspf', 'playlists').splitlines())))
# Destination of music on the phone
# A 'itunes-sync' subfolder will be created with the synced music
music_destination = config.get('phone', 'music_destination')
# SSH user+host to connect to
ssh_destination = config.get('phone', 'ssh_destination')

if check_artwork:
    try:
        from mutagen import File
    except ImportError:
        logger.warning("Could not import mutagen; turning off artwork check")
        check_artwork = False

if not library_root.endswith('/'):
    library_root += '/'

logger.debug("Found library root: " + library_root)
if not os.path.isdir(library_root):
    logger.error("Library root " + library_root + " does not exist")
    sys.exit(1)

playlists = []
tracks_used = {}
artworkAlbums = {}
total_size = 0

logger.info("Analyzing library...")

if check_artwork:
    def pict_test(audio):
        try:
            x = audio.pictures
            if x:
                return True
        except Exception:
            pass
        if 'covr' in audio or 'APIC:' in audio:
            return True
        return False

ns = {
    'xspf': 'http://xspf.org/ns/0/'
}

for p in playlists_to_synchronize:
    tree = ET.parse(os.path.expanduser(p))
    root = tree.getroot()
    trackList = root[0]

    playlist = {
        'name': os.path.splitext(os.path.basename(p))[0],
        'tracks': [],
    }

    for t in trackList:
        track = {
            'name': t.findtext('xspf:title', "", ns),
            'artist': t.findtext('xspf:creator', "", ns),
            'album': t.findtext('xspf:album', "", ns),
            'location_full_path': t.findtext("xspf:location", "", ns).replace('file://', '')
        }

        if track['location_full_path'] not in tracks_used:
            # Sanity check: ignore files that are not in a subdirectory of the library root
            # This is a convenience to avoid finding a unique file path on the phone
            if not track['location_full_path'].startswith(library_root):
                logger.warning("Ignoring file at " + track['location_full_path'] + ": outside library")
                continue

            if not os.path.exists(track['location_full_path']):
                logger.warning("Ignoring file at " + track['location_full_path'] + ": could not be found")
                continue

            track['location_full_path'] = os.path.abspath(urllib.unquote(track['location_full_path']))    # Location of file on this FS
            track['location_relative'] = track['location_full_path'].replace(library_root, '')  # Location of file relative to music folder
            track['location_on_phone'] = music_destination + 'itunes-sync/' + track['location_relative']  # Final location on the phone
            track['size'] = os.path.getsize(track['location_full_path'])
            total_size += track['size']

            if check_artwork:
                artworkIndex = track['artist'] + '-' + track['album']
                # Check artwork only if never checked that album
                if artworkIndex not in artworkAlbums:
                    file = File(track['location_full_path'])
                    artworkAlbums[artworkIndex] = pict_test(file)
                    if not artworkAlbums[artworkIndex]:
                        logger.warning("Track at " + track['location_full_path'] + " does not have artwork")

            tracks_used[track['location_full_path']] = track

        playlist['tracks'].append(track['location_full_path'])

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

    if not os.path.isdir(full_dir):
        os.makedirs(full_dir)
    if os.path.exists(full_filename):
        # Should not happen
        logger.warning("Ignoring file " + full_filename + ": already exists (wtf?)")
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
