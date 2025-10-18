import logging
from string import Template
from helpers import query
from escape_helpers import sparql_escape_uri

logger = logging.getLogger(__name__)

# TODO: adapt code for actual implementation of fetch_data_from_task
def fetch_data_from_task(task_uri: str) -> str:
    q = f"""
    PREFIX dct: <http://purl.org/dc/terms/>

    SELECT ?source WHERE {{
      <{task_uri}> dct:source ?source .
    }}
    """
    r = query(q)
    try:
        return r["results"]["bindings"][0]["source"]["value"]
    except Exception:
        return None


def fetch_scheduled_tasks() -> list:
    q = """
    PREFIX adms: <http://www.w3.org/ns/adms#>
    PREFIX task: <http://lblod.data.gift/vocabularies/tasks/>
    SELECT ?task WHERE {
      ?task adms:status <http://redpencil.data.gift/id/concept/JobStatus/scheduled> ;
            task:operation <http://lblod.data.gift/id/jobs/concept/TaskOperation/entity-extracting> .
    }
    """
    r = query(q)
    try:
        tasks = [b["task"]["value"] for b in r["results"]["bindings"]]
    except:
        tasks = []

    return tasks


def change_task_state(task_uri: str, old_state: str, new_state: str, results_container_uri: str = "") -> None:
    query_template = Template("""
        PREFIX task: <http://redpencil.data.gift/vocabularies/tasks/>
        PREFIX adms: <http://www.w3.org/ns/adms#>

        DELETE {
        GRAPH <http://mu.semte.ch/graphs/jobs> {
            ?task adms:status ?oldStatus .
        }
        }
        INSERT {
        GRAPH <http://mu.semte.ch/graphs/jobs> {
            ?task
            $results_container_line
            adms:status <http://redpencil.data.gift/id/concept/JobStatus/$new_state> .
            
        }
        }
        WHERE {
        GRAPH <http://mu.semte.ch/graphs/jobs> {
            BIND($task AS ?task)
            BIND(<http://redpencil.data.gift/id/concept/JobStatus/$old_state> AS ?oldStatus)
            OPTIONAL { ?task adms:status ?oldStatus . }
        }
        }
        """)

    results_container_line = ""
    if results_container_uri:
        results_container_line = f"task:resultsContainer <{results_container_uri}> ;"

    query_string = query_template.substitute(new_state=new_state,
                                             old_state=old_state,
                                             task=sparql_escape_uri(task_uri),
                                             results_container_line=results_container_line)

    query(query_string)


def fetch_data_from_decision(decision_uri: str) -> str:
    query_string = f"""
    SELECT ?title ?description ?decision_basis WHERE {{
    BIND(<{decision_uri}> AS ?s)
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
