from django.urls import path

from .views import event_detail, history, home, mission, update_detail, updates, vision

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("mission/", mission, name="mission"),
    path("vision/", vision, name="vision"),
    path("history/", history, name="history"),
    path("updates/", updates, name="updates"),
    path("updates/<str:update_type>/<int:pk>/", update_detail, name="update_detail"),
    path("events/<int:pk>/", event_detail, name="event_detail"),
]
