import contextlib
import logging
import os
import json
from abc import ABC, abstractmethod

from uuid import uuid4
from string import Template
from helpers import query
from escape_helpers import sparql_escape_uri

from .helper_functions import clean_string, get_start_end_offsets, process_text, geocode_detectable, get_street_uri
from .spacy_ner_analyzer import SpacyNERAnalyzer
from .nominatim_geocoder import NominatimGeocoder
from .annotation import GeoAnnotation


class Task(ABC):

    def __init__(self, task_uri: str):
        super().__init__()
        self.task_uri = task_uri
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_uri(cls, task_uri: str):
        q = Template("""
            PREFIX adms: <http://www.w3.org/ns/adms#>
            PREFIX task: <http://lblod.data.gift/vocabularies/tasks/>
            
            SELECT ?task ?taskType WHERE {
              ?task task:operation ?taskType .
              FILTER(?task = $uri)
            }
        """).substitute(uri=sparql_escape_uri(task_uri))
        for b in query(q).get('results').get('bindings'):
            for candidate_cls in cls.__subclasses__():
                if candidate_cls.__task_type__ == b['taskType']['value']:
                    return candidate_cls(task_uri)
            raise RuntimeError("Unknown task type {0}".format(b['taskType']['value']))
        raise RuntimeError("Task with uri {0} not found").format(task_uri)

    def change_state(self, old_state: str, new_state: str, results_container_uri: str = "") -> None:
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
                                                 task=sparql_escape_uri(self.task_uri),
                                                 results_container_line=results_container_line)

        query(query_string)

    @contextlib.contextmanager
    def run(self):
        self.change_state("scheduled", "busy")
        yield
        self.change_state("busy", "success")

    def execute(self):
        with self.run():
            self.process()

    @abstractmethod
    def process(self):
        pass


class DecisionTask(Task, ABC):
    def __init__(self, task_uri: str):
        super().__init__(task_uri)

        q = f"""
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT ?source WHERE {{
          <{task_uri}> dct:source ?source .
        }}
        """
        r = query(q)
        self.source = r["results"]["bindings"][0]["source"]["value"]

    def fetch_data(self) -> str:
        query_string = f"""
        SELECT ?title ?description ?decision_basis WHERE {{
        BIND(<{self.source}> AS ?s)
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


class EntityExtractionTask(DecisionTask):

    __task_type__ = "http://lblod.data.gift/id/jobs/concept/TaskOperation/entity-extracting"

    ner_analyzer = SpacyNERAnalyzer(model_path=os.getenv("NER_MODEL_PATH"), labels=json.loads(os.getenv("NER_LABELS")))
    geocoder = NominatimGeocoder(base_url=os.getenv("NOMINATIM_BASE_URL"), rate_limit=0.5)

    def apply_geo_entities(self, task_data: str):
        default_city = "Gent"

        cleaned_text = clean_string(task_data)
        detectables, _, doc = process_text(cleaned_text, self.__class__.ner_analyzer, default_city)

        if hasattr(doc, 'error'):
            self.logger.error(f"Error: {doc['error']}")
        else:
            # Geocoding Results
            if detectables:
                self.logger.info("Geocoding Results")

                for geo_entity in ["streets", "addresses"]:
                    if geo_entity in detectables:
                        for detectable in detectables[geo_entity]:
                            result = geocode_detectable(detectable, self.__class__.geocoder, default_city)

                            if result["success"]:
                                offsets = get_start_end_offsets(task_data, detectable["name"])
                                start_offset = offsets[0][0]
                                end_offset = offsets[0][1]
                                annotation = GeoAnnotation(
                                    result.get("geojson", {}),
                                    self.task_uri,
                                    uuid4(),
                                    sparql_escape_uri("http://example.org/{0}".format(uuid4())),
                                    start_offset,
                                    end_offset,
                                    sparql_escape_uri("http://example.org/entity-extraction"),
                                    sparql_escape_uri("https://data.vlaanderen.be/ns/lblod#AIComponent>")
                                )
                                annotation.add_to_triplestore()
                            self.logger.info(result)
            else:
                self.logger.info("No location entities detected.")

    def process(self):
        task_data = self.fetch_data(self.source)
        self.logger.info(task_data)

        self.apply_geo_entities(task_data)



