import os
import logging
from src.strava.auth import StravaAuth
from src.strava.activities import StravaActivities
from src.spotify.handler import SpotifyHandler

# Set up logging
logger = logging.getLogger(__name__)

def process_activities(create_playlist=True, limit=1, use_s3=False):
    """Process Strava activities and create Spotify playlists
    
    Args:
        create_playlist (bool): Whether to create Spotify playlists
        limit (int): Number of recent activities to process
        use_s3 (bool): Whether to use S3 for token storage
        
    Returns:
        list: List of processed activities
    """
    logger.info(f"Processing {limit} activities (create_playlist={create_playlist}, use_s3={use_s3})")
    
    # Initialize auth handlers
    strava_auth = StravaAuth(use_s3=use_s3)
    strava_auth.authenticate()
    
    strava = StravaActivities(strava_auth)
    spotify = SpotifyHandler()

    # Get user info
    athlete = strava.get_athlete_info()
    logger.info(f'Hello, {athlete.firstname} {athlete.lastname}!')

    results = []
    # Process activities
    activity_count = 0
    for activity in strava.get_activities(limit=limit):
        activity_count += 1
        name, start, start_epoch, end, end_epoch = activity
        logger.info(f'Activity: {name}')
        logger.info(f'Start: {start} ({start_epoch}), End: {end} ({end_epoch})')

        activity_tracks = spotify.get_activity_tracks(start_epoch, end_epoch)
        logger.info(f'Found {len(activity_tracks)} tracks played during this activity')

        if create_playlist and activity_tracks:
            spotify.create_activity_playlist(name, start, end, activity_tracks)
            logger.info(f'Created playlist with {len(activity_tracks)} tracks')
            
        results.append({
            'activity_name': name,
            'start_time': start.isoformat(),
            'end_time': end.isoformat(),
            'track_count': len(activity_tracks)
        })
    
    logger.info(f"Processed {activity_count} activities")
    return results


def main():
    """Main function for local execution"""
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run with default settings for local execution
    process_activities(create_playlist=True)


if __name__ == '__main__':
    main()