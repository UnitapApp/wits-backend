from django.db import models
from django.conf import settings

import requests


class ApiUserProfile(models.Model):

    @staticmethod
    def resolve_user(token: str):
        return requests.get(
            settings.UNITAP_API_HOST + "/auth/user/info/",
            headers={"Authorization": token},
        ).json()

    @staticmethod
    def get_or_create_user(token: str):
        try:
            user = requests.get(
                settings.UNITAP_API_HOST + "/auth/user/info/",
                headers={"Authorization": token},
            ).json()
            return ApiUserProfile.objects.get_or_create(
                defaults={"pk": user["pk"]}, pk=user["pk"]
            )
        except Exception as e:
            print(e)
            raise Exception("Invalid authentication token")

    @staticmethod
    def login():
        pass
