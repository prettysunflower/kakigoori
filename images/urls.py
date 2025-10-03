from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload", views.upload, name="images.upload"),
    path("<uuid:image_id>/<str:image_type>", views.get, name="images.get"),
    path(
        "<uuid:image_id>/<str:image_type>/thumbnail",
        views.get_thumbnail,
        name="images.get_thumbnail",
    ),
    path(
        "<uuid:image_id>/height/<int:height>/<str:image_type>",
        views.get_image_with_height,
        name="images.get_image_with_height",
    ),
    path(
        "<uuid:image_id>/width/<int:width>/<str:image_type>",
        views.get_image_with_width,
        name="images.get_image_with_width",
    ),
]
