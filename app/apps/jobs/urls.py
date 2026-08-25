from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.job_list, name="list"),
    path("<str:job_id>/", views.job_detail, name="detail"),
]

