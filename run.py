import argparse
import subprocess
import sys
import os
import requests
import time
import signal

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

from utils.config import Config

def train():
    print("--- V2 Intelligence Layer: Full Training Pipeline ---")
    print("1. Augmenting Text Data...")
    subprocess.run([sys.executable, os.path.join("data", "augment_data.py")], check=True)
    print("\n2. Training NLP Disruption Classifier...")
    subprocess.run([sys.executable, os.path.join("ml", "train_model.py")], check=True)
    print("\n3. Training Multi-Feature Company Model...")
    subprocess.run([sys.executable, os.path.join("ml", "company_train.py")], check=True)
    print("\n[OK] All Intelligence Layer Models trained successfully!")

def api():
    print("--- V2 API Layer ---")
    print(f"Starting uvicorn on {Config.API_HOST}:{Config.API_PORT}...")
    command = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", Config.API_HOST, "--port", str(Config.API_PORT)]
    if os.getenv("API_RELOAD", "true").lower() == "true":
        command.append("--reload")
    subprocess.run(command)

def ui():
    print("--- V2 Dashboard Layer ---")
    print(f"Starting Streamlit on port {Config.UI_PORT}...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", os.path.join("ui", "app.py"),
        "--server.address", Config.UI_HOST, "--server.port", str(Config.UI_PORT),
        "--server.headless", "true",
    ])

def check():
    print("--- V2 System Health Check ---")
    print("\n1. Intelligence Layer Files:")
    check_files = [
        Config.MODEL_PATH,
        Config.PIPELINE_PATH,
        Config.AUGMENTED_DATASET_PATH,
        os.path.join(Config.ARTEFACTS_DIR, "company_model.pkl"),
        os.path.join(Config.ARTEFACTS_DIR, "company_encoders.pkl"),
        os.path.join(Config.ARTEFACTS_DIR, "company_training_report.json"),
        os.path.join(Config.DATA_DIR, "supplychain.db")
    ]
    for f in check_files:
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
    print("--- Supply Chain Control Center: launching API and dashboard ---")
    signal.signal(signal.SIGTERM, _handle_termination)
    api_command = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", Config.API_HOST, "--port", str(Config.API_PORT)]
    if os.getenv("API_RELOAD", "true").lower() == "true":
        api_command.append("--reload")
    api_process = subprocess.Popen(api_command)
    ui_process = None
    try:
        for _ in range(60):
            if api_process.poll() is not None:
                raise RuntimeError("The API stopped before it became ready.")
            try:
                response = requests.get(f"http://127.0.0.1:{Config.API_PORT}/monitor/health", timeout=1)
                if response.ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("The API did not become ready within 60 seconds.")

        ui_command = [
            sys.executable, "-m", "streamlit", "run", os.path.join("ui", "app.py"),
            "--server.address", Config.UI_HOST, "--server.port", str(Config.UI_PORT),
            "--server.headless", "true",
        ]
        ui_process = subprocess.Popen(ui_command)
        while True:
            if api_process.poll() is not None:
                raise RuntimeError("The API process stopped.")
            if ui_process.poll() is not None:
                raise RuntimeError("The dashboard process stopped.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services gracefully...")
    finally:
        for process in (ui_process, api_process):
            if process is not None and process.poll() is None:
                process.terminate()
        for process in (ui_process, api_process):
            if process is not None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()


def _handle_termination(signum, frame):
    raise KeyboardInterrupt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity V2 Launcher")
    parser.add_argument("command", choices=["train", "api", "ui", "check", "all"], help="Command to run")
    
    args = parser.parse_args()
    try:
        if args.command == "train": train()
        elif args.command == "api": api()
        elif args.command == "ui": ui()
        elif args.command == "check": check()
        elif args.command == "all": all_services()
    except Exception as e:
        print(f"Fatal error executing command '{args.command}': {e}")
