import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
import csv
import time
import re

SPOTIFY_CLIENT_ID = 'client_id_from_spotify_developer_account'
SPOTIFY_CLIENT_SECRET = 'client_secret_from_spotify_developer_account'

CART_CSV_FILE = 'carts.csv'


def import_csv_to_track_list(csv_file: str) -> list:
    '''Import Rivendell CSV Cart Dump file and generate list
    of (artist, title) tuples.'''
    lines = []

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            lines.append(row)

    lines.pop(0)  # remove headers

    tracks = []

    for line in lines:
        # Artist is column index 5, title is 4
        tracks.append((line[5], line[4]))

    return tracks


class SpotifyAPI():
    def __init__(self):
        self.client_id = SPOTIFY_CLIENT_ID
        self.client_secret = SPOTIFY_CLIENT_SECRET

        self.auth_manager = SpotifyClientCredentials(
            client_id=self.client_id, client_secret=self.client_secret)
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

        self.request_rate_limit_ms = 600
        self.search_limit = 1
        self.search_offset = 0
        self.search_type = 'track'

        self.audio_feature_query_limit = 100
        self.error_log = []

    def sanitize_text(self, text: str) -> str:
        '''Remove any text in () or [], inclusively to help with query correctness.'''
        return re.sub("[\(\[].*?[\)\]]", "", text)

    def est_time_remaining(self, total: int, index: int) -> str:
        '''Estimate time remaining by multiplying the number 
        of remaining loops with the loop iteration time'''
        millis = (total - index) * self.request_rate_limit_ms
        seconds = round(int((millis / 1000) % 60))
        minutes = round(int((millis/(60_000)) % 60))
        hours = round(int((millis/(3_600_000)) % 24))
        if hours == 0:
            return f'{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'
        else:
            return f'{str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'

    def get_tracks(self, artist_title_list: list) -> object:
        tracks = {}
        total_tracks = len(artist_title_list)

        print('[INF] Getting track metadata from Spotify API...')

        for i, artist_title in enumerate(artist_title_list):
            est_remain = self.est_time_remaining(len(artist_title_list), i)

            artist = self.sanitize_text(artist_title[0])
            title = self.sanitize_text(artist_title[1])

            track = self.get_track_meta(artist, title)
            if track == None:
                self.error_log.append(
                    f'[ERR] No data returned for {artist_title}')
                continue
            # Use Spotify Track ID as key for track
            tracks[track['track']['id']] = track

            progress(i+1, total_tracks,
                     f'[INF] {i+1} of {total_tracks}', f'Complete. {est_remain} Remaining.', 1, 30)

            # In future, may try batch, wait for 429, back off, and batch again...
            time.sleep(self.request_rate_limit_ms / 1000)

        return tracks

    def get_track_meta(self, artist: str, title: str) -> object:
        '''Get relevant Spotify information from query using artist and title keywords'''
        query_string = f'{artist} {title}'
        results = self.sp.search(q=query_string, limit=self.search_limit,
                                 offset=self.search_offset, type=self.search_type)

        if len(results['tracks']['items']) == 0:
            return None

        try:
            track = results['tracks']['items'][0]
        except KeyError:
            self.error_log.append(
                f'[ERR] Query results for {artist} - {title} does not contain valid items.')
            return None

        album_struct = track.get('album')
        album = {
            'id': album_struct.get('id'),
            'name': album_struct.get('name'),
            'type': album_struct.get('album_type')
        }

        artists = []
        artists_struct = track.get('artists')

        if artists_struct == None:
            artists_struct = []

        for artist in artists_struct:
            artists.append({
                'id': artist.get('id'),
                'name': artist.get('name')
            })

        external_ids_struct = track.get('external_ids')
        track = {
            'id': track.get('id'),
            'isrc': external_ids_struct.get('isrc'),
            'name': track.get('name'),
            'popularity': track.get('popularity')
        }

        return {
            'album': album,
            'artists': artists,
            'track': track
        }

    def batch_audio_features(self, tracks: object, track_ids: list) -> object:
        '''Get audio features from a list of Spotify track IDs (which we got from calls to get_tracks()'''
        if len(track_ids) > self.audio_feature_query_limit:
            # Spotify only allows 100 IDs per query, so use list comprehension to split into len<=100 lists
            [track_ids[i:i + self.audio_feature_query_limit]
                for i in range(0, len(track_ids), self.audio_feature_query_limit)]
        else:
            # next block expecting list of lists due to above
            track_ids = [track_ids]

        total_batches = len(track_ids)
        print('[INF] Batch processing audio features from Spotify API...')

        for i, track_id_list in enumerate(track_ids):
            audio_features = self.sp.audio_features(track_id_list)
            est_remain = self.est_time_remaining(len(track_ids), i)

            for item in audio_features:
                id = item.get('id')
                tracks[id]['audio_features'] = item

            progress(i+1, total_batches,
                     f'[INF] {i+1} of {total_batches}', f'Complete. {est_remain} Remaining.', 1, 30)

            time.sleep(self.request_rate_limit_ms / 1000)

        return tracks


def progress(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)

    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)

    if iteration >= total:
        print()


if __name__ == '__main__':
    api = SpotifyAPI()
    track_list = import_csv_to_track_list(CART_CSV_FILE)
    track_struct = api.get_tracks(track_list)
    # keys are ID's we use to request audio features
    track_ids = list(track_struct.keys())
    track_struct = api.batch_audio_features(track_struct, track_ids)

    print('[INF] Writing data to file...')
    with open('carts.json', 'w') as f:
        f.write(json.dumps(track_struct, indent=2))

    if len(api.error_log) == 0:
        print('[INF] Completed. Goodbye!')
    else:
        for err in api.error_log:
            print(err)
        print(
            f'[WRN] Completed with {len(api.error_log)} errors. Please see above for detail. Goodbye!')
