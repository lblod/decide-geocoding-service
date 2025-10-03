import spacy
import os

class SpacyNERAnalyzer:
    def __init__(self, model_path, labels=None):
        self.model_path = model_path
        self.labels = set(labels) if labels else None
        self.nlp = None
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            print(f"❌ Model not found at {self.model_path}")
            return
        try:
            self.nlp = spacy.load(self.model_path)
            print(f"✅ Loaded model: {self.nlp.meta.get('name', 'Unknown')} "
                  f"(v{self.nlp.meta.get('version', 'Unknown')})")
            if self.nlp.has_pipe("ner"):
                model_labels = self.nlp.get_pipe('ner').labels
                print(f"Model labels: {model_labels}")
                if self.labels:
                    print(f"Filtering for labels: {sorted(self.labels)}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.nlp = None

    def extract_entities(self, text):
        if not self.nlp:
            return {"error": "Model not loaded"}
        if not text.strip():
            return {"entities": [], "text": text}
        try:
            return self.nlp(text)
        except Exception as e:
            return {"error": f"Processing error: {e}", "text": text}


    def get_model_info(self):
        if not self.nlp:
            return {"error": "Model not loaded"}
        info = {
            "path": self.model_path,
            "name": self.nlp.meta.get('name', 'Unknown'),
            "version": self.nlp.meta.get('version', 'Unknown'),
            "lang": self.nlp.meta.get('lang', 'Unknown'),
            "pipeline": list(self.nlp.pipe_names),
        }
        if self.nlp.has_pipe("ner"):
            info["ner_labels"] = list(self.nlp.get_pipe("ner").labels)
        if self.labels:
            info["filter_labels"] = sorted(self.labels)
        return info

