import os
import json
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Generator, Tuple
from urllib.parse import urlparse, parse_qs
import webbrowser

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from stravalib.client import Client

class StravaAuth:
    def __init__(self):
        self.client = Client()
        self.client_id = os.environ.get('MY_STRAVA_CLIENT_ID')
        self.client_secret = os.environ.get('MY_STRAVA_CLIENT_SECRET')
        self.code = os.environ.get('MY_STRAVA_CODE')

    class AuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if not self.path.startswith('/authorization'):
                self.send_error(404)
                return

            query = parse_qs(urlparse(self.path).query)
            code = query.get('code', [None])[0]

            if not code:
                self.send_error(400, 'Missing authorization code')
                return

            try:
                self._handle_auth_code(code)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authorization complete. You can close this tab now.')
            except Exception as e:
                self.send_error(500, f'Failed to exchange token: {str(e)}')

    def authenticate(self) -> None:
        """Handle Strava authentication flow"""
        try:
            with open('access_token', 'r') as f:
                access_token = json.load(f)
                self.client.access_token = access_token
                self._check_token()
        except FileNotFoundError:
            self._get_new_auth()

    def _check_token(self) -> None:
        """Verify and refresh token if needed"""
        with open('access_token', 'r') as f:
            token = json.load(f)

        if time.time() > token['expires_at']:
            refresh = self.client.refresh_access_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=token['refresh_token']
            )
            self._update_client_tokens(refresh)
        else:
            self._update_client_tokens(token)
            print('Access token is still valid')

    def _update_client_tokens(self, token_data: dict) -> None:
        """Update client tokens and save to file"""
        self.client.access_token = token_data['access_token']
        self.client.refresh_token = token_data['refresh_token']
        self.client.token_expires_at = token_data['expires_at']

        with open('access_token', 'w') as f:
            json.dump(token_data, f)

    def get_activities(self) -> Generator[Tuple[str, datetime, float, datetime, float], None, None]:
        """Retrieve recent activities"""
        activities = self.client.get_activities(limit=1)
        for activity in activities:
            if activity.type.root == 'Run':
                end_time = activity.start_date_local + timedelta(seconds=activity.elapsed_time)
                yield (
                    activity.name,
                    activity.start_date_local,
                    activity.start_date_local.timestamp(),
                    end_time,
                    end_time.timestamp()
                )

class SpotifyHandler:
    def __init__(self):
        scope = 'user-read-recently-played,playlist-modify-private,playlist-read-private,playlist-modify-public'
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    def create_activity_playlist(self, activity_name: str, start_time: datetime,
                               end_time: datetime, tracks: list) -> None:
        """Create a playlist for an activity with the given tracks"""
        user = self.sp.current_user()
        playlist_name = f"Runlist - {start_time.day}/{start_time.month}"
        playlist = self.sp.user_playlist_create(
            user=user['id'],
            name=playlist_name,
            description=activity_name
        )
        self.sp.playlist_add_items(playlist_id=playlist['id'], items=tracks)

    def get_activity_tracks(self, start_epoch: float, end_epoch: float) -> list:
        """Get tracks played during activity timeframe"""
        track_results = self.sp.current_user_recently_played()
        tracks = track_results['items']

        while track_results['next']:
            track_results = self.sp.next(track_results)
            tracks.extend(track_results['items'])

        activity_tracks = []

        time_start = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
        time_end = datetime.fromtimestamp(end_epoch, tz=timezone.utc)

        for track in tracks:
            track_time = datetime.strptime(
                track['played_at'],
                '%Y-%m-%dT%H:%M:%S.%fZ'
            ).replace(tzinfo=timezone.utc)

            if time_start < track_time < time_end:
                activity_tracks.append(track['track']['uri'])

        return activity_tracks

def main():
    create_playlist = True

    # Initialize auth handlers
    strava = StravaAuth()
    strava.authenticate()
    spotify = SpotifyHandler()

    # Print user info
    athlete = strava.client.get_athlete()
    print(f'Hello, {athlete.firstname} {athlete.lastname}!')

    # Process activities
    for activity in strava.get_activities():
        name, start, start_epoch, end, end_epoch = activity
        print(f'Start: {start} ({start_epoch}), End: {end} ({end_epoch})')

        activity_tracks = spotify.get_activity_tracks(start_epoch, end_epoch)

        if create_playlist and activity_tracks:
            spotify.create_activity_playlist(name, start, end, activity_tracks)

if __name__ == '__main__':
    main()
