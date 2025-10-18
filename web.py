import os
import json

from src.pipeline import run_pipeline
from src.spacy_ner_analyzer import SpacyNERAnalyzer
from src.nominatim_geocoder import NominatimGeocoder

from fastapi import APIRouter, Request
from pydantic import BaseModel, Literal, BackgroundTasks


ner_analyzer = SpacyNERAnalyzer(model_path=os.getenv("NER_MODEL_PATH"),
                                labels=json.loads(os.getenv("NER_LABELS")))
geocoder = NominatimGeocoder(base_url=os.getenv("NOMINATIM_BASE_URL"),
                             rate_limit=0.5)

router = APIRouter()


class Value(BaseModel):
    type: str
    value: str


class ExpectedTaskPredicateValue(BaseModel):
    value: Literal[os.getenv("EXPECTED_TASK_PREDICATE")]


class ExpectedTaskObjectValue(BaseModel):
    value: Literal[os.getenv("EXPECTED_TASK_OBJECT")]


class Triplet(BaseModel):
    subject: Value
    predicate: Value
    object: Value
    graph: Value


class InsertTriplet(Triplet):
    predicate: ExpectedTaskPredicateValue
    object: ExpectedTaskObjectValue


class DeltaNotification(BaseModel):
    inserts: list[InsertTriplet]
    deletes: list[Triplet]


class DataModel(BaseModel):
    __root__: list[DeltaNotification] = []


class NotificationResponse(BaseModel):
    status: str
    message: str


@router.post("/delta", status_code=202)
def delta(request: Request, background_tasks: BackgroundTasks) -> NotificationResponse:
    data = DataModel(__root__=request.json())

    for patch in data.__root__:
        for ins in patch.inserts:
            background_tasks.add_task(run_pipeline, ins.subject.value, ner_analyzer, geocoder)


    return NotificationResponse(status="accepted", message="Processing started")
