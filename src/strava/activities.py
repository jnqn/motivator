from datetime import datetime, timedelta
from typing import Generator, Tuple

from .auth import StravaAuth


class StravaActivities:
    def __init__(self, auth: StravaAuth):
        self.auth = auth
        self.client = auth.client

    def get_activities(self, limit: int = 1) -> Generator[Tuple[str, datetime, float, datetime, float], None, None]:
        """Retrieve recent activities"""
        activities = self.client.get_activities(limit=limit)
        for activity in activities:
            if activity.type.root == 'Run':
                end_time = activity.start_date_local + timedelta(seconds=activity.elapsed_time)
                yield (
                    activity.name,
                    activity.start_date_local,
                    activity.start_date_local.timestamp(),
                    end_time,
                    end_time.timestamp()
                )
    
    def get_athlete_info(self):
        """Get athlete information"""
        return self.client.get_athlete()
