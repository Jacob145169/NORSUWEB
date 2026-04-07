from django.contrib import admin

from .models import Announcement, Event, News


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "posted_by", "date_posted")
    list_filter = ("department", "date_posted")
    search_fields = ("title", "content")
    date_hierarchy = "date_posted"


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "posted_by", "date_posted")
    list_filter = ("department", "date_posted")
    search_fields = ("title", "content")
    date_hierarchy = "date_posted"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "event_date", "end_date", "location", "posted_by")
    list_filter = ("department", "event_date", "end_date")
    search_fields = ("title", "description", "location")
    date_hierarchy = "event_date"
