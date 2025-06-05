# resume/apps.py
from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import get_user_model

class ResumeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "resume"           # ← keep your app label

    def ready(self):
        # Only registers the signal; nothing touches the DB yet
        import resume.signals  # noqa

    # def ready(self):
    #     """Create or update the bootstrap super-user on every boot."""
    #     cfg = getattr(settings, "ADMIN_CONFIG", {})          # already in settings.py:contentReference[oaicite:7]{index=7}
    #     username = cfg.get("USERNAME")
    #     email    = cfg.get("EMAIL")
    #     password = cfg.get("PASSWORD")

    #     if username and email and password:
    #         User = get_user_model()
    #         user, created = User.objects.update_or_create(
    #             username=username,
    #             defaults={
    #                 "email": email,
    #                 "is_staff": True,
    #                 "is_superuser": True,
    #             },
    #         )
    #         if created or not user.check_password(password):
    #             user.set_password(password)
    #             user.save()
