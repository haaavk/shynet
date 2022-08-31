from django.urls import path

from . import views

urlpatterns = [
    path("", views.ShyDBApiView.as_view(), name="shydb"),
]
