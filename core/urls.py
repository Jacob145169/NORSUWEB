from django.urls import path

from .views import history, home, mission, updates, vision

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("mission/", mission, name="mission"),
    path("vision/", vision, name="vision"),
    path("history/", history, name="history"),
    path("updates/", updates, name="updates"),
]
