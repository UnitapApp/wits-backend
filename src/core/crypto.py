
import json
from eth_account import Account
from eth_account.messages import encode_defunct
from django.utils import timezone



class Crypto:
  def __init__(self, minutes_to_verify=None) -> None:
    self.minutes_to_verify = minutes_to_verify or 2


  def sign_message(self, message: str, private_key):
    account = Account.from_key(private_key)
    signature = Account.sign_message(encode_defunct(text=message), private_key).signature.hex()
    return account.address, signature


  def verify_signature(self, address, message, signature):
        digest = encode_defunct(text=message)
        signer = Account.recover_message(digest, signature=signature)

        now = timezone.now()

        data = json.loads(message)

        signed_time = timezone.datetime.fromisoformat(
          data["message"]["IssuedAt"].replace("Z", "+00:00")
        )

        return signer == address and now - signed_time > timezone.timedelta(minutes=self.minutes_to_verify)