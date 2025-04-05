import json
import os
from unittest.mock import patch, MagicMock
import pytest

# Mock stravalib to avoid compatibility issues
with patch('sys.modules', {'stravalib': MagicMock(), 'stravalib.client': MagicMock()}):
    from lambda_function import lambda_handler, get_secret


@pytest.fixture
def mock_env_vars():
    # Save original environment variables
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["SECRET_NAME"] = "test-secret"
    os.environ["S3_BUCKET"] = "test-bucket"
    os.environ["CREATE_PLAYLIST"] = "true"
    os.environ["ACTIVITY_LIMIT"] = "2"
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_secrets_manager():
    with patch("boto3.session.Session") as mock_session:
        session = MagicMock()
        client = MagicMock()
        mock_session.return_value = session
        session.client.return_value = client
        
        # Mock get_secret_value response
        response = {
            "SecretString": json.dumps({
                "MY_STRAVA_CLIENT_ID": "test_client_id",
                "MY_STRAVA_CLIENT_SECRET": "test_client_secret"
            })
        }
        client.get_secret_value.return_value = response
        
        yield client


@pytest.fixture
def mock_process_activities():
    with patch("lambda_function.process_activities") as mock_process:
        mock_process.return_value = [
            {
                "activity_name": "Test Run",
                "start_time": "2023-01-01T12:00:00+00:00",
                "end_time": "2023-01-01T13:00:00+00:00",
                "track_count": 5
            }
        ]
        yield mock_process


def test_get_secret(mock_secrets_manager, mock_env_vars):
    # Test get_secret function
    get_secret()
    
    # Verify Secrets Manager client was created with the right parameters
    mock_secrets_manager.get_secret_value.assert_called_once_with(
        SecretId="test-secret"
    )
    
    # Verify environment variables were set
    assert os.environ["MY_STRAVA_CLIENT_ID"] == "test_client_id"
    assert os.environ["MY_STRAVA_CLIENT_SECRET"] == "test_client_secret"


def test_lambda_handler_success(mock_secrets_manager, mock_process_activities, mock_env_vars):
    # Test the lambda handler with successful execution
    event = {}
    context = {}
    result = lambda_handler(event, context)
    
    # Verify get_secret was called
    mock_secrets_manager.get_secret_value.assert_called_once()
    
    # Verify process_activities was called with the right parameters
    mock_process_activities.assert_called_once_with(
        create_playlist=True,
        limit=2,
        use_s3=True
    )
    
    # Verify the result
    assert result["success"] is True
    assert "activities" in result


def test_lambda_handler_missing_s3_bucket(mock_secrets_manager, mock_env_vars):
    # Test lambda handler when S3_BUCKET is not set
    os.environ.pop("S3_BUCKET")
    
    event = {}
    context = {}
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="S3_BUCKET environment variable must be set"):
        lambda_handler(event, context)


def test_lambda_handler_exception(mock_secrets_manager, mock_process_activities, mock_env_vars):
    # Test lambda handler when an exception occurs
    mock_process_activities.side_effect = Exception("Test error")
    
    event = {}
    context = {}
    
    # Should raise the exception
    with pytest.raises(Exception, match="Test error"):
        lambda_handler(event, context)
