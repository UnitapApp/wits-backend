from django.urls import re_path

from quiz import consumers

websocket_urlpatterns = [
    re_path(r'ws/quiz/(?P<competition_id>\d+)/$', consumers.QuizConsumer.as_asgi()),
]