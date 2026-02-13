from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/rewards/(?P<userprofile_id>\w+)/$', consumers.RewardConsumer.as_asgi()),
]


