"""Build model artifacts for Vercel; deployment never trains or reseeds at runtime."""
from pathlib import Path
from data.augment_data import augment_dataset
from ml.train_model import train_and_evaluate
from ml.company_train import train as train_company_model
from utils.config import Config

if __name__ == "__main__":
    augment_dataset()
    train_and_evaluate()
    train_company_model()
    required = [Config.PIPELINE_PATH, Config.MODEL_PATH, Config.COMPANY_MODEL_PATH, Config.COMPANY_ENCODER_PATH]
    missing = [path for path in required if not Path(path).is_file()]
    if missing:
        raise SystemExit("Vercel model build did not produce required artifacts: " + ", ".join(missing))
