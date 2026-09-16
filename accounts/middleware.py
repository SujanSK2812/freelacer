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
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={path}")

            if not request.user.is_superuser:
                role = getattr(request.user, 'role', None)
                if role != 'client':
                    messages.error(request, "Access denied. This page is reserved for Clients.")
                    if role == 'freelancer':
                        return redirect('freelancer:freelancer_dashboard')
                    return redirect('home')

        # 2. FREELANCER ROUTE PROTECTION (/freelancer/...)
        # Note: /freelancer/profile/<id>/ is public to authenticated clients to review candidate profiles.
        elif path.startswith('/freelancer/'):
            # Check if this is a candidate profile view by an authenticated client
            is_public_profile_view = bool(re.match(r'^/freelancer/profile/\d+/?$', path))

            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={path}")

            if not request.user.is_superuser:
                role = getattr(request.user, 'role', None)
                # If it's a profile view, any authenticated user can view it
                if not (is_public_profile_view and role == 'client'):
                    if role != 'freelancer':
                        messages.error(request, "Access denied. This page is reserved for Freelancers.")
                        if role == 'client':
                            return redirect('client:client_dashboard')
                        return redirect('home')

        # 3. ADMIN-ONLY ACCOUNT ROUTES (/accounts/admin-home/, /accounts/admin/users/)
        elif path.startswith('/accounts/admin-home/') or path.startswith('/accounts/admin/users/'):
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={path}")
            if not request.user.is_superuser:
                messages.error(request, "Access denied. Administrator privileges required.")
                role = getattr(request.user, 'role', None)
                if role == 'freelancer':
                    return redirect('freelancer:freelancer_dashboard')
                elif role == 'client':
                    return redirect('client:client_dashboard')
                return redirect('home')

        return self.get_response(request)
