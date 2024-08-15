from django.http import HttpResponseForbidden
from django.http.request import HttpRequest
from rest_framework.exceptions import PermissionDenied
from authentication.models import ApiUserProfile


def resolve_user_from_request(request: HttpRequest):
  token = request.headers.get("Authorization")
  
  if not token:
    raise PermissionDenied()
  
  user, created = ApiUserProfile.get_or_create_user(token)

  return user
