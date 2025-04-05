import os
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

# Remove direct imports from stravalib model to avoid compatibility issues
# We're using MagicMock instead
from src.strava.auth import StravaAuth
from src.strava.activities import StravaActivities
from src.spotify.handler import SpotifyHandler


# Mock token data
@pytest.fixture
def mock_token_data():
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_at": int(datetime.now().timestamp() + 3600)  # Valid for 1 hour
    }


# Mock expired token data
@pytest.fixture
def mock_expired_token_data():
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_at": int(datetime.now().timestamp() - 3600)  # Expired 1 hour ago
    }


# Mock token file
@pytest.fixture
def mock_token_file(tmp_path, mock_token_data):
    token_file = tmp_path / "access_token"
    with open(token_file, "w") as f:
        json.dump(mock_token_data, f)
    return token_file


# Mock S3 client
@pytest.fixture
def mock_s3_client():
    with patch("boto3.client") as mock_client:
        s3_client = MagicMock()
        mock_client.return_value = s3_client
        
        # Mock get_object response
        get_object_response = {
            "Body": MagicMock()
        }
        get_object_response["Body"].read.return_value = json.dumps({  
            "access_token": "mock_s3_access_token",
            "refresh_token": "mock_s3_refresh_token",
            "expires_at": int(datetime.now().timestamp() + 3600)
        }).encode("utf-8")
        
        s3_client.get_object.return_value = get_object_response
        yield s3_client


# Mock Strava client
@pytest.fixture
def mock_strava_client():
    # Use direct MagicMock instead of patching stravalib to avoid import issues
    strava_client = MagicMock()
    
    # Mock exchange_code_for_token
    strava_client.exchange_code_for_token.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_at": int(datetime.now().timestamp() + 3600)  # Valid for 1 hour
    }
    
    # Mock refresh_access_token
    strava_client.refresh_access_token.return_value = {
        "access_token": "refreshed_access_token",
        "refresh_token": "refreshed_refresh_token",
        "expires_at": int(datetime.now().timestamp() + 3600)  # Valid for 1 hour
    }
    
    # Mock get_athlete
    athlete = MagicMock()
    athlete.firstname = "Test"
    athlete.lastname = "User"
    strava_client.get_athlete.return_value = athlete
    
    # Mock activity
    activity = MagicMock()
    activity.name = "Test Run"
    activity.type.root = "Run"
    activity.start_date_local = datetime.now(timezone.utc)
    activity.elapsed_time = 3600  # 1 hour
    strava_client.get_activities.return_value = [activity]
    
    return strava_client


# Mock Spotify client
@pytest.fixture
def mock_spotify_client():
    with patch("spotipy.Spotify") as mock_spotify:
        spotify_client = MagicMock()
        mock_spotify.return_value = spotify_client
        
        # Mock current_user
        spotify_client.current_user.return_value = {
            "id": "test_user"
        }
        
        # Mock user_playlist_create
        spotify_client.user_playlist_create.return_value = {
            "id": "test_playlist_id"
        }
        
        # Mock current_user_recently_played
        played_at_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        spotify_client.current_user_recently_played.return_value = {
            "items": [
                {
                    "played_at": played_at_time,
                    "track": {
                        "uri": "spotify:track:test_track_1"
                    }
                }
            ],
            "next": None
        }
        
        yield spotify_client


# Mock SpotifyOAuth
@pytest.fixture
def mock_spotify_oauth():
    with patch("spotipy.oauth2.SpotifyOAuth") as mock_oauth:
        oauth = MagicMock()
        mock_oauth.return_value = oauth
        yield oauth
