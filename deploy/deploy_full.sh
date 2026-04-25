#!/bin/bash
# ThetaEdge - Full Production Deployment Script
# Targets: Hetzner server (Asia/Kolkata timezone)

# Note: In a local environment, this reads credentials from the neighbor .env
HETZNER_IP=$(grep HETZNER_IP ../option-historical_data/.env | cut -d '=' -f2 | tr -d '\r')
HETZNER_USER=$(grep HETZNER_USER ../option-historical_data/.env | cut -d '=' -f2 | tr -d '\r')
HETZNER_PASS=$(grep HETZNER_PASS ../option-historical_data/.env | cut -d '=' -f2 | tr -d '\r')

REMOTE_USER_HOME="/home/algo"
REMOTE_PATH="$REMOTE_USER_HOME/ThetaEdge"
ZIP_FILE="ThetaEdge_Deploy.zip"

echo "🚀 Preparing deployment package..."
# Clean zip of current directory
zip -r $ZIP_FILE . -x "*.env" "*/logs/*" "*/data/*.db" "*/__pycache__/*" "deploy/ThetaEdge_Deploy.zip" ".git/*"

echo "📂 Creating remote directory: $REMOTE_PATH"
# Attempt to create user home and path
sshpass -p "$HETZNER_PASS" ssh -o StrictHostKeyChecking=no $HETZNER_USER@$HETZNER_IP "mkdir -p $REMOTE_PATH"

echo "📤 Transferring package..."
sshpass -p "$HETZNER_PASS" scp $ZIP_FILE $HETZNER_USER@$HETZNER_IP:$REMOTE_PATH/

echo "🛠️ Remote Setup and Initialization..."
sshpass -p "$HETZNER_PASS" ssh $HETZNER_USER@$HETZNER_IP << EOF
    cd $REMOTE_PATH
    unzip -o $ZIP_FILE
    rm $ZIP_FILE
    
    # Ensure logs and data dirs exist on remote
    mkdir -p S1_straddle/logs S1_straddle/data
    
    # Setup dependencies
    pip3 install pandas schedule requests jugaad-data --upgrade
    
    # Initialize Databases
    export PYTHONPATH=.
    python3 shared/db_initializer.py
    
    # Initial 5-day Data Backfill
    python3 shared/data_vault.py --backfill
    
    # Install Crontab
    crontab deploy/crontab_s1.txt
EOF

echo "✅ DEPLOYMENT SUCCESSFUL"
echo "Location: $HETZNER_IP:$REMOTE_PATH"
echo "Status: Active & Scheduled (IST Timezone)"
rm $ZIP_FILE
