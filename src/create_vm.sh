#!/bin/bash
# create_vms.sh

ZONE="asia-southeast1-b"
IMAGE="debian-11"
EDGE_MACHINE="e2-small"
FOG_MACHINE="e2-standard-4"

gcloud compute instances create edge-device1 \
  --zone=$ZONE \
  --image-family=$IMAGE \
  --image-project=debian-cloud \
  --machine-type=$EDGE_MACHINE

gcloud compute instances create fog-node \
  --zone=$ZONE \
  --image-family=$IMAGE \
  --image-project=debian-cloud \
  --machine-type=$FOG_MACHINE

echo "✔ Edge and Fog VMs created in $ZONE"
