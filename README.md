# Motivator

A tool that automatically creates Spotify playlists from music listened to during Strava activities.

## Project Structure

```
motivator/
├── src/                      # Source code package
│   ├── strava/               # Strava-related functionality
│   │   ├── __init__.py       # Package initialization
│   │   ├── auth.py           # Strava authentication
│   │   └── activities.py     # Activity retrieval
│   ├── spotify/              # Spotify-related functionality
│   │   ├── __init__.py       # Package initialization
│   │   └── handler.py        # Playlist management
│   ├── __init__.py           # Main package initialization
│   └── main.py               # Core application logic
├── tests/                    # Unit tests
├── lambda_function.py        # AWS Lambda handler
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Local Setup

### Requirements

- Python 3.8 or newer (tested with Python 3.13)

### Installation

1. Install dependencies:
   ```
   python3 -m pip install -r requirements.txt
   ```

2. Set environment variables:
   ```
   export MY_STRAVA_CLIENT_ID=your_strava_client_id
   export MY_STRAVA_CLIENT_SECRET=your_strava_client_secret
   ```

3. Run locally:
   ```
   python3 -m src.main
   ```

## Development

### Installation

For development, install the development dependencies:

```
python3 -m pip install -r requirements-dev.txt
```

### Running Tests

Run the tests using pytest:

```
python3 -m pytest
```

Run tests with coverage:

```
python3 -m pytest --cov=src tests/
```

For convenience, you can use the provided shell script that runs tests with Python 3.13:

```
./run_tests.sh
```

## AWS Lambda Deployment

### Prerequisites

1. AWS account with necessary permissions
2. AWS CLI installed and configured
3. Create a Secret in AWS Secrets Manager with the following keys:
   - `MY_STRAVA_CLIENT_ID`: Your Strava Client ID
   - `MY_STRAVA_CLIENT_SECRET`: Your Strava Client Secret
   - (Optionally) `MY_STRAVA_CODE`: If you have a pre-authorized code

### Deployment Steps

1. Create a deployment package:
   ```
   python3 -m pip install -r requirements.txt -t ./package
   cp -r src lambda_function.py ./package/
   cd package
   zip -r ../deployment.zip .
   cd ..
   ```

2. Create Lambda function in AWS Console or via CLI:
   ```
   aws lambda create-function \
     --function-name Motivator \
     --runtime python3.9 \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://deployment.zip \
     --role arn:aws:iam::account-id:role/lambda-role-with-secrets-access \
     --environment Variables={SECRET_NAME=motivator-secrets}
   ```

3. Configure environment variables:
   - `SECRET_NAME`: Name of the secret in AWS Secrets Manager
   - `CREATE_PLAYLIST`: Whether to create playlists (true/false, default: true)
   - `ACTIVITY_LIMIT`: Number of recent activities to process (default: 1)

4. Set up a CloudWatch Events rule to schedule the Lambda function:
   ```
   aws events put-rule \
     --name MotivatorDailyRun \
     --schedule-expression "cron(0 6 * * ? *)" \
     --state ENABLED
   ```

5. Add permission for CloudWatch Events to invoke the Lambda function:
   ```
   aws lambda add-permission \
     --function-name Motivator \
     --statement-id MotivatorDailyRun \
     --action lambda:InvokeFunction \
     --principal events.amazonaws.com \
     --source-arn arn:aws:events:region:account-id:rule/MotivatorDailyRun
   ```

6. Create a target for the CloudWatch Events rule:
   ```
   aws events put-targets \
     --rule MotivatorDailyRun \
     --targets "Id"="1","Arn"="arn:aws:lambda:region:account-id:function:Motivator"
   ```

### Authentication Handling

Since AWS Lambda can't open a browser for authentication, you should:

1. Run the authentication flow once locally to generate the token file.
2. Upload the token file to AWS S3:
   ```
   aws s3 cp access_token s3://your-bucket/motivator/access_token
   ```
3. Configure the Lambda function to download the token file from S3.

### Token Storage Options

For managing the token in AWS Lambda:

1. **S3 Storage** (Recommended for this use case): 
   - Modify the `StravaAuth` class to read/write tokens from S3
   - Add S3 bucket name and key as environment variables

2. **Secrets Manager**:
   - You could store the tokens in AWS Secrets Manager
   - However, this is more expensive for frequently updated data

## Continuous Integration

This project uses GitHub Actions for continuous integration. On each push and pull request, the following checks are run:

- Unit tests on Python 3.8, 3.9, 3.10, and 3.13
- Code coverage reporting

## Notes for Production Use

1. Add proper error handling and monitoring
2. Set up CloudWatch Logs for tracking execution
3. Set up CloudWatch Alarms to notify on failures
4. Consider handling token expiration and rotation
5. Enable S3 versioning on the token file for recovery if needed