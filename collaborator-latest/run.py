import argparse
import subprocess
import sys
import os
import requests
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

from utils.config import Config

def train():
    print("--- V2 Intelligence Layer ---")
    print("1. Augmenting Data...")
    subprocess.run([sys.executable, os.path.join("data", "augment_data.py")], check=True)
    print("\n2. Training Text Risk Model...")
    subprocess.run([sys.executable, os.path.join("ml", "train_model.py")], check=True)
    print("\n3. Training Company Event Model...")
    subprocess.run([sys.executable, os.path.join("ml", "company_train.py")], check=True)

def seed():
    print("--- Reseeding database with fresh shipments ---")
    from db.reseed_db import reseed
    reseed()

def api():
    print("--- V2 API Layer ---")
    print(f"3D Command Center will be served at http://localhost:{Config.API_PORT}/")
    print(f"Starting uvicorn on {Config.API_HOST}:{Config.API_PORT}...")
    subprocess.run([sys.executable, "-m", "uvicorn", "api.main:app", "--host", Config.API_HOST, "--port", str(Config.API_PORT), "--reload"])

def ui():
    print("--- V2 Dashboard Layer ---")
    print(f"Starting Streamlit on port {Config.UI_PORT}...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.join("ui", "app.py"), "--server.port", str(Config.UI_PORT)])

def check():
    print("--- V2 System Health Check ---")
    print("\n1. Intelligence Layer Files:")
    for f in [Config.PIPELINE_PATH, Config.COMPANY_MODEL_PATH, Config.AUGMENTED_DATASET_PATH, Config.DB_PATH]:
        status = "[OK] Found" if os.path.exists(f) else "[X] Missing"
        print(f"  {os.path.basename(f)}: {status}")
        
    print("\n2. API Health Check:")
    try:
        response = requests.get(f"http://127.0.0.1:{Config.API_PORT}/monitor/health", timeout=2)
        if response.status_code == 200:
            print("  [OK] API is Online.")
            print(f"  Response: {response.json()}")
        else:
            print(f"  [!] API returned status {response.status_code}")
    except Exception as e:
        print("  [X] API is Offline. Start it with 'python run.py api'")

def all_services():
    print("--- Antigravity V2 Initialization: Launching All Services ---")
    from utils.bootstrap import ensure_ready
    ensure_ready()
    print(f"3D Command Center : http://localhost:{Config.API_PORT}/")
    print(f"Streamlit console : http://localhost:{Config.UI_PORT}/")
    
    api_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", Config.API_HOST, "--port", str(Config.API_PORT), "--reload"])
    
    time.sleep(3)
    
    ui_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", os.path.join("ui", "app.py"), "--server.port", str(Config.UI_PORT)])
    
    try:
        api_process.wait()
        ui_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down services gracefully...")
        api_process.terminate()
        ui_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity V2 Launcher")
    parser.add_argument("command", choices=["train", "seed", "api", "ui", "check", "all"], help="Command to run")
    
    args = parser.parse_args()
    try:
        if args.command == "train": train()
        elif args.command == "seed": seed()
        elif args.command == "api": api()
        elif args.command == "ui": ui()
        elif args.command == "check": check()
        elif args.command == "all": all_services()
    except Exception as e:
        print(f"Fatal error executing command '{args.command}': {e}")
        sys.exit(1)
