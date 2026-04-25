#!/bin/bash
# ThetaEdge S1 Deployment Script
# Usage: bash deploy/deploy_S1.sh YOUR_HETZNER_IP

HETZNER_IP=$1
DEPLOY_USER="algo"
DEPLOY_PATH="/home/algo/ThetaEdge"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_NAME="ThetaEdge_S1_${TIMESTAMP}.zip"

if [ -z "$HETZNER_IP" ]; then
    echo "Usage: bash deploy/deploy_S1.sh YOUR_HETZNER_IP"
    exit 1
fi

echo "Packaging ThetaEdge S1..."
# Use absolute path for reliability in script
cd D:/Dev/Codex/ThetaEdge

zip -r $ZIP_NAME \
  shared/ \
  S1_straddle/ \
  requirements.txt \
  README.md \
  .env.example \
  --exclude "*.pyc" \
  --exclude "__pycache__/*" \
  --exclude "S1_straddle/logs/*" \
  --exclude ".env" \
  --exclude "shoonyakey.txt"

echo "Deploying to Hetzner: $HETZNER_IP..."
scp $ZIP_NAME ${DEPLOY_USER}@${HETZNER_IP}:${DEPLOY_PATH}/

ssh ${DEPLOY_USER}@${HETZNER_IP} "
  cd ${DEPLOY_PATH} &&
  unzip -o ${ZIP_NAME} &&
  pip install -r requirements.txt --quiet &&
  crontab ${DEPLOY_PATH}/deploy/crontab_s1.txt &&
  echo '[DEPLOY] Cron jobs installed successfully:' &&
  crontab -l | tail -n 10
"

echo "Cleanup local zip..."
rm $ZIP_NAME
echo "Done. ThetaEdge S1 is live on Hetzner."
