import os
import json
from src.pipeline import run_pipeline
from src.spacy_ner_analyzer import SpacyNERAnalyzer
from src.nominatim_geocoder import NominatimGeocoder

from flask import jsonify, copy_current_request_context, request
import threading


ner_analyzer = SpacyNERAnalyzer(model_path=os.getenv("NER_MODEL_PATH"),
                                labels=json.loads(os.getenv("NER_LABELS")))
geocoder = NominatimGeocoder(base_url=os.getenv("NOMINATIM_BASE_URL"),
                             rate_limit=0.5)


@app.post("/delta")
def delta():
    data = request.get_json(silent=True) or []

    for patch in data:
        for ins in patch.get("inserts", []):
            if ins != []:
                subj = ins.get("subject", {}).get("value")
                pred = ins.get("predicate", {}).get("value")
                obj = ins.get("object", {}).get("value")

                if pred != os.getenv("EXPECTED_TASK_PREDICATE") or obj != os.getenv("EXPECTED_TASK_OBJECT"):
                    return jsonify({
                        "error": "Unexpected predicate/object",
                        "got": {"predicate": pred, "object": obj},
                        "expected": {"predicate": os.getenv("EXPECTED_TASK_PREDICATE"), "object": os.getenv("EXPECTED_TASK_OBJECT")}
                    }), 400

                else:
                    @copy_current_request_context
                    def run_pipeline_with_context():
                        run_pipeline(subj, ner_analyzer, geocoder)

                    threading.Thread(
                        target=run_pipeline_with_context, daemon=True).start()
                    return jsonify({"status": "accepted", "message": "Processing started"}), 202
