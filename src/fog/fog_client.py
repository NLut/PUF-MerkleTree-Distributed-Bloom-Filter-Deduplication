from flask import Flask, request, jsonify
import hashlib
import hmac
import json
import os
import random
import csv
from binascii import unhexlify
from fuzzy_extractor import ReedSolomonFuzzyExtractor
from merkletree import MerkleTree
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv() 
PORT = int(os.getenv("PORT", "5000"))
RECORD_FILE = os.getenv("RECORD_FILE", "records.csv")
CSV_FIELDS = os.getenv("CSV_FIELDS", "DID,timestamp,type,value,leaf,tag").split(",")
TEMP_CHALLENGE_FILE = os.getenv("TEMP_CHALLENGE_FILE", "temp_challenge.json")
PUF_DB_FILE = os.getenv("PUF_DB_FILE", "PUF_DB.json")
PROOF_DB_FILE = os.getenv("PROOF_DB_FILE", "proof_db.json")
NUM_CHALLENGE = int(os.getenv("NUM_CHALLENGE", "10"))
fe = ReedSolomonFuzzyExtractor(n_bytes=32, ecc_bytes=16)


@app.route('/enroll', methods=['POST'])
def enroll():
    data = request.json

    # === Case 1: Generate challenge set ===
    if "DID" in data and "C" not in data:
        DID = data["DID"]
        challenges = [f"C{i}" for i in range(NUM_CHALLENGE)]
        with open(TEMP_CHALLENGE_FILE, "w") as f:
            json.dump({DID: challenges}, f, indent=2)
        return jsonify(challenges), 200

    # === Case 2: Receive CRP from Edge ===
    elif all(k in data for k in ["DID", "C", "Raw_R"]):
        DID = data["DID"]
        C = data["C"]
        raw_hex = data["Raw_R"]

        try:
            raw_bytes = unhexlify(raw_hex)
        except Exception:
            return "Invalid Raw_R hex format", 400

        if len(raw_bytes) != 32:
            return "Raw_R must be 32 bytes (SHA256)", 400

        try:
            P_bytes, K_bytes = fe.gen(raw_bytes)
        except Exception as e:
            return f"Fuzzy extractor error: {str(e)}", 500

        P = P_bytes.hex()
        K = K_bytes.hex()

        # Load or initialize DB
        if os.path.exists(PUF_DB_FILE):
            with open(PUF_DB_FILE) as f:
                db = json.load(f)
        else:
            db = {}

        if DID not in db:
            db[DID] = []

        if any(entry["C"] == C for entry in db[DID]):
            return f"Challenge {C} for {DID} already exists. Skipped.", 200

        db[DID].append({"C": C, "P": P, "K": K})

        with open(PUF_DB_FILE, "w") as f:
            json.dump(db, f, indent=2)

        # If enrollment complete, build Merkle tree and return challenge
        print(len(db[DID]))
        if len(db[DID]) == NUM_CHALLENGE:
            mt = MerkleTree()
            mt.load_leaves_from_db(db)
            mt.build_tree()
            mt.generate_proofs()
            mt.save_proofs(PROOF_DB_FILE)
            root = mt.root()

            random_entry = random.choice(db[DID])
            return jsonify({
                "message": f"Enrollment complete.",
                "merkle_root": root,
                "next": {"DID": DID, "C": random_entry["C"]}
            })

        return f"CRP for {DID} stored."

    return "Invalid request format", 400


@app.route("/send_challenge", methods=["POST"])
def send_challenge():
    data = request.json
    DID = data.get("DID")
    if not DID:
        return "Missing DID", 400

    if not os.path.exists(PUF_DB_FILE):
        return "PUF_DB not found", 500

    with open(PUF_DB_FILE) as f:
        db = json.load(f)

    if DID not in db or not db[DID]:
        return "DID not enrolled", 404

    entry = random.choice(db[DID])
    return jsonify({"DID": DID, "C": entry["C"]})


@app.route("/auth_response", methods=["POST"])
def auth_response():
    data = request.json
    DID = data.get("DID")
    C = data.get("C")
    P_hex = data.get("P")

    if not all([DID, C, P_hex]):
        return "Missing one of DID, C, or P", 400

    if not os.path.exists(PUF_DB_FILE):
        return "PUF_DB not found", 500

    with open(PUF_DB_FILE) as f:
        db = json.load(f)

    if DID not in db:
        return "Unknown DID", 404

    for entry in db[DID]:
        if entry["C"] == C:
            stored_P = entry["P"]
            if P_hex == stored_P:
                return "Authentication successful", 200
            else:
                return "Authentication failed", 403

    return "Challenge not found for DID", 404

@app.route("/send_payload", methods=["POST"])
def receive_payload():
    data = request.json
    DID = data.get("DID")
    timestamp = data.get("timestamp")
    payload_data = data.get("data")
    leaf = data.get("leaf")
    tag = data.get("tag")

    # Load PUF_DB
    if not os.path.exists(PUF_DB_FILE):
        return "PUF_DB missing", 500
    with open(PUF_DB_FILE) as f:
        db = json.load(f)

    if DID not in db:
        return "DID not registered", 404

    # Search for matching leaf (C, P)
    matched = None
    for entry in db[DID]:
        candidate_leaf = hashlib.sha256(f"{DID}|{entry['C']}|{entry['P']}".encode()).hexdigest()
        if candidate_leaf == leaf:
            matched = entry
            break

    if not matched:
        return "Leaf not found", 403

    # Verify HMAC
    K = bytes.fromhex(matched["K"])
    msg = f"{json.dumps(payload_data)}|{matched['C']}|{matched['P']}|{timestamp}"
    computed_tag = hmac.new(K, msg.encode(), hashlib.sha256).hexdigest()

    if hmac.compare_digest(tag, computed_tag):
        print(f"[✔] Payload from {DID}: {payload_data}")

        # Check if the file needs a header
        write_header = not os.path.exists(RECORD_FILE)

        with open(RECORD_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "DID": DID,
                "timestamp": timestamp,
                "type": payload_data.get("type"),
                "value": payload_data.get("value"),
                "leaf": leaf,
                "tag": tag
        })
        return "Payload accepted ✅", 200
    else:
        return "Invalid tag ❌", 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
