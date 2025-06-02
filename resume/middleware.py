# resume/middleware.py - Task 14: Authentication middleware

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings

class SPAAuthenticationMiddleware:
    """
    Middleware to ensure only authenticated users can access the SPA dashboard
    Task 14: No one should be able to access spa.html or resume creating service without logging in
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that require authentication
        self.protected_paths = [
            '/app/',  # SPA dashboard
            '/api/',  # All API endpoints
            '/templates/',  # Template endpoints
            '/manual-resume/',  # Manual resume creation
            '/admin-panel/',  # Admin panel
        ]
        
        # URLs that should be accessible without authentication
        self.public_paths = [
            '/',  # Landing page
            '/login/',
            '/signup/',
            '/password-reset/',
            '/ats-details/',
            '/our-services/',
            '/static/',
            '/media/',
            '/admin/',  # Django admin (has its own auth)
        ]

    def __call__(self, request):
        # Check if the request path requires authentication
        if self.requires_authentication(request.path):
            if not request.user.is_authenticated:
                # Store the original URL they were trying to access
                request.session['next_url'] = request.get_full_path()
                
                # Add an informative message
                messages.warning(
                    request, 
                    '🔒 Please log in to access the resume optimizer dashboard. '
                    'Create a free account if you don\'t have one yet!'
                )
                
                # Redirect to login page
                return redirect('login')
        
        response = self.get_response(request)
        return response

    def requires_authentication(self, path):
        """Check if a path requires authentication"""
        
        # Check if path is explicitly public
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return False
        
        # Check if path requires authentication
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        
        # Default to not requiring authentication for other paths
        return False


# Alternative function-based middleware (if you prefer)
def spa_authentication_middleware(get_response):
    """
    Alternative function-based middleware for SPA authentication
    """
    
    def middleware(request):
        protected_paths = ['/app/', '/api/', '/templates/', '/manual-resume/', '/admin-panel/']
        public_paths = ['/', '/login/', '/signup/', '/password-reset/', '/ats-details/', '/our-services/', '/static/', '/media/', '/admin/']
        
        # Check if path requires authentication
        requires_auth = False
        for protected_path in protected_paths:
            if request.path.startswith(protected_path):
                requires_auth = True
                break
        
        # Override if path is explicitly public
        for public_path in public_paths:
            if request.path.startswith(public_path):
                requires_auth = False
                break
        
        if requires_auth and not request.user.is_authenticated:
            request.session['next_url'] = request.get_full_path()
            messages.warning(
                request, 
                '🔒 Please log in to access the resume optimizer. Create a free account if you don\'t have one!'
            )
            return redirect('login')
        
        response = get_response(request)
        return response
    
    return middleware


# Custom decorator for view-based protection (alternative approach)
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

def spa_login_required(view_func):
    """
    Custom decorator that adds a specific message for SPA access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(
                request,
                '🔒 Please log in to access the ATS Resume Optimizer dashboard. '
                'Your career optimization tools are waiting!'
            )
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

