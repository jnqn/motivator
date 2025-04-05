from unittest.mock import patch, MagicMock
import pytest

# Import directly (stravalib already mocked in conftest)
from src.main import process_activities


def test_process_activities(mock_strava_client, mock_spotify_client):
    # Setup mocks
    with patch("src.main.StravaAuth") as mock_auth, \
         patch("src.main.StravaActivities") as mock_activities, \
         patch("src.main.SpotifyHandler") as mock_spotify:
        
        # Configure mock returns
        mock_auth_instance = MagicMock()
        mock_auth.return_value = mock_auth_instance
        
        mock_activities_instance = MagicMock()
        mock_activities.return_value = mock_activities_instance
        
        # Setup athlete info
        athlete = MagicMock()
        athlete.firstname = "Test"
        athlete.lastname = "User"
        mock_activities_instance.get_athlete_info.return_value = athlete
        
        # Setup activity data
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        activity_data = [
            ("Test Run", now, now.timestamp(), now + timedelta(hours=1), (now + timedelta(hours=1)).timestamp())
        ]
        mock_activities_instance.get_activities.return_value = activity_data
        
        # Setup Spotify handler
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.get_activity_tracks.return_value = ["spotify:track:test_track"]
        
        # Call the function
        results = process_activities(create_playlist=True, limit=1)
        
        # Verify StravaAuth was initialized
        mock_auth.assert_called_once_with(use_s3=False)
        mock_auth_instance.authenticate.assert_called_once()
        
        # Verify StravaActivities was initialized with the auth instance
        mock_activities.assert_called_once_with(mock_auth_instance)
        
        # Verify SpotifyHandler was initialized
        mock_spotify.assert_called_once()
        
        # Verify get_athlete_info was called
        mock_activities_instance.get_athlete_info.assert_called_once()
        
        # Verify get_activities was called with limit
        mock_activities_instance.get_activities.assert_called_once_with(limit=1)
        
        # Verify get_activity_tracks was called with correct timestamps
        mock_spotify_instance.get_activity_tracks.assert_called_once_with(
            activity_data[0][2],  # start_epoch
            activity_data[0][4]   # end_epoch
        )
        
        # Verify create_activity_playlist was called
        mock_spotify_instance.create_activity_playlist.assert_called_once_with(
            activity_data[0][0],  # name
            activity_data[0][1],  # start
            activity_data[0][3],  # end
            ["spotify:track:test_track"]
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]["activity_name"] == "Test Run"
        assert results[0]["track_count"] == 1


def test_process_activities_no_playlist(mock_strava_client, mock_spotify_client):
    # Setup mocks
    with patch("src.main.StravaAuth") as mock_auth, \
         patch("src.main.StravaActivities") as mock_activities, \
         patch("src.main.SpotifyHandler") as mock_spotify:
        
        # Configure mock returns
        mock_auth_instance = MagicMock()
        mock_auth.return_value = mock_auth_instance
        
        mock_activities_instance = MagicMock()
        mock_activities.return_value = mock_activities_instance
        
        # Setup athlete info
        athlete = MagicMock()
        athlete.firstname = "Test"
        athlete.lastname = "User"
        mock_activities_instance.get_athlete_info.return_value = athlete
        
        # Setup activity data
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        activity_data = [
            ("Test Run", now, now.timestamp(), now + timedelta(hours=1), (now + timedelta(hours=1)).timestamp())
        ]
        mock_activities_instance.get_activities.return_value = activity_data
        
        # Setup Spotify handler
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.get_activity_tracks.return_value = ["spotify:track:test_track"]
        
        # Call the function with create_playlist=False
        results = process_activities(create_playlist=False, limit=1)
        
        # Verify create_activity_playlist was NOT called
        mock_spotify_instance.create_activity_playlist.assert_not_called()
        
        # Verify results still include track count
        assert len(results) == 1
        assert results[0]["track_count"] == 1
