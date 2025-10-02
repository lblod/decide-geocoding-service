import os
import json
from src.pipeline import run_pipeline
from src.spacy_ner_analyzer import SpacyNERAnalyzer
from src.nominatim_geocoder import NominatimGeocoder

from flask import jsonify, copy_current_request_context
import threading


# TODO: DOWNLOAD NER MODEL?

ner_analyzer = SpacyNERAnalyzer(model_path=os.getenv("NER_MODEL_PATH"),
                                labels=json.loads(os.getenv("NER_LABELS")))
geocoder = NominatimGeocoder(base_url=os.getenv("NOMINATIM_BASE_URL"),
                             rate_limit=0.5)


@app.route("/notify-change")
def notify_change():
    @copy_current_request_context
    def run_pipeline_with_context():
        run_pipeline(ner_analyzer, geocoder)

    threading.Thread(target=run_pipeline_with_context, daemon=True).start()
    return jsonify({"status": "accepted", "message": "Processing started"}), 202
