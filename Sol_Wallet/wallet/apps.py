from flask import Flask, request, jsonify
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.rpc.api import Client  # Import Client here
import base58
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Solana endpoint
SOLANA_URL = os.getenv("SOLANA_URL", "https://api.mainnet-beta.solana.com")  # Default to mainnet
client = Client(SOLANA_URL)

# Blacklisted addresses
BLACKLIST = {"DpMcHVRUveeUS3xYh8APDPVySVxZXa79pfzjswGjDR6S"}

# Endpoint: Transfer SOL with blacklist check
@app.route('/wallet/transfer', methods=['POST'])
def transfer_sol():
    data = request.get_json()
    receiver_public_key = data.get("receiver_public_key")
    amount = data.get("amount")

    if not receiver_public_key or not amount:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be a positive number."}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount format."}), 400

    # Retrieve the sender private key from the .env file
    sender_private_key = os.getenv("SENDER_PRIVATE_KEY")
    if not sender_private_key:
        return jsonify({"error": "Sender private key is missing in environment."}), 500

    sender_keypair = Keypair.from_secret_key(base58.b58decode(sender_private_key))
    sender_public_key = str(sender_keypair.public_key)

    # Check if sender or receiver is blacklisted
    if sender_public_key in BLACKLIST:
        logging.warning(f"Blacklisted sender attempted transfer: {sender_public_key}")
        return jsonify({"error": "Sender address is blacklisted."}), 403
    if receiver_public_key in BLACKLIST:
        logging.warning(f"Blacklisted receiver attempted transfer: {receiver_public_key}")
        return jsonify({"error": "Receiver address is blacklisted."}), 403

    try:
        transfer_amount = int(amount * 1e9)  # Convert SOL to lamports

        # Create transaction
        transaction = Transaction().add(
            transfer(
                TransferParams(
                    from_pubkey=sender_keypair.public_key,
                    to_pubkey=receiver_public_key,
                    lamports=transfer_amount,
                )
            )
        )

        # Send transaction
        response = client.send_transaction(transaction, sender_keypair)
        if response.get("result"):
            logging.info(f"Transaction successful: {response['result']}")
            return jsonify({"transaction_id": response["result"]})

        logging.error(f"Transaction failed: {response}")
        return jsonify({"error": "Transaction failed"}), 500
    except Exception as e:
        logging.error(f"Transfer error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True)
