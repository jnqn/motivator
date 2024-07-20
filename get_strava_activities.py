import os, json, time
from stravalib.client import Client

global CLIENT
global MY_STRAVA_CLIENT_ID
global MY_STRAVA_CLIENT_SECRET
global MY_STRAVA_CODE

def get_auth():
    if MY_STRAVA_CODE:
        access_token = CLIENT.exchange_code_for_token(
            client_id=MY_STRAVA_CLIENT_ID,
            client_secret=MY_STRAVA_CLIENT_SECRET,
            code=MY_STRAVA_CODE
            )
        with open('access_token', 'w') as f:
            f.write(json.dumps(access_token))
    else:
        url = CLIENT.authorization_url(
            client_id=MY_STRAVA_CLIENT_ID,
            redirect_uri='http://localhost:5000/authorization',
            scope=['read_all', 'activity:read_all', 'profile:read_all']
            )
        print(url)

def check_auth():
    token = open('access_token', 'r').read()
    token = json.loads(token)
    if time.time() > token['expires_at']:
        refresh = CLIENT.refresh_access_token(
                    client_id=MY_STRAVA_CLIENT_ID,
                    client_secret=MY_STRAVA_CLIENT_SECRET,
                    refresh_token=token['refresh_token']
                )
    else:
        refresh = False
        CLIENT.access_token = token['access_token']
        CLIENT.refresh_token = token['refresh_token']
        CLIENT.token_expires_at = token['expires_at']
        print('Access token is still valid')
    if refresh:
        CLIENT.access_token = refresh['access_token']
        CLIENT.refresh_token = refresh['refresh_token']
        CLIENT.token_expires_at = refresh['expires_at']
        with open('access_token', 'w') as f:
            f.write(json.dumps(refresh))

def get_activity_lengths():
    activities = CLIENT.get_activities()
    for activity in activities:
        yield activity.start_date_local, activity.start_date_local + activity.elapsed_time


if __name__ == '__main__':
    CLIENT = Client()
    MY_STRAVA_CLIENT_ID = os.environ.get('MY_STRAVA_CLIENT_ID')
    MY_STRAVA_CLIENT_SECRET = os.environ.get('MY_STRAVA_CLIENT_SECRET')
    MY_STRAVA_CODE = os.environ.get('MY_STRAVA_CODE')
    try:
        with open('access_token', 'r') as f:
            access_token = json.loads(f.read())
            CLIENT.access_token = access_token
            check_auth()
    except FileNotFoundError:
        get_auth()

    athlete = CLIENT.get_athlete()
    print(f'Hello, {athlete.firstname} {athlete.lastname}!')
    for activity in get_activity_lengths():
        start, end = activity
        print(f'Start: {start}, End: {end}')