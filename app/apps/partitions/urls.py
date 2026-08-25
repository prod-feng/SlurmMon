from django.urls import path

from . import views

app_name = "partitions"

urlpatterns = [
    path("", views.partition_list, name="list"),
    path(
        "<str:partition_name>/",
        views.partition_detail,
        name="detail",
    ),
]

