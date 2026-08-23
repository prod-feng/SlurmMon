from django.urls import path

from . import views

app_name = "nodes"

urlpatterns = [
    path("", views.node_list, name="list"),
    path("<str:node>/drain/", views.drain_node, name="drain"),
    path("<str:node>/resume/", views.resume_node, name="resume"),
]

