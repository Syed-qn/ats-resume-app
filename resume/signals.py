# resume/signals.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_or_update_bootstrap_admin(**kwargs):
    cfg = getattr(settings, "ADMIN_CONFIG", {})
    username = cfg.get("USERNAME")
    email    = cfg.get("EMAIL")
    password = cfg.get("PASSWORD")

    if not all([username, email, password]):
        # Missing secrets – silently skip
        return

    User = get_user_model()
    user, _ = User.objects.update_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if not user.check_password(password):
        user.set_password(password)
        user.save()
