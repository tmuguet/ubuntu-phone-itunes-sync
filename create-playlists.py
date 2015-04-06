#!/usr/bin/python3

# Script to be ran on the phone to create the playlists in the Music app
# This script is ran automatically at the end of the synchronization.

import sqlite3
import configparser
import os
import pickle

database = None
version = None

# Find database to update
for dirname, dirnames, filenames in os.walk('.local/share/com.ubuntu.music/Databases'):
    for filename in filenames:
        (f, ext) = os.path.splitext(filename)
        if ext == '.ini':
            config = configparser.ConfigParser()
            config.read(os.path.join(dirname, filename))

            name = config['General']['Name']
            if name == 'music-app-playlist':
                database = os.path.join(dirname, filename.replace('.ini', '.sqlite'))
                version = config['General']['Version']

if not database:
    print('Could not find database')
    exit(1)

print('Using database ' + database + ' (version ' + version + ')')
if version != '1.3':
    print('This version is not supported')
    exit(1)

# Fetch data from the sync scripts
pkl_file = open('itunes-sync.pkl', 'rb')
playlists = pickle.load(pkl_file,encoding='utf-8')
tracks = pickle.load(pkl_file,encoding='utf-8')
pkl_file.close()


conn = sqlite3.connect(database)
c = conn.cursor()


for playlist in playlists:
    # Create playlist
    c.execute("INSERT OR IGNORE INTO playlist VALUES(?)", [(playlist['name']),])

    # Delete all tracks from playlist
    c.execute("DELETE FROM track WHERE playlist=?", [(playlist['name']),])

    # Add tracks
    i=0
    for track in playlist['tracks']:
        t = tracks[track]
        c.execute("INSERT OR IGNORE INTO track VALUES(?,?,?,?,?,?)", (i, playlist['name'], t['location_on_phone'], t['name'], t['artist'], t['album']),)
        i=i+1

    print('Created ' + playlist['name'] + ' with ' + str(i) + ' tracks')

conn.commit()
conn.close()
