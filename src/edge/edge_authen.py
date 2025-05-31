# authenticate.py

import requests
import json
import time
from puf_module import PUF
from fuzzy_extractor import ReedSolomonFuzzyExtractor
from binascii import unhexlify
import threading
import os
from dotenv import load_dotenv

load_dotenv()

MAX_USES = int(os.getenv("MAX_USES", "1000"))
CHALLENGE_URL = os.getenv("CHALLENGE_URL", "http://10.148.0.2:5000/send_challenge")
AUTH_URL = os.getenv("AUTH_URL", "http://10.148.0.2:5000/auth_response")
SESSION_FILE = os.getenv("SESSION_FILE", ".session.json")
DID = os.getenv("DID")

fe = ReedSolomonFuzzyExtractor(n_bytes=32, ecc_bytes=16)

def authenticate(did=DID, challenge=None):
    if not challenge:
        resp = requests.post(CHALLENGE_URL, json={"DID": did})
        if resp.status_code != 200:
            print("Failed to get challenge:", resp.text)
            return False
        challenge = resp.json()["C"]

    Raw_R = PUF(challenge)
    raw_bytes = unhexlify(Raw_R)
    P_bytes, K_bytes = fe.gen(raw_bytes)

    payload = {
        "DID": did,
        "C": challenge,
        "P": P_bytes.hex()
    }

    resp = requests.post(AUTH_URL, json=payload)
    print(f"Auth response: {resp.status_code}, {resp.text}")

    if resp.status_code == 200:
        session = {
         "DID": did,
            "C": challenge,
            "session": True,
            "P": P_bytes.hex(),
            "K": K_bytes.hex(),
            "created_at": time.time(),
            "max_uses": MAX_USES,
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session, f, indent=2)
        print("Session created ✔")
        return True
    else:
        print("Authentication failed ❌")
        return False


if __name__ == "__main__":
    authenticate()
