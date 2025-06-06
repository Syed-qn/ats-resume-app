# resume/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(BaseBackend):
    """
    Authenticate with *only* the user's e-mail address.
    • `username` is completely ignored (it can be blank or duplicated).
    • `email` must be unique and is matched case-insensitively.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Accept either `username` or explicit `email` kwarg – treat both as e-mail
        email = username or kwargs.get("email")
        if not email or not password:
            return None

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

        return user if user.check_password(password) else None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
