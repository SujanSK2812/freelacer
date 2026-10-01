import time
import logging
from django.utils.deprecation import MiddlewareMixin
from projects.services import auto_complete_expired_projects

logger = logging.getLogger(__name__)

_last_checked = 0


class ProjectExpirationMiddleware(MiddlewareMixin):
    """
    Middleware that performs server-side checks to update any projects
    whose estimated completion date has passed.
    Throttled to run at most once every 20 seconds across HTTP requests,
    ensuring negligible overhead while guaranteeing up-to-date project statuses.
    """

    def process_request(self, request):
        global _last_checked
        now_ts = time.time()
        # Throttled check
        if now_ts - _last_checked > 20:
            _last_checked = now_ts
            try:
                auto_complete_expired_projects()
            except Exception as e:
                logger.error(f"Error in ProjectExpirationMiddleware: {e}")
        return None
