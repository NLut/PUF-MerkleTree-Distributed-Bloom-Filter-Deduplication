# PUF-Based Fog Authentication with Merkle Tree Proofs and Distributed Bloom Filter Deduplication for IIoT (Copy)

This full-stack system securely authenticates IIoT edge devices using **PUF (Physically Unclonable Functions)** and **Merkle Tree proofs**, transmits data with **HMAC integrity**, and performs **deduplication** using a high-performance **distributed Bloom Filter** implemented in C.

---

## Overview

| Module                      | Description |
|-----------------------------|-------------|
| Edge–Fog Auth + Transmission| PUF-based enrollment, authentication, secure transmission with HMAC |
| Merkle Tree (Fog)           | Membership verification for data authenticity |
| Bloom Filter Deduplication  | Multi-threaded deduplication on IIoT sensor data using hash filters |

---
## Project Structure

```
create_vm.sh
.
├── edge/                          # Edge node
│   ├── edge_enroll.py            # Enroll CRP with Fog
│   ├── edge_authen.py            # Authenticate with Fog
│   ├── data_transmission.py      # Send signed payloads
│   ├── puf_module.py             # Simulated PUF logic
│   ├── fuzzy_extractor.py        # Reed–Solomon fuzzy extractor
│   ├── .env                      # Edge environment
│   ├── requirements.txt
│   └── setup_venv.sh             # Create python venv

│
├── fog/                           # Fog node
│   ├── fog_client.py             # Flask API for enrollment/auth/data
│   ├── merkletree.py             # Merkle tree builder and proof generator
│   ├── fuzzy_extractor.py        # Same extractor logic as edge
│   ├── PUF_DB.json               # CRPs from Edge
│   ├── proof_db.json             # Merkle proofs
│   ├── .env                      # Fog environment                # C-based deduplication engine
│   ├── bloomfilter.c             # Main logic: filter + threading
│   ├── records.csv               # Input: IIoT data stream (from fog)
│   ├── non_duplicates.csv        # Output: Deduplicated result
│   └── requirements.txt
│   └── setup_venv.sh             # Create python venv
````
# Environment Setup
- Installing dependencies
- Setting up Google Cloud CLI (for VM use)
- Initializing Python virtual environment
- Setting up `.env` files

## Step 1: Install Google Cloud CLI
Follow the official guide: https://cloud.google.com/sdk/docs/install

## Step 2: Initialize Google Cloud CLI
After installing the `gcloud` CLI, initialize your environment:

```bash
gcloud init
```
- Sign in with your Google account.
- Select or create a Google Cloud project.
- Choose a default region and zone.

## Step 3: Create VM Instances (Edge and Fog)
```bash
chmod +x create_vm.sh
./create_vm.sh
```

```bash
gcloud compute firewall-rules create allow-fog-port5000 \
  --allow tcp:=5000 \
  --target-tags=fog-node \
  --direction=INGRESS \
  --priority=1000 \
  --description="Allow Flask API access"
```

## Step 4: SSH to each VM instance
Follow the official guide: https://cloud.google.com/compute/docs/connect/standard-ssh

## Step 5: Set Up Python Virtual Environment

```bash
# On both Edge and Fog VMs
sudo apt update && sudo apt install -y python3-venv git

# Inside your project directory (e.g. `/home/yourname/edge/`)
chmod +x setup_venv.sh
./setup_venv.sh
source .venv/bin/activate
```

## Step 6: Create .env Configuration Files

### 1. Configure `.env` (Fog Node)
Create a `.env` file in the `fog/` directory (e.g., `/home/user/fog/`) with the following content:

### Example .env
```env
# File management
RECORD_FILE=records.csv
CSV_FIELDS=DID,timestamp,type,value,leaf,tag

# Database files
TEMP_CHALLENGE_FILE=temp_challenge.json
PUF_DB_FILE=PUF_DB.json
PROOF_DB_FILE=proof_db.json

# Connection
PORT=5000
```
- start fog_client using:
  ```bash
  python fog_client.py
  ```
- The expected output:
  ```bash
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:5000
   * Running on http://10.148.0.2:5000
  ```

### 2. Configure `.env` (Edge Node)
Create a `.env` file in the `edge/` directory (e.g., `/home/user/edge/`) with the following content:

### Example .env (Local Test)
Use this when running **Edge** and **Fog** on the same machine (e.g., during local testing):

```env
NUM_CHALLENGE=10                # Number of challenge-response pairs (CRPs) to generate per enrollment
DID=EDGE1                       # Unique identifier of the Edge device
TYPE=temperature                # Type of sensor data being sent (e.g., temperature, humidity, etc.)
FREQUENCY=0.01                  # Time interval (in seconds) between each payload transmission
DELETE_AFTER_SECONDS=60         # Session expiration timeout in seconds (auto-deletes session file)
MAX_USES=1000                   # Maximum number of payloads allowed per authentication session

# === Endpoint URLs ===

ENROLL_URL=http://127.0.0.1:5000/enroll              # Endpoint to send DID and receive CRPs from the Fog node
CHALLENGE_URL=http://127.0.0.1:5000/send_challenge   # Endpoint to receive a random challenge for authentication
AUTH_URL=http://127.0.0.1:5000/auth_response         # Endpoint to send the authentication response
AUTH_RESPONSE_URL=http://127.0.0.1:5000/auth_response  # Alias for AUTH_URL (kept for backward compatibility)
SEND_PAYLOAD=http://127.0.0.1:5000/send_payload      # Endpoint to send authenticated data payloads to the Fog

# === Session File ===
SESSION_FILE=.session.json      # Path to local session file storing active session keys (P, K, C)
```

### Example .env (Between 2 VMs)
Use this format on your **Edge** when communicating with a **Fog** hosted on different VM:

```env
# === Configuration ===

NUM_CHALLENGE=10                # Number of challenge-response pairs (CRPs) to generate during enrollment
DID=EDGE1                       # Unique Device ID for the Edge node (must match across authentication and payload)
TYPE=temperature                # Sensor type being reported (e.g., temperature, humidity, pressure)
FREQUENCY=0.01                  # Delay (in seconds) between each payload transmission to Fog
DELETE_AFTER_SECONDS=60         # Time after which the session file is auto-deleted (session expiry)
MAX_USES=1000                   # Max number of payloads allowed before re-authentication is required

# === Endpoint URLs (Fog Node) ===

ENROLL_URL=http://10.148.0.2:5000/enroll              # Endpoint for Edge enrollment (sending DID, receiving challenges)
CHALLENGE_URL=http://10.148.0.2:5000/send_challenge   # Endpoint for receiving a random challenge for authentication
AUTH_URL=http://10.148.0.2:5000/auth_response         # Endpoint for sending authentication response {DID, C, P}
AUTH_RESPONSE_URL=http://10.148.0.2:5000/auth_response # Same as AUTH_URL; maintained for compatibility
SEND_PAYLOAD=http://10.148.0.2:5000/send_payload       # Endpoint for sending secure, signed sensor payloads

# === Session File ===

SESSION_FILE=.session.json      # File storing session data (challenge C, helper P, secret key K); auto-deleted after timeout

```
---

## PUF–Merkle Tree Secure Edge–Fog Framework

This project implements a secure **PUF-based authentication and data transmission framework** for IIoT edge–fog communication. It uses **Reed–Solomon fuzzy extractors** and **Merkle Trees** for device verification and **HMAC** for tamper-resistant data integrity.

---

## How It Works

### Enrollment Phase
### ▶ Run

```bash
  python edge_enroll.py
```

1. **Edge** generates challenge–response pairs (CRP) via PUF simulation
2. **Edge** derives `(P, K)` using a Reed–Solomon fuzzy extractor
3. **Edge** sends `{C, P, K}` to the **Fog Node**
4. **Fog** builds a Merkle Tree from all `(DID, C, P)` and generates proofs for each leaf

---

### Authentication Phase
### ▶ Run

```bash
  python edge_authen.py
```
1. **Fog** randomly selects a stored challenge `C` for a given `DID`
2. **Edge** computes `P` from its PUF and sends `{DID, C, P}` to the fog
3. **Fog** verifies `P` against the stored value in `PUF_DB.json`
4. On success, a session file `.session.json` is created for secure payload communication

---

### Data Transmission
### ▶ Run
```bash
  python datatransmission.py
```
1. **Edge** sends a signed payload with the following structure:
   ```json
   {
     "DID": "EDGE1",
     "timestamp": 1722299999,
     "data": { "type": "temperature", "value": 28.5 },
     "leaf": "<MerkleLeafHash>",
     "tag": "<HMAC(K, data|C|P|timestamp)>"
   }
## Distributed Bloom Filter Deduplication for IIoT Sensor Data

This C project implements a **distributed Bloom filter-based deduplication** system for large-scale **IIoT sensor data** stored in CSV format. It detects duplicates efficiently using a time-resetting Bloom filter per data type and exports only non-duplicate records.

---

## Input CSV Format

The system expects an input file named `records.csv` in the following format:

```csv
device_id,timestamp,type,value,leaf,tag
temp_sensor_01,2025-06-01T12:00:00,temperature,25.5,leafA,tagX
temp_sensor_02,2025-06-01T12:00:01,temperature,25.6,leafB,tagY
...
````

Each line represents a unique IIoT sensor reading.


## How It Works

* Groups records by `type` (e.g., temperature, humidity)
* Each thread processes one group using a 3-hash Bloom filter
* Resets the bit array after `RESET_INTERVAL` entries to limit false positives
* Non-duplicate records are written to `non_duplicates.csv`

---

## Compilation & Run

### Compile

```bash
gcc bloomfilter.c -o bloomfilter
```

### ▶ Run

```bash
./bloomfilter
```

### Output Example

```txt
=== Distributed Bloom Filter Summary ===
Total Records Processed: 1000000
Total Duplicates Detected: 120000
Processing Time: 4.3720 sec
Total Memory Used (RSS): 22.34 MB
```

The output file `non_duplicates.csv` will contain all unique records in the original CSV format.

---

## Configuration

You can modify these parameters in `bloomfilter.c`:

```c
#define BLOOM_SIZE     333333   // Bloom filter size (bits)
#define MAX_TYPES      5         // Max number of sensor types
#define MAX_RECORDS    50000    // Max records per type (not more than 50000) (if more than 50000, it will cause segmentation failed(linux default))
#define RESET_INTERVAL 20000     // Reset Bloom filter every N records
```

---

## Notes

* Uses `/proc/self/status` to fetch real memory (RSS) on **Linux**
* Designed to be run on **Linux-based VM or Edge devices**
* Handles up to 200k records with low memory footprint
* In case to check whether the output is having duplicated record or not you can change the load file name to check duplication in this line.
  ```
  load_csv("records.csv", groups, &group_count);
  ```


## License

This project is open-source and provided for educational and research purposes.


