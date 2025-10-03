import logging
import pandas as pd

from .jobs_client import fetch_data_from_job, fetch_open_jobs
from .helper_functions import clean_string, process_text, geocode_detectable
from .linked_data_writer import store_linked_data
from .spacy_ner_analyzer import SpacyNERAnalyzer
from .nominatim_geocoder import NominatimGeocoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pipeline(ner_analyzer: SpacyNERAnalyzer, geocoder: NominatimGeocoder) -> None:
    # TODO: adapt code for actual implementation of fetch_open_jobs
    jobs = fetch_open_jobs()

    for job in jobs:
        # TODO: adapt code for actual implementation of fetch_data_from_job
        job_data = fetch_data_from_job(job)

        default_city = "Gent"

        logger.info(job_data)

        cleaned_text = clean_string(job_data)
        detectables, _, doc = process_text(
            cleaned_text, ner_analyzer, default_city)

        if hasattr(doc, 'error'):
            logger.error(f"Error: {doc['error']}")
        else:
            # Geocoding Results
            if detectables:
                logger.info("Geocoding Results")

                # Geocode all detectables
                geocoded_results = []

                for i, detectable in enumerate(detectables):
                    result = geocode_detectable(
                        detectable, geocoder, default_city)
                    geocoded_results.append(result)

                # Create simple results table
                results_data = []
                for result in geocoded_results:
                    if result["success"]:
                        osm_link = result.get("osm_url", "")
                        results_data.append({
                            "Entity": result["detectable"]["name"],
                            "Type": result["detectable"]["type"],
                            "Query": result["query"],
                            "Found Location": result["display_name"],
                            "Coordinates": f"{result['lat']:.6f}, {result['lon']:.6f}",
                            "OpenStreetMap": osm_link if osm_link else ""
                        })
                    else:
                        results_data.append({
                            "Entity": result["detectable"]["name"],
                            "Type": result["detectable"]["type"],
                            "Query": result["query"],
                            "Found Location": "Not found",
                            "Coordinates": "",
                            "OpenStreetMap": ""
                        })

                if results_data:
                    df = pd.DataFrame(results_data)

                    store_linked_data(df)

                    # TODO: set job to done?

                    for result in results_data:
                        logger.info(result)
            else:
                logger.info("No location entities detected.")
