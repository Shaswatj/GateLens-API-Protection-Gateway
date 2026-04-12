"""ML-based attack detector using TF-IDF + LogisticRegression"""

import pickle
import os
import warnings

warnings.filterwarnings('ignore')

# Make sklearn optional - graceful fallback if not installed
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError as e:
    print(f"[ML] WARNING: scikit-learn not installed. Running rule-based detection only.")
    print(f"[ML] Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False

ML_DIR = os.path.join(os.path.dirname(__file__))
MODEL_PATH = os.path.join(ML_DIR, 'attack_model.pkl')


class AttackDetector:
    """Simple ML-based attack detector with graceful fallback"""
    
    def __init__(self):
        self.pipeline = None
        self.loaded = False
        self.enabled = SKLEARN_AVAILABLE
        
        if self.enabled:
            self._load_or_train()
        else:
            print("[ML] ML detection disabled (scikit-learn not available)")
    
    def _train_model(self):
        """Train model from scratch using training data"""
        if not SKLEARN_AVAILABLE:
            return False
        
        try:
            from ml.training_data import TRAINING_DATA
            
            texts = [item['input'] for item in TRAINING_DATA]
            labels = [item['label'] for item in TRAINING_DATA]
            
            # Simple pipeline: TF-IDF → Logistic Regression
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    lowercase=True,
                    stop_words='english',
                    max_features=100,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=1.0
                )),
                ('classifier', LogisticRegression(
                    max_iter=200,
                    random_state=42,
                    solver='lbfgs'
                    # Note: multi_class is removed - uses default (auto)
                ))
            ])
            
            # Train
            self.pipeline.fit(texts, labels)
            
            # Save
            os.makedirs(ML_DIR, exist_ok=True)
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.pipeline, f)
            
            self.loaded = True
            print(f"[ML] Model trained and saved")
            return True
            
        except Exception as e:
            print(f"[ML] ERROR during training: {e}")
            self.loaded = False
            return False
    
    def _load_or_train(self):
        """Load existing model or train new one"""
        if not SKLEARN_AVAILABLE:
            return
        
        # Try to load existing model
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    self.pipeline = pickle.load(f)
                self.loaded = True
                print(f"[ML] Model loaded from disk")
                return
            except Exception as e:
                print(f"[ML] ERROR loading model: {e}. Training new model...")
        
        # Train new model if load failed or file doesn't exist
        self._train_model()
    
    def predict(self, text: str) -> dict:
        """
        Predict if input is attack or normal.
        
        Safe fallback: returns normal if ML disabled or fails
        
        Returns:
            {
              'label': 'xss' | 'sqli' | 'normal',
              'confidence': 0.0-1.0,
              'is_attack': bool
            }
        """
        # Fallback if ML not available or not trained
        if not self.enabled or not self.pipeline or not self.loaded:
            return {'label': 'normal', 'confidence': 0.0, 'is_attack': False}
        
        try:
            # Get prediction and confidence
            label = self.pipeline.predict([text])[0]
            confidence = max(self.pipeline.predict_proba([text])[0])
            is_attack = label in ['xss', 'sqli']
            
            return {
                'label': label,
                'confidence': round(float(confidence), 2),
                'is_attack': is_attack
            }
        except Exception as e:
            print(f"[ML] ERROR in prediction: {e}")
            # Fallback to normal (rule-based detection will catch attacks)
            return {'label': 'normal', 'confidence': 0.0, 'is_attack': False}


# Global instance - safe to create even if sklearn not available
detector = AttackDetector()

