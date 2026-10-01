from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings


def role_required(allowed_roles, redirect_url=None):
    """
    Decorator that checks whether the user has one of the allowed roles.
    - If unauthenticated: redirects to LOGIN_URL with ?next=<path>.
    - If superuser: access is granted.
    - If user's role is in allowed_roles: access is granted.
    - If unauthorized: shows an access-denied message and redirects to the user's appropriate role dashboard.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = getattr(settings, 'LOGIN_URL', 'accounts:login')
                return redirect(f"{login_url}?next={request.path}")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = getattr(request.user, 'role', None)

            if user_role not in allowed_roles:
                view_name = getattr(view_func, '__name__', '')
                if user_role == 'freelancer':
                    if view_name == 'client_home':
                        return redirect('freelancer:freelancer_home')
                    elif view_name in ['client_proposals', 'proposals']:
                        return redirect('freelancer:my_proposals')
                    return redirect('freelancer:freelancer_dashboard')
                elif user_role == 'client':
                    if view_name == 'freelancer_home':
                        return redirect('client:client_home')
                    elif view_name in ['my_proposals', 'proposals']:
                        return redirect('client:client_proposals')
                    return redirect('client:client_dashboard')
                return redirect('home')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def freelancer_required(view_func):
    """Convenience decorator for freelancer-only views."""
    return role_required(['freelancer'])(view_func)


def client_required(view_func):
    """Convenience decorator for client-only views."""
    return role_required(['client'])(view_func)


def admin_required(view_func):
    """Convenience decorator for superuser/admin-only views."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = getattr(settings, 'LOGIN_URL', 'accounts:login')
            return redirect(f"{login_url}?next={request.path}")
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'admin':
            user_role = getattr(request.user, 'role', None)
            if user_role == 'freelancer':
                return redirect('freelancer:freelancer_dashboard')
            elif user_role == 'client':
                return redirect('client:client_dashboard')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
