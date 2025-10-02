 # Geocoding Service: Text to Geolocation
 
This repo provides (the start of) a geocoding service that processes text to extract and resolve geolocations. It combines natural language processing (NLP) for location extraction with geocoding to map locations to geographic coordinates.

Location extraction is based on the RobBERT NER model and currently only suitable for Ghent. The service uses spaCy for NLP processing.
 
 ## Features
 - Extracts location entities from text using an NLP model
 - Resolves extracted locations to latitude/longitude using Nominatim
 - Load data from local triple store
 
 ## Model
The location extraction model used in this project can be found on HuggingFace:

[svercoutere/RoBERTa-NER-BE-Loc](https://huggingface.co/svercoutere/RoBERTa-NER-BE-Loc)

You need to download the model from [HuggingFace](https://huggingface.co/svercoutere/RoBERTa-NER-BE-Loc) and pass its location to the spaCy model loader.
 
 ## Requirements
 - Python 3.8+
 - SpaCy (model was trained with spaCy v3.6.1, tested with version 3.7.2)
 - Download the RobBERT NER model from [HuggingFace](https://huggingface.co/svercoutere/RoBERTa-NER-BE-Loc) and provide its path to spaCy.
 - Run [app-decide](https://github.com/lblod/app-decide) locally in another Docker container, and place a triple store dump in the /data/db folder of that container.
 - Run the [Nominatim](https://nominatim.org/) geocoding service (Docker, see instruction below on how to run it)
 - Modify the docker-compose.yaml file and fill in the MU_SPARQL_ENDPOINT of the local triple store (hosted in the app-decide Docker container), the NOMINATIM_BASE_URL of the geocoding service and NER_MODEL_PATH, the folder path to the NER model.

 ### Running Nominatim with Docker
You need a running Nominatim instance for geocoding. The example below uses Belgium, but you can specify other regions. See https://download.geofabrik.de for available locations. Start it using:
 
 ```powershell
 docker run -it -e PBF_URL=https://download.geofabrik.de/europe/belgium-latest.osm.pbf -p 8080:8080 --name nominatim mediagis/nominatim:5.1
 ```
 
 ## Usage 
 Run
 ```
docker compose up
 ```
and send a request to the /notify-change endpoint on the port as configured in the docker-compose.yaml file.

## Original demo code
The original demo code can be found in the [demo](/demo) folder.
