import json
import os
import time
from unittest.mock import patch, MagicMock
import pytest

# Import directly (stravalib already mocked in conftest)
from src.strava.auth import StravaAuth


@pytest.fixture
def mock_env_vars():
    # Save original environment variables
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["MY_STRAVA_CLIENT_ID"] = "test_client_id"
    os.environ["MY_STRAVA_CLIENT_SECRET"] = "test_client_secret"
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)


def test_init(mock_env_vars):
    auth = StravaAuth()
    assert auth.client_id == "test_client_id"
    assert auth.client_secret == "test_client_secret"
    assert auth.token_path == "access_token"
    assert auth.use_s3 is False
    
    # Test with S3 enabled
    os.environ["S3_BUCKET"] = "test-bucket"
    auth = StravaAuth(use_s3=True)
    assert auth.use_s3 is True
    assert auth.s3_bucket == "test-bucket"
    assert auth.s3_key == "motivator/access_token"


def test_authenticate_with_file(mock_token_file, mock_strava_client):
    auth = StravaAuth(token_path=str(mock_token_file))
    auth.authenticate()
    
    # Verify client was authenticated
    assert auth.client.access_token is not None


def test_check_token_valid(mock_token_file, mock_strava_client):
    auth = StravaAuth(token_path=str(mock_token_file))
    auth._check_token()
    
    # Verify client tokens were updated but not refreshed
    assert auth.client.refresh_access_token.call_count == 0


def test_check_token_expired(tmp_path, mock_expired_token_data, mock_strava_client):
    # Create expired token file
    token_file = tmp_path / "expired_token"
    with open(token_file, "w") as f:
        json.dump(mock_expired_token_data, f)
    
    # Configure the mock to return a dictionary instead of a MagicMock
    mock_strava_client.refresh_access_token.return_value = {
        "access_token": "refreshed_access_token",
        "refresh_token": "refreshed_refresh_token",
        "expires_at": int(datetime.now().timestamp() + 3600)  # Valid for 1 hour
    }
    
    auth = StravaAuth(token_path=str(token_file))
    auth._check_token()
    
    # Verify token was refreshed
    mock_strava_client.refresh_access_token.assert_called_once()


def test_save_token_to_file(tmp_path, mock_token_data):
    token_file = tmp_path / "new_token"
    auth = StravaAuth(token_path=str(token_file))
    auth._save_token_to_file(mock_token_data)
    
    # Verify token was saved to file
    assert token_file.exists()
    with open(token_file, "r") as f:
        saved_token = json.load(f)
        assert saved_token == mock_token_data


def test_load_token_from_file(mock_token_file, mock_token_data):
    auth = StravaAuth(token_path=str(mock_token_file))
    token = auth._load_token_from_file()
    
    # Verify token was loaded from file
    assert token == mock_token_data


def test_save_token_to_s3(mock_s3_client, mock_token_data, mock_env_vars):
    os.environ["S3_BUCKET"] = "test-bucket"
    auth = StravaAuth(use_s3=True)
    auth._save_token_to_s3(mock_token_data)
    
    # Verify token was saved to S3
    mock_s3_client.put_object.assert_called_once_with(
        Body=json.dumps(mock_token_data),
        Bucket="test-bucket",
        Key="motivator/access_token"
    )


def test_load_token_from_s3(mock_s3_client, mock_env_vars):
    os.environ["S3_BUCKET"] = "test-bucket"
    auth = StravaAuth(use_s3=True)
    token = auth._load_token_from_s3()
    
    # Verify token was loaded from S3
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="motivator/access_token"
    )
    
    # Verify token was parsed correctly
    assert "access_token" in token
    assert "refresh_token" in token
    assert "expires_at" in token


def test_save_token_missing_s3_bucket():
    auth = StravaAuth(use_s3=True)
    
    # Should raise ValueError if S3_BUCKET is not set
    with pytest.raises(ValueError, match="S3_BUCKET environment variable must be set"):
        auth._save_token_to_s3({"access_token": "test"})


def test_handle_auth_code(mock_strava_client, tmp_path):
    token_file = tmp_path / "new_token"
    
    # Configure the mock to return a dictionary instead of a MagicMock
    mock_strava_client.exchange_code_for_token.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_at": int(datetime.now().timestamp() + 3600)  # Valid for 1 hour
    }
    
    auth = StravaAuth(token_path=str(token_file))
    auth._handle_auth_code("test_code")
    
    # Verify code was exchanged for token
    mock_strava_client.exchange_code_for_token.assert_called_once_with(
        client_id="test_client_id",
        client_secret="test_client_secret",
        code="test_code"
    )
    
    # Verify environment variable was set
    assert os.environ["MY_STRAVA_CODE"] == "test_code"
    
    # Verify token file was created
    assert token_file.exists()
