
from rest_framework.generics import (
    CreateAPIView,
    RetrieveUpdateAPIView
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from authentication.models import UserProfile
from authentication.serializers import AuthenticateSerializer, UserProfileSerializer

from web3 import Web3

import uuid


class GetProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user.profile # type: ignore
    

class AuthenticateView(CreateAPIView):
    serializer_class = AuthenticateSerializer
    queryset = UserProfile.objects.filter(user__is_active=True)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)

        wallet_address = serializer.validated_data["wallet_address"]

        try:
            profile = UserProfile.objects.get(
                wallet_address=Web3.to_checksum_address(wallet_address)
            )
        except UserProfile.DoesNotExist:
            user = User.objects.create_user(username="WITS" + str(uuid.uuid4())[:16])

            profile = UserProfile.objects.create(
                wallet_address=Web3.to_checksum_address(wallet_address),
                user=user
            )
        
        return Response(UserProfileSerializer(instance=profile).data, status=status.HTTP_201_CREATED, headers=headers)
        