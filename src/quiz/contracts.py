import web3
import logging

from django.conf import settings
from web3 import Web3
from eth_account import Account
from web3.middleware import geth_poa_middleware


logger = logging.getLogger(__name__)

wits_contract_abi = [{"inputs":[{"internalType":"address","name":"_logic","type":"address"},{"internalType":"address","name":"initialOwner","type":"address"},{"internalType":"bytes","name":"_data","type":"bytes"}],"stateMutability":"payable","type":"constructor"},{"inputs":[{"internalType":"address","name":"target","type":"address"}],"name":"AddressEmptyCode","type":"error"},{"inputs":[{"internalType":"address","name":"admin","type":"address"}],"name":"ERC1967InvalidAdmin","type":"error"},{"inputs":[{"internalType":"address","name":"implementation","type":"address"}],"name":"ERC1967InvalidImplementation","type":"error"},{"inputs":[],"name":"ERC1967NonPayable","type":"error"},{"inputs":[],"name":"FailedInnerCall","type":"error"},{"inputs":[],"name":"ProxyDeniedAdminAccess","type":"error"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"previousAdmin","type":"address"},{"indexed":False,"internalType":"address","name":"newAdmin","type":"address"}],"name":"AdminChanged","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"implementation","type":"address"}],"name":"Upgraded","type":"event"},{"stateMutability":"payable","type":"fallback"}]



wits_contract_address = "0x1042a37E7E0Fc24adCFbbF82919Da8631003b9D1"



class ContractManager:
    def __init__(self, address=None, private_key=None, abi=None) -> None:
        self.instance = Web3(Web3.HTTPProvider(settings.OP_MAINNET_RPC_URL))
        self.contract = self.instance.eth.contract(address=address or wits_contract_address, abi=abi or wits_contract_abi)
        self.private_key = private_key or settings.OPTIMISM_DISTRIBUTOR_PRIVATE_KEY

        if self.instance.is_connected() is False:
            raise Exception("instance must be connected")

        if not settings.OPTIMISM_DISTRIBUTOR_PRIVATE_KEY:
            raise Exception("Optimism private key must be present") 
        
        self.account = Account.from_key(private_key or settings.OPTIMISM_DISTRIBUTOR_PRIVATE_KEY)
    
    def estimate_gas(self, tx):
        return web3.eth.estimate_gas(tx)

    def distribute(self, addresses, amounts):
        distribute = self.contract.functions.distribute(addresses, amounts)
        gas = distribute.estimate_gas()

        transaction = self.contract.functions.distribute(addresses, amounts).build_transaction({
            'chianId': 10,
            'gas': gas,
            'gasPrice': self.instance.to_wei('0.001', 'gwei'),
            'nonce': self.instance.eth.get_transaction_count(self.account.address),
        })

        signed_tx = self.instance.eth.account.sign_transaction(transaction, private_key=self.private_key)

        txn_hash = self.instance.eth.send_raw_transaction(signed_tx.rawTransaction)

        txn_receipt = self.instance.eth.wait_for_transaction_receipt(txn_hash)

        return txn_receipt