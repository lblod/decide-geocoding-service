import logging
from helpers import query

logger = logging.getLogger(__name__)

# TODO: adapt code for actual implementation of fetch_open_jobs
def fetch_open_jobs() -> list:
    return ["https://data.gent.be/id/besluiten/21.0903.3099.6301",
            "https://data.gent.be/id/besluiten/21.0906.2448.3753"
            ]


# TODO: adapt code for actual implementation of fetch_data_from_job
def fetch_data_from_job(job_id: int) -> str:
    query_string = f"""
    SELECT ?title ?description ?decision_basis WHERE {{
    BIND(<{job_id}> AS ?s)
    OPTIONAL {{ ?s <http://data.europa.eu/eli/ontology#title> ?title }}
    OPTIONAL {{ ?s <http://data.europa.eu/eli/ontology#description> ?description }}
    OPTIONAL {{ ?s <http://data.europa.eu/eli/eli-dl#decision_basis> ?decision_basis }}
    }}
    """

    query_result = query(query_string)

    title = query_result["results"]["bindings"][0]["title"]["value"]
    description = query_result["results"]["bindings"][0]["description"]["value"]
    decision_basis = query_result["results"]["bindings"][0]["decision_basis"]["value"]

    return "\n".join([title, description, decision_basis])
