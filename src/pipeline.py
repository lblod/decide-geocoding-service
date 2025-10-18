import logging
import pandas as pd
from uuid import uuid4
import time

from .jobs_client import fetch_data_from_task, fetch_data_from_decision, change_task_state
from .helper_functions import clean_string, get_start_end_offsets, process_text, geocode_detectable, get_street_uri
from .linked_data_writer import insert_annotation
from .spacy_ner_analyzer import SpacyNERAnalyzer
from .nominatim_geocoder import NominatimGeocoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pipeline(task_uri: str, ner_analyzer: SpacyNERAnalyzer, geocoder: NominatimGeocoder) -> None:
    change_task_state(task_uri, old_state="scheduled", new_state="busy")

    # TODO: adapt code for actual implementation of fetch_data_from_task
    source_decision = fetch_data_from_task(task_uri)
    task_data = fetch_data_from_decision(source_decision)

    default_city = "Gent"

    logger.info(task_data)

    cleaned_text = clean_string(task_data)
    detectables, _, doc = process_text(cleaned_text, ner_analyzer, default_city)

    if hasattr(doc, 'error'):
        logger.error(f"Error: {doc['error']}")
    else:
        # Geocoding Results
        if detectables:
            logger.info("Geocoding Results")

            for geo_entity in ["streets", "addresses"]:
                if geo_entity in detectables:
                    for detectable in detectables[geo_entity]:
                        result = geocode_detectable(detectable, geocoder, default_city)

                        if result["success"]:
                            osm_link = result.get("osm_url", "")

                            if geo_entity == "streets":
                                straat_object_id = get_street_uri(detectable["city"], detectable["name"])

                                # TODO: adapt and move example URIs
                                graph_uri = "http://mu.semte.ch/graphs/annotations"
                                annotation_uri = f"http://example.org/id/annotation/{uuid4()}"
                                body_uri = f"http://example.org/id/body/{uuid4()}"
                                target_uri = f"http://example.org/id/target/{uuid4()}"
                                selector_uri = f"http://example.org/id/selector/{uuid4()}"
                                geom_uri = f"http://data.lblod.info/id/geometries/{uuid4()}"

                                offsets = get_start_end_offsets(task_data, detectable["name"])

                                source_doc = source_decision
                                start_offset = offsets[0][0]
                                end_offset = offsets[0][1]
                                confidence = 0.87
                                label = detectable["name"]
                                geojson = result.get("geojson", {})
                                geometry = ", ".join(
                                    f"{x} {y}" for x, y in geojson["coordinates"])

                                insert_annotation(geo_entity, body_uri,
                                                  label, geom_uri,
                                                  geometry, straat_object_id,
                                                  graph_uri, annotation_uri,
                                                  confidence, target_uri,
                                                  source_doc, selector_uri,
                                                  start_offset, end_offset)

                        logger.info(result)
        else:
            logger.info("No location entities detected.")

        change_task_state(task_uri, old_state="busy", new_state="success")
