# middleware.py
import base64
from http.cookies import SimpleCookie

from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from channels.db import database_sync_to_async

@database_sync_to_async
def get_user_from_basic_auth(tk: str):
    try:
        token = Token.objects.filter(key=tk).first()

        return token.user if token is not None else AnonymousUser()
    except Exception:
        return AnonymousUser()


class BasicTokenHeaderAuthentication:
    """
    Custom middleware (insecure) that takes user IDs from the query string.
    """

    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):

        headers = dict(scope["headers"])
        cookie = SimpleCookie()
        cookie.load(str(headers[b'cookie']))

        if "userToken" in cookie.keys():
            scope["user"] = await get_user_from_basic_auth(cookie.get("userToken").value) # type: ignore
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
