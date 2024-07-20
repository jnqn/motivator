import os, json, time
from stravalib.client import Client

client = Client()

MY_STRAVA_CLIENT_ID = os.environ.get('MY_STRAVA_CLIENT_ID')
MY_STRAVA_CLIENT_SECRET = os.environ.get('MY_STRAVA_CLIENT_SECRET')
MY_STRAVA_CODE = os.environ.get('MY_STRAVA_CODE')

def get_auth():
    if MY_STRAVA_CODE:
        access_token = client.exchange_code_for_token(
            client_id=MY_STRAVA_CLIENT_ID,
            client_secret=MY_STRAVA_CLIENT_SECRET,
            code=MY_STRAVA_CODE
            )
        with open('access_token', 'w') as f:
            f.write(json.dumps(access_token))
    else:
        url = client.authorization_url(
            client_id=MY_STRAVA_CLIENT_ID,
            redirect_uri='http://localhost:5000/authorization',
            scope=['read_all', 'activity:read_all', 'profile:read_all']
            )
        print(url)

def check_auth():
    token = open('access_token', 'r').read()
    token = json.loads(token)
    if time.time() > token['expires_at']:
        refresh = client.refresh_access_token(
                    client_id=MY_STRAVA_CLIENT_ID,
                    client_secret=MY_STRAVA_CLIENT_SECRET,
                    refresh_token=token['refresh_token']
                )
    else:
        refresh = False
        client.access_token = token['access_token']
        client.refresh_token = token['refresh_token']
        client.token_expires_at = token['expires_at']
        print('Access token is still valid')
    if refresh:
        client.access_token = refresh['access_token']
        client.refresh_token = refresh['refresh_token']
        client.token_expires_at = refresh['expires_at']
        with open('access_token', 'w') as f:
            f.write(json.dumps(refresh))


if __name__ == '__main__':
    try:
        with open('access_token', 'r') as f:
            access_token = json.loads(f.read())
            client.access_token = access_token
            check_auth()
    except FileNotFoundError:
        get_auth()

    athlete = client.get_athlete()
    print(f'Hello, {athlete.firstname} {athlete.lastname}!')