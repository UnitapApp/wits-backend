import jwt
from jwt import InvalidTokenError
from django.conf import settings
import jwt.algorithms
from more_itertools import first
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User
import requests

from authentication.models import PrivyProfile, UserProfile


PUBLIC_KEY_URL = settings.PRIVY_JWKS_URL


def get_public_key():
    response = requests.get(PUBLIC_KEY_URL)

    assert response.ok, "Unable to fetch public keys"

    jwks = response.json()

    return jwt.algorithms.ECAlgorithm.from_jwk(jwks["keys"][0])


def get_privy_user_by_id(privy_id: str):
    response = requests.get(
        f"https://auth.privy.io/api/v1/users/{privy_id}",
        auth=(settings.PRIVY_APP_ID, settings.PRIVY_APP_SECRET),
        headers={"privy-app-id": settings.PRIVY_APP_ID},
    )

    assert response.ok, "Unable to get privy user"

    return response.json()


class PrivyJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            token = auth_header.split(" ")[1]
            public_key = get_public_key()

            payload = jwt.decode(token, public_key, algorithms=["ES256"])

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationFailed("User not found in token")

            privy_user = PrivyProfile.objects.filter(id=user_id).first()

            if privy_user:
                return (privy_user.profile.user, token)

            privy_data = get_privy_user_by_id(user_id)

            wallet_address = first(
                filter(
                    lambda account: account["imported"] is False
                    and account["walletClient"] == "privy",
                    privy_data["linkedAccounts"],
                )
            )

            user = User.objects.create(username=user_id)

            user_profile = UserProfile.objects.create(
                wallet_address=wallet_address, user=user, username=f"User {user.pk}"
            )

            privy_user = PrivyProfile.objects.create(profile=user_profile, id=user_id)

            return (user, token)
        except Exception as e:
            print(e)
            raise AuthenticationFailed("Invalid token")
