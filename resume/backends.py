from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()

class EmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        login = username or kwargs.get("email")
        if not login:
            return None
        try:
            user = User.objects.get(email__iexact=login)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username__iexact=login)
            except User.DoesNotExist:
                return None
        return user if user.check_password(password) else None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
