from django.urls import path

from .views import department_detail, department_list

app_name = "departments"

urlpatterns = [
    path("", department_list, name="list"),
    path("<slug:slug>/", department_detail, name="detail"),
]
