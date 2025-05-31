import requests
from puf_module import PUF
from fuzzy_extractor import ReedSolomonFuzzyExtractor
from binascii import unhexlify
from edge_authen import authenticate
from dotenv import load_dotenv
import os

load_dotenv()

DID = os.getenv("DID")
ENROLL_URL = os.getenv("ENROLL_URL", "http://10.148.0.2:5000/enroll")

# Initialize fuzzy extractor
fe = ReedSolomonFuzzyExtractor(n_bytes=32, ecc_bytes=16)

def enrollment():
    print("\n=== Enrollment Phase ===")
    response = requests.post(ENROLL_URL, json={"DID": DID})
    if response.status_code != 200:
        print("Failed to get challenges:", response.text)
        return

    challenges = response.json()
    print(f"Received challenges for {DID}:", challenges)

    for C in challenges:
        Raw_R = PUF(C)
        payload = {
            "DID": DID,
            "C": C,
            "Raw_R": Raw_R
        }
        res = requests.post(ENROLL_URL, json=payload)
        print(f"Sent CRP for C={C}: {res.status_code}, {res.text}")
        
        # If last challenge triggers auth challenge, capture it
        try:
            data = res.json()
            if "next" in data:
                return data["next"]["C"]
        except Exception:
            pass

    return None

#def main():
#    challenge_from_enroll = enrollment()

#    if challenge_from_enroll:
#        authenticate(challenge_from_enroll)
#    else:
#        authenticate()
if __name__ == "__main__":
    enrollment()
