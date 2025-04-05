import os
import json
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import webbrowser
import logging

import boto3
from botocore.exceptions import ClientError
from stravalib.client import Client

# Set up logging
logger = logging.getLogger(__name__)

class StravaAuth:
    def __init__(self, token_path='access_token', use_s3=False):
        self.client = Client()
        self.client_id = os.environ.get('MY_STRAVA_CLIENT_ID')
        self.client_secret = os.environ.get('MY_STRAVA_CLIENT_SECRET')
        self.code = os.environ.get('MY_STRAVA_CODE')
        self.token_path = token_path
        self.use_s3 = use_s3
        self.s3_bucket = os.environ.get('S3_BUCKET')
        self.s3_key = os.environ.get('S3_TOKEN_KEY', 'motivator/access_token')

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
                # Note: this is just a placeholder, as this method is actually handled
                # by the server instance
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authorization complete. You can close this tab now.')
            except Exception as e:
                self.send_error(500, f'Failed to exchange token: {str(e)}')

    def _get_new_auth(self) -> None:
        """Initialize new authentication flow"""
        if self.code:
            self._handle_auth_code(self.code)
        else:
            auth_url = self.client.authorization_url(
                client_id=self.client_id,
                redirect_uri='http://localhost:5000/authorization',
                scope=['read_all', 'activity:read_all', 'profile:read_all']
            )
            webbrowser.open(auth_url)
            self._handle_auth_response()

    def _handle_auth_response(self) -> None:
        """Start local server to handle auth callback"""
        server = HTTPServer(('localhost', 5000), self.AuthHandler)
        
        # Monkey patch the handler to have access to self
        def patched_do_GET(handler):
            if not handler.path.startswith('/authorization'):
                handler.send_error(404)
                return

            query = parse_qs(urlparse(handler.path).query)
            code = query.get('code', [None])[0]

            if not code:
                handler.send_error(400, 'Missing authorization code')
                return

            try:
                self._handle_auth_code(code)
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(b'Authorization complete. You can close this tab now.')
            except Exception as e:
                handler.send_error(500, f'Failed to exchange token: {str(e)}')
        
        server.RequestHandlerClass.do_GET = patched_do_GET
        server.handle_request()

    def _handle_auth_code(self, code: str) -> None:
        """Exchange authorization code for access token"""
        os.environ['MY_STRAVA_CODE'] = code
        access_token = self.client.exchange_code_for_token(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code
        )

        self._save_token(access_token)

    def authenticate(self) -> None:
        """Handle Strava authentication flow"""
        try:
            access_token = self._load_token()
            if access_token:
                self.client.access_token = access_token
                self._check_token()
            else:
                self._get_new_auth()
        except (FileNotFoundError, ClientError):
            logger.info("No token found, starting new authentication flow")
            self._get_new_auth()

    def _check_token(self) -> None:
        """Verify and refresh token if needed"""
        token = self._load_token()
        
        if not token:
            logger.error("Token not found during refresh check")
            self._get_new_auth()
            return

        if time.time() > token['expires_at']:
            logger.info("Token expired, refreshing")
            refresh = self.client.refresh_access_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=token['refresh_token']
            )
            self._update_client_tokens(refresh)
        else:
            self._update_client_tokens(token)
            logger.info('Access token is still valid')

    def _update_client_tokens(self, token_data: dict) -> None:
        """Update client tokens and save to file"""
        self.client.access_token = token_data['access_token']
        self.client.refresh_token = token_data['refresh_token']
        self.client.token_expires_at = token_data['expires_at']

        self._save_token(token_data)

    def _save_token(self, token_data: dict) -> None:
        """Save token data to file or S3"""
        if self.use_s3:
            self._save_token_to_s3(token_data)
        else:
            self._save_token_to_file(token_data)

    def _load_token(self) -> dict:
        """Load token data from file or S3"""
        if self.use_s3:
            return self._load_token_from_s3()
        else:
            return self._load_token_from_file()

    def _save_token_to_file(self, token_data: dict) -> None:
        """Save token to local file"""
        with open(self.token_path, 'w') as f:
            json.dump(token_data, f)
        logger.info(f"Token saved to file: {self.token_path}")

    def _load_token_from_file(self) -> dict:
        """Load token from local file"""
        with open(self.token_path, 'r') as f:
            token = json.load(f)
            logger.info(f"Token loaded from file: {self.token_path}")
            return token

    def _save_token_to_s3(self, token_data: dict) -> None:
        """Save token to S3 bucket"""
        if not self.s3_bucket:
            raise ValueError("S3_BUCKET environment variable must be set when use_s3=True")
        
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Body=json.dumps(token_data),
            Bucket=self.s3_bucket,
            Key=self.s3_key
        )
        logger.info(f"Token saved to S3: {self.s3_bucket}/{self.s3_key}")

    def _load_token_from_s3(self) -> dict:
        """Load token from S3 bucket"""
        if not self.s3_bucket:
            raise ValueError("S3_BUCKET environment variable must be set when use_s3=True")
        
        s3_client = boto3.client('s3')
        response = s3_client.get_object(
            Bucket=self.s3_bucket,
            Key=self.s3_key
        )
        token = json.loads(response['Body'].read().decode('utf-8'))
        logger.info(f"Token loaded from S3: {self.s3_bucket}/{self.s3_key}")
        return token