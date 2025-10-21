import os
import logging
import spacy


class SpacyNERAnalyzer:
    """Named Entity Recognition analyzer using spaCy models."""
    
    def __init__(self, model_path, labels=None):
        self.model_path = model_path
        self.labels = set(labels) if labels else None
        self.nlp = None

        # Configure logging
        self.logger = logging.getLogger(__name__)

        self.load_model()
        

    def load_model(self):
        """Load the spaCy NER model from the specified path."""
        if not os.path.exists(self.model_path):
            self.logger.error(f"Model not found at {self.model_path}")
            return
        try:
            self.nlp = spacy.load(self.model_path)
            self.logger.info(
                f"Loaded model: {self.nlp.meta.get('name', 'Unknown')} (v{self.nlp.meta.get('version', 'Unknown')})")
            if self.nlp.has_pipe("ner"):
                model_labels = self.nlp.get_pipe("ner").labels
                self.logger.info(f"Model labels: {model_labels}")
                if self.labels:
                    self.logger.info(
                        f"Filtering for labels: {sorted(self.labels)}")
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self.nlp = None

    def extract_entities(self, text):
        """Extract named entities from text and return spaCy Doc object."""
        if not self.nlp:
            return {"error": "Model not loaded"}
        if not text.strip():
            return {"entities": [], "text": text}
        try:
            return self.nlp(text)
        except Exception as e:
            return {"error": f"Processing error: {e}", "text": text}
