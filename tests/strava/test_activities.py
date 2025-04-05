from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

# Mock the stravalib import to avoid compatibility issues
with patch('sys.modules', {'stravalib.client': MagicMock()}):
    from src.strava.activities import StravaActivities


def test_get_activities(mock_strava_client):
    # Create mock auth
    auth = MagicMock()
    auth.client = mock_strava_client
    
    activities = StravaActivities(auth)
    results = list(activities.get_activities(limit=1))
    
    # Verify get_activities was called
    mock_strava_client.get_activities.assert_called_once_with(limit=1)
    
    # Verify results
    assert len(results) == 1
    activity_data = results[0]
    
    # Verify activity data format
    assert len(activity_data) == 5
    name, start, start_epoch, end, end_epoch = activity_data
    assert name == "Test Run"
    assert isinstance(start, datetime)
    assert isinstance(start_epoch, float)
    assert isinstance(end, datetime)
    assert isinstance(end_epoch, float)
    
    # End time should be start time + elapsed time
    assert (end - start).total_seconds() == 3600


def test_get_athlete_info(mock_strava_client):
    # Create mock auth
    auth = MagicMock()
    auth.client = mock_strava_client
    
    activities = StravaActivities(auth)
    athlete = activities.get_athlete_info()
    
    # Verify get_athlete was called
    mock_strava_client.get_athlete.assert_called_once()
    
    # Verify athlete info
    assert athlete.firstname == "Test"
    assert athlete.lastname == "User"
