import os
import json
import logging
from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account

# === CONFIG === #
WALLET_FILE = "wallet.json"
CONTRACT_ADDRESS = '0xc2132d05d31c914a87c6611c10748aeb04b58e8f'  # USDT contract on Polygon
WITHDRAW_AMOUNT_WEI = 1000000  # 1 USDT (6 decimals)
POLYGON_RPC = 'https://polygon-rpc.com'

# === ERC-20 ABI === #
CONTRACT_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [
            {"name": "", "type": "bool"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "account", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [
            {"name": "", "type": "uint256"}
        ],
        "type": "function"
    }
]

# === LOGGING === #
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# === WALLET MGMT === #
def load_or_create_wallet():
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, 'r') as f:
            data = json.load(f)
            logger.info(f"Using existing wallet: {data['address']}")
            return data['address'], data['private_key']
    else:
        acct = Account.create()
        wallet_data = {
            "address": acct.address,
            "private_key": acct.key.hex()
        }
        with open(WALLET_FILE, 'w') as f:
            json.dump(wallet_data, f)
        logger.info(f"New wallet generated and saved: {acct.address}")
        return acct.address, acct.key.hex()

# === POLYGON CONNECTION === #
def connect_to_polygon():
    web3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    if not web3.is_connected():
        raise ConnectionError("Failed to connect to Polygon network.")
    logger.info("Connected to Polygon network.")
    return web3

# === USDT TRANSFER === #
def transfer_usdt(web3, address, private_key):
    try:
        contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
        nonce = web3.eth.get_transaction_count(address)
        txn = contract.functions.transfer(
            '0xd23aaC8184B0Ad5BD70adD5267dCC5875C666037',  # Your destination address
            WITHDRAW_AMOUNT_WEI
        ).build_transaction({
            'chainId': 137,
            'gas': 200000,
            'gasPrice': web3.to_wei('30', 'gwei'),
            'nonce': nonce
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=private_key)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(f"Transaction sent: {txn_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
        if receipt.status == 1:
            logger.info("✅ USDT transfer successful.")
        else:
            logger.error("❌ USDT transfer failed.")
    except TransactionNotFound:
        logger.error("Transaction not found.")
    except Exception as e:
        logger.error(f"Transaction error: {e}")

# === MAIN ENTRY === #
def main():
    try:
        address, private_key = load_or_create_wallet()
        logger.info(f"Wallet address: {address}")
        web3 = connect_to_polygon()

        # Check MATIC balance
        native_balance = web3.eth.get_balance(address)
        logger.info(f"MATIC balance: {web3.from_wei(native_balance, 'ether')} MATIC")
        if native_balance < web3.to_wei(0.02, 'ether'):
            logger.warning("Insufficient MATIC to cover gas. Fund wallet with at least 0.02 MATIC.")
            return

        # Check USDT balance
        contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
        usdt_balance = contract.functions.balanceOf(address).call()
        logger.info(f"USDT balance: {usdt_balance / 10**6} USDT")
        if usdt_balance < WITHDRAW_AMOUNT_WEI:
            logger.warning("Insufficient USDT in wallet to transfer. Fund wallet and re-run.")
            return

        # Send transaction
        transfer_usdt(web3, address, private_key)

    except Exception as e:
        logger.critical(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
