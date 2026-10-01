import re
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings


class RoleAccessMiddleware:
    """
    Middleware that enforces backend route protection based on the user's role.
    Prevents users from bypassing role restrictions simply by typing URLs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Ignore static, media, admin django urls
        if path.startswith('/static/') or path.startswith('/media/') or path.startswith('/admin/'):
            return self.get_response(request)

        # 1. CLIENT ROUTE PROTECTION (/client/...)
        if path.startswith('/client/'):
            # Allow job details page for any authenticated user (e.g. freelancers viewing and applying to jobs)
            is_job_detail_view = bool(re.match(r'^/client/job/\d+/?$', path))

            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={path}")

            if not request.user.is_superuser:
                role = getattr(request.user, 'role', None)
                if not (is_job_detail_view and role == 'freelancer'):
                    if role != 'client':
                        if role == 'freelancer':
                            if path.startswith('/client/home/'):
                                return redirect('freelancer:freelancer_home')
                            elif path.startswith('/client/proposals/'):
                                return redirect('freelancer:my_proposals')
                            return redirect('freelancer:freelancer_dashboard')
                        return redirect('home')

        # 2. FREELANCER ROUTE PROTECTION (/freelancer/...)
        # Note: /freelancer/profile/<id>/ is public to authenticated clients to review candidate profiles.
        # Note: /freelancer/search/ is the shared search endpoint used across the portal.
        elif path.startswith('/freelancer/'):
            # Check if this is a candidate profile view or search by an authenticated client
            is_public_profile_view = bool(re.match(r'^/freelancer/profile/\d+/?$', path))
            is_search_view = path.startswith('/freelancer/search/')

            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={path}")

            if not request.user.is_superuser:
                role = getattr(request.user, 'role', None)
                # If it's a profile view or search, any authenticated user can view it
                if not ((is_public_profile_view or is_search_view) and role == 'client'):
                    if role != 'freelancer':
                        if role == 'client':
                            if path.startswith('/freelancer/home/'):
                                return redirect('client:client_home')
                            elif path.startswith('/freelancer/my-proposals/'):
                                return redirect('client:client_proposals')
                            return redirect('client:client_dashboard')
                        return redirect('home')

        # 3. ADMIN-ONLY ACCOUNT ROUTES (/accounts/admin-home/, /accounts/admin/users/, etc.)
        elif path.startswith('/accounts/admin-home/') or path.startswith('/accounts/admin/users/') or path.startswith('/accounts/admin/connection-requests/'):
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={path}")
            if not request.user.is_superuser and getattr(request.user, 'role', '') != 'admin':
                role = getattr(request.user, 'role', None)
                if role == 'freelancer':
                    return redirect('freelancer:freelancer_dashboard')
                elif role == 'client':
                    return redirect('client:client_dashboard')
                return redirect('home')

        return self.get_response(request)
