from rest_framework import serializers

from authentication.models import UserProfile
from core.crypto import Crypto



class UserProfileSerializer(serializers.ModelSerializer):
  class Meta:
    model = UserProfile
    fields = ['pk', 'wallet_address', 'username']
    read_only_fields = ['wallet_address']



class AuthenticateSerializer(serializers.Serializer):
  address = serializers.CharField( max_length=256)
  signature = serializers.CharField()
  message = serializers.CharField()

  def is_valid(self, *, raise_exception=False):
    is_data_valid = super().is_valid(raise_exception=raise_exception)

    if is_data_valid is False:
      return is_data_valid
    
    crypto = Crypto()

    assert type(self.validated_data) == dict, "validated data must not be empty"


    return crypto.verify_signature(self.validated_data.get("address"), self.validated_data.get("message"), self.validated_data.get("signature"))
