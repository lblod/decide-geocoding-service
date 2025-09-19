 # Geocoding Service: Text to Geolocation
 
This repo provides (the start of) a geocoding service that processes text to extract and resolve geolocations. It combines natural language processing (NLP) for location extraction with geocoding to map locations to geographic coordinates.

Location extraction is based on the RobBERT NER model and currently only suitable for Ghent. The service uses spaCy for NLP processing.
 
 ## Features
 - Extracts location entities from text using an NLP model
 - Resolves extracted locations to latitude/longitude using Nominatim
 - Demo app included (see `demo/streamlit_location_app.py`)
 
 ## Model
The location extraction model used in this project can be found on HuggingFace:

**svercoutere/RoBERTa-NER-BE-Loc**

You need to download the model from HuggingFace and pass its location to the spaCy model loader.
 
 ## Requirements
 - Python 3.8+
 - SpaCy (model was trained with spaCy v3.6.1, tested with version 3.7.2)
 - [Nominatim](https://nominatim.org/) geocoding service (Docker)

- Download the RobBERT NER model from HuggingFace and provide its path to spaCy.
 
 ### Running Nominatim with Docker
You need a running Nominatim instance for geocoding. The example below uses Belgium, but you can specify other regions. See https://download.geofabrik.de for available locations. Start it using:
 
 ```powershell
 docker run -it -e PBF_URL=https://download.geofabrik.de/europe/belgium-latest.osm.pbf -p 8080:8080 --name nominatim mediagis/nominatim:5.1
 ```
 
 ## Usage
 See the demo app in `demo/streamlit_location_app.py` for an example of how to use the service.
 
 ## Structure
 - `library/` - Core modules for location extraction and geocoding
 - `demo/` - Example Streamlit app
 
