from django.apps import AppConfig


class DjangoApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.django_api"

    def ready(self) -> None:
        from .startup import initialize_backend

        initialize_backend()
