FROM semtech/mu-python-template:feature-fastapi
LABEL maintainer="ward@ml2grow.com"

RUN uv run hf download svercoutere/RoBERTa-NER-BE-Loc
ENV NER_MODEL_PATH=/root/.cache/huggingface/hub/models--svercoutere--RoBERTa-NER-BE-Loc/snapshots/423e85a3f6be1511335e9a46f4a120af046dcda5

ENV EXPECTED_TASK_PREDICATE=http://www.w3.org/ns/adms#status
ENV EXPECTED_TASK_OBJECT=http://redpencil.data.gift/id/concept/JobStatus/scheduled
ENV BASE_REGISTRY_URI=https://api.basisregisters.vlaanderen.be