from django.urls import include, path

urlpatterns = [
    path("", include("backend.django_api.urls")),
]
