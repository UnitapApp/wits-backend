"""
ASGI config for witswin project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'witswin.settings')

django_asgi_app = get_asgi_application()

from .middleware import BasicTokenHeaderAuthentication
from witswin.routing import websocket_urlpatterns



application = ProtocolTypeRouter({
  "http": django_asgi_app,
  "websocket": AllowedHostsOriginValidator(BasicTokenHeaderAuthentication(
    URLRouter(websocket_urlpatterns)
  )),
})
