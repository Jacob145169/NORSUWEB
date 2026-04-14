from django.urls import path

from .views import (
    about,
    calendar,
    alumni,
    contact,
    core_values,
    event_detail,
    history,
    home,
    mission,
    mission_vision,
    quality_policy,
    strategic_goals,
    update_detail,
    updates,
    vision,
)

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("mission-vision/", mission_vision, name="mission_vision"),
    path("mission/", mission, name="mission"),
    path("vision/", vision, name="vision"),
    path("strategic-goals/", strategic_goals, name="strategic_goals"),
    path("core-values/", core_values, name="core_values"),
    path("quality-policy/", quality_policy, name="quality_policy"),
    path("history/", history, name="history"),
    path("calendar/", calendar, name="calendar"),
    path("alumni/", alumni, name="alumni"),
    path("contact/", contact, name="contact"),
    path("updates/", updates, name="updates"),
    path("updates/<str:update_type>/<int:pk>/", update_detail, name="update_detail"),
    path("events/<int:pk>/", event_detail, name="event_detail"),
]
