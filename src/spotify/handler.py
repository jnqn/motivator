import os
from datetime import datetime, timezone

import spotipy
from spotipy.oauth2 import SpotifyOAuth


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
