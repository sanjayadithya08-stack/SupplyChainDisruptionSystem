import pandas as pd
import json
import joblib
import os
import sys
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from utils.text_preprocessing import clean_text

def train_and_evaluate():
    print(f"Loading augmented dataset from: {Config.AUGMENTED_DATASET_PATH}")
    try:
        if not os.path.exists(Config.AUGMENTED_DATASET_PATH):
            raise FileNotFoundError(f"Dataset not found at {Config.AUGMENTED_DATASET_PATH}. Run augment_data.py first.")
            
        df = pd.read_csv(Config.AUGMENTED_DATASET_PATH)
        
        # Preprocessing
        df['cleaned_text'] = df['text'].apply(clean_text)
        
        X_train, X_test, y_train, y_test = train_test_split(
            df['cleaned_text'], df['label'], test_size=0.2, random_state=42, stratify=df['label']
        )
        
        models = {
            "Logistic Regression": LogisticRegression(max_iter=1000, class_weight='balanced'),
            "Random Forest": RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42),
            "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42)
        }
        
        best_model_name = None
        best_f1 = -1
        best_pipeline = None
        report_data = {}
        
        for name, model in models.items():
            print(f"Training {name}...")
            pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1,2))),
                ('clf', model)
            ])
            
            pipeline.fit(X_train, y_train)
            preds = pipeline.predict(X_test)
            
            f1 = f1_score(y_test, preds, average='macro')
            print(f"{name} Macro F1: {f1:.4f}")
            
            report_data[name] = {
                "macro_f1": f1,
                "report": classification_report(y_test, preds, output_dict=True, zero_division=0)
            }
            
            if f1 > best_f1:
                best_f1 = f1
                best_model_name = name
                best_pipeline = pipeline
                
        print(f"\nBest Model: {best_model_name} (Macro F1: {best_f1:.4f})")
        
        os.makedirs(Config.ARTEFACTS_DIR, exist_ok=True)
        joblib.dump(best_pipeline, Config.PIPELINE_PATH)
        joblib.dump(best_pipeline.named_steps['clf'], Config.MODEL_PATH)
        
        final_report = {
            "best_model": best_model_name,
            "best_macro_f1": best_f1,
            "all_models": report_data
        }
        with open(Config.TRAINING_REPORT_PATH, "w") as f:
            json.dump(final_report, f, indent=4)
        
    except Exception as e:
        print(f"CRITICAL ERROR in training: {e}")
        os.makedirs(Config.ARTEFACTS_DIR, exist_ok=True)
        with open(Config.TRAINING_REPORT_PATH, "w") as f:
            json.dump({"error": str(e), "status": "failed"}, f)

if __name__ == "__main__":
    train_and_evaluate()