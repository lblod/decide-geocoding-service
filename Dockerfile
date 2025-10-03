FROM semtech/mu-python-template:2.0.0-beta.3
LABEL maintainer="ward@ml2grow.com"

RUN hf download svercoutere/RoBERTa-NER-BE-Loc
ENV NER_MODEL_PATH=/root/.cache/huggingface/hub/models--svercoutere--RoBERTa-NER-BE-Loc/snapshots/423e85a3f6be1511335e9a46f4a120af046dcda5