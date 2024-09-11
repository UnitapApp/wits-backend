from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("quiz/", include("quiz.urls")),
    path("auth/", include("authentication.urls")),
    path("stats/", include("stats.urls")),
]
