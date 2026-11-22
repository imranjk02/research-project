
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),

    path("api/analyze", views.analyze, name="analyze"),
    path("api/build", views.build, name="build"),
    path("api/generate-thumbnail", views.generate_thumbnail, name="generate_thumbnail"),

    path("signin", views.signin, name="signin"),
    path("signup", views.signup, name="signup"),
    path("logout", views.logout, name="logout"),

    path("collection", views.collection, name="collection"),

    path(
        "download/<int:thumbnail_id>",
        views.download_thumbnail,
        name="download_thumbnail"
    ),

    path(
        "delete/<int:thumbnail_id>",
        views.delete_thumbnail,
        name="delete_thumbnail"
    ),
]
