import pandas as pd
import random
import os
import sys

# Add parent to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

SYNONYMS = {
    "strike": ["walkout", "stoppage", "protest"],
    "delaying": ["stalling", "slowing", "holding up"],
    "attack": ["breach", "hack", "incident"],
    "conflict": ["tension", "dispute", "hostility"],
    "major": ["significant", "severe", "large-scale"],
    "minor": ["small", "slight", "insignificant"],
    "shortage": ["lack", "scarcity", "deficit"],
    "disrupting": ["interrupting", "disturbing", "halting"]
}

def paraphrase(text: str) -> str:
    """
    Simple word substitution for augmentation.
    Antigravity Rule: Wrap in try/except, return original on failure.
    """
    try:
        words = text.split()
        new_words = []
        for word in words:
            clean_word = word.lower().strip(".,!?")
            if clean_word in SYNONYMS and random.random() > 0.3:
                sub = random.choice(SYNONYMS[clean_word])
                # Preserve capitalization
                if word[0].isupper():
                    sub = sub.capitalize()
                new_words.append(sub)
            else:
                new_words.append(word)
        return " ".join(new_words)
    except Exception as e:
        print(f"Error in paraphrase: {e}")
        return text

def augment_dataset():
    """
    Read dataset.csv, paraphrase each sample 2x, append, save to augmented_dataset.csv.
    """
    print(f"Loading dataset from: {Config.DATASET_PATH}")
    try:
        if not os.path.exists(Config.DATASET_PATH):
            print("Dataset not found!")
            return
            
        df = pd.read_csv(Config.DATASET_PATH)
        augmented_rows = []
        
        for _, row in df.iterrows():
            # Keep original
            augmented_rows.append({"text": row["text"], "label": row["label"]})
            # Paraphrase 1
            augmented_rows.append({"text": paraphrase(row["text"]), "label": row["label"]})
            # Paraphrase 2
            augmented_rows.append({"text": paraphrase(row["text"]), "label": row["label"]})
            
        aug_df = pd.DataFrame(augmented_rows)
        # Shuffle
        aug_df = aug_df.sample(frac=1).reset_index(drop=True)
        
        aug_df.to_csv(Config.AUGMENTED_DATASET_PATH, index=False)
        print(f"Augmented dataset saved to {Config.AUGMENTED_DATASET_PATH} with {len(aug_df)} rows.")
    except Exception as e:
        print(f"Error augmenting dataset: {e}")

if __name__ == "__main__":
    augment_dataset()
