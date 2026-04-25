import paramiko
import os

# Credentials
HOST = "46.62.141.57"
USER = "root"
PASS = "Srisai@10@het"
LOCAL_SCRIPT = r"d:\Dev\Codex\ThetaEdge\scratch\test_futures_remote.py"
REMOTE_PATH = "/home/algo/ThetaEdge/scripts/test_futures.py"

def deploy_and_run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {HOST}...")
        ssh.connect(HOST, username=USER, password=PASS)
        
        # 1. Create directory
        print("Creating remote directory...")
        ssh.exec_command("mkdir -p /home/algo/ThetaEdge/scripts")
        
        # 2. Upload script
        print("Uploading script...")
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_SCRIPT, REMOTE_PATH)
        sftp.close()
        
        # 3. Run script
        print("Starting backfill on server (this may take a minute)...")
        # Use nohup or similar if it's very long, but 6 months of spot is fast.
        # We'll run it and wait for output.
        stdin, stdout, stderr = ssh.exec_command(f"/home/algo/ThetaEdge/venv/bin/python {REMOTE_PATH}")
        
        # Print output in real-time
        for line in stdout:
            print(f"[REMOTE] {line.strip()}")
            
        err = stderr.read().decode()
        if err:
            print(f"[REMOTE ERROR] {err}")
            
        print("Server-side execution finished.")
        
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    deploy_and_run()
