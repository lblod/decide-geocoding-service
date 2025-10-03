 # Geocoding Service: Text to Geolocation
 
This repo provides a geocoding service that processes text to extract and resolve geolocations. It combines natural language processing (NLP) for location extraction with geocoding to map locations to geographic coordinates.

Location extraction is based on the RobBERT NER model and currently only suitable for Ghent. The service uses spaCy for NLP processing.
 
 ## Features
 - Extracts location entities from text using an NLP model
 - Resolves extracted locations to latitude/longitude using Nominatim
 - Load data from local triple store
 
 ## Requirements
 - Modify the docker-compose.yaml file and fill in the MU_SPARQL_ENDPOINT of the local triple store (hosted in the app-decide Docker container). This may require modifying the network name as well to match the docker network app-decide is running in.

 ### Running Nominatim with Docker
Running Nominatim has been included in the included docker compose file. Note that on the first start, Nominatim might be busy for an hour to build its
database. As a volume is mounted for the database, this setup happens once.
 
 ## Usage 
 Run
 ```
docker compose up
 ```
and send a request to the /notify-change endpoint on the port as configured in the docker-compose.yaml file.

## Original demo code
The original demo code can be found in the [demo](/demo) folder.
