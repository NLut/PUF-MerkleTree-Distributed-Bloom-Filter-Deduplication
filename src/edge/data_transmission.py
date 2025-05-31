import time
import json
import random
import hmac
import hashlib
import requests
import os
from datetime import datetime
from edge_authen import authenticate
from dotenv import load_dotenv

load_dotenv()  # Loads values from .env

FREQUENCY = float(os.getenv("FREQUENCY", 0.1))
SEND_PAYLOAD = os.getenv("SEND_PAYLOAD", "http://10.148.0.2:5000/send_payload")
SESSION_FILE = os.getenv("SESSION_FILE", ".session.json")
TYPE = os.getenv("TYPE", "temperature")

def load_session():
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERROR] Session not found. Please authenticate first.")
        return None

def generate_payload():
    if TYPE == "temperature":
        value = round(random.uniform(20.0, 35.0), 2)
    elif TYPE == "humidity":
        value = round(random.uniform(30.0, 80.0), 2)
    elif TYPE == "pressure":
        value = round(random.uniform(980.0, 1050.0), 2)
    elif TYPE == "light":
        value = round(random.uniform(100.0, 1000.0), 2)
    elif TYPE == "co2":
        value = round(random.uniform(300.0, 1000.0), 2)
    else:
        raise ValueError(f"Unsupported sensor type: {TYPE}")

    return {
        "type": TYPE,
        "value": value
    }
def compute_leaf(DID, C, P):
    return hashlib.sha256(f"{DID}|{C}|{P}".encode()).hexdigest()

def compute_tag(K_hex, data, C, P, timestamp):
    msg = f"{json.dumps(data)}|{C}|{P}|{timestamp}"
    return hmac.new(bytes.fromhex(K_hex), msg.encode(), hashlib.sha256).hexdigest()

def send_data():
    session = load_session()
    while not session:
        print("No session: Please do authentication")
        return
    max_use = session["max_uses"]
    DID = session["DID"]
    C = session["C"]
    P = session["P"]
    K = session["K"]
    leaf = compute_leaf(DID, C, P)

    while max_use > 0:
        timestamp = int(time.time())
        data = generate_payload()
        tag = compute_tag(K, data, C, P, timestamp)

        payload = {
            "DID": DID,
            "timestamp": timestamp,
            "data": data,
            "leaf": leaf,
            "tag": tag
        }

        try:
            response = requests.post(SEND_PAYLOAD, json=payload)
            print(f"[{datetime.now()}] Sent payload: {response.status_code} {response.text}")
        except Exception as e:
            print(f"[ERROR] Transmission failed: {e}")

        max_use -= 1
        time.sleep(FREQUENCY)

    if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            print(f"[INFO] Session ended. '{SESSION_FILE}' deleted.")
            print("[ACTION REQUIRED] Please run authentication again to start a new session.")    

if __name__ == "__main__":
    send_data()

