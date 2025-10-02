import streamlit as st
import spacy
from spacy import displacy
import pandas as pd
import folium
from folium import Map, Marker, Popup
import requests
import time
import logging
import re
import unicodedata
from typing import List, Dict, Any, Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Location Extraction & Geocoding App",
    page_icon="🗺️",
    layout="wide"
)

# Add custom CSS for better styling
st.markdown("""
<style>
.entity-highlight {
    padding: 0.25rem 0.5rem;
    margin: 0.1rem;
    border-radius: 0.25rem;
    font-weight: bold;
}
.entity-STREET { background-color: #fef3c7; color: #92400e; }
.entity-CITY { background-color: #dbeafe; color: #1e40af; }
.entity-HOUSENUMBERS { background-color: #fce7f3; color: #be185d; }
.entity-ROAD { background-color: #d1fae5; color: #065f46; }
.entity-INTERSECTION { background-color: #fef3c7; color: #92400e; }
.entity-DOMAIN { background-color: #e0e7ff; color: #3730a3; }
.entity-POSTCODE { background-color: #fecaca; color: #991b1b; }
.entity-PROVINCE { background-color: #f3e8ff; color: #6b21a8; }
.annotation-box {
    border: 1px solid #ddd;
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f8f9fa;
    color: #333;
}
</style>
""", unsafe_allow_html=True)

# SpaCy NER Analyzer Class (from your notebook)
class SpacyNERAnalyzer:
    def __init__(self, model_path, labels=None):
        self.model_path = model_path
        self.labels = set(labels) if labels else None
        self.nlp = None
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            st.error(f"❌ Model not found at {self.model_path}")
            return
        try:
            self.nlp = spacy.load(self.model_path)
            st.success(f"✅ Loaded model: {self.nlp.meta.get('name', 'Unknown')} (v{self.nlp.meta.get('version', 'Unknown')})")
            if self.nlp.has_pipe("ner"):
                model_labels = self.nlp.get_pipe('ner').labels
                st.info(f"Model labels: {model_labels}")
                if self.labels:
                    st.info(f"Filtering for labels: {sorted(self.labels)}")
        except Exception as e:
            st.error(f"❌ Error loading model: {e}")
            self.nlp = None

    def extract_entities(self, text):
        if not self.nlp:
            return {"error": "Model not loaded"}
        if not text.strip():
            return {"entities": [], "text": text}
        try:
            return self.nlp(text)
        except Exception as e:
            return {"error": f"Processing error: {e}", "text": text}

# Nominatim Geocoder Class (from your notebook)
class NominatimGeocoder:
    def __init__(self, base_url: str = "http://localhost:8080", rate_limit: float = 1.0, timeout: float = 10.0):
        self.base_url = base_url.rstrip('/')
        self.rate_limit = max(0.0, rate_limit)
        self.timeout = timeout
        self._last = 0.0
        self._sess = requests.Session()

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = self.rate_limit - (now - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def search(self, query: str, city: str = "Gent", limit: int = 1, country: str = "BE") -> Optional[Dict[str, Any]]:
        if not query or not query.strip():
            return None

        self._throttle()
        full_query = f"{query}, {city}" if city else query
        params = {
            "q": full_query,
            "format": "json",
            "limit": limit,
            "countrycodes": country,
            "addressdetails": 1,
            "extratags": 0,
            "namedetails": 0,
        }

        try:
            resp = self._sess.get(f"{self.base_url}/search", params=params, timeout=self.timeout)
            resp.raise_for_status()
            results = resp.json()
            if not results:
                return None
            return self._format(results[0], original_query=query)
        except requests.RequestException as exc:
            logger.warning("Nominatim request failed for %r: %s", query, exc)
            return None
        except ValueError as exc:
            logger.warning("Failed parsing Nominatim JSON for %r: %s", query, exc)
            return None

    def _format(self, r: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        addr = r.get("address", {})
        osm_type = r.get("osm_type")
        osm_id = r.get("osm_id")
        osm_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_type and osm_id else None

        return {
            "query": original_query,
            "display_name": r.get("display_name"),
            "lat": float(r.get("lat", 0.0)),
            "lon": float(r.get("lon", 0.0)),
            "importance": r.get("importance"),
            "place_id": r.get("place_id"),
            "osm_type": osm_type,
            "osm_id": osm_id,
            "osm_url": osm_url,
            "address": {
                "house_number": addr.get("house_number"),
                "road": addr.get("road"),
                "city": addr.get("city") or addr.get("town") or addr.get("village"),
                "postcode": addr.get("postcode"),
                "country": addr.get("country"),
                "country_code": addr.get("country_code"),
            },
            "bbox": r.get("boundingbox"),
            "type": r.get("type"),
            "class": r.get("class"),
        }

# Helper functions (from your notebook)
def clean_string(input_string):
    cleaned_string = input_string.replace('\n', ' ')
    cleaned_string = cleaned_string.strip()
    cleaned_string = re.sub(r'\s+', ' ', cleaned_string)
    cleaned_string = unicodedata.normalize('NFKD', cleaned_string)
    return cleaned_string

def clean_house_number(housenumber):
    # Split the housenumbers based on "," , "en" and "/"
    housenumber = housenumber.replace("  ", " ").replace("tot en met",'t.e.m.').replace("TOT EN MET",'t.e.m.')
    # Remove "huisnummer" and similar terms
    housenumber = re.sub(r'\b(huisnummer|huisnr|nr|nummer)\b', '', housenumber, flags=re.IGNORECASE)
    housenumber = re.sub(r'\s+', ' ', housenumber).strip()  # Clean up extra spaces
    parts = [item.strip() for item in re.split(r',|en', housenumber) if item]
    result_list = []

    for part in parts:
        # Remove leading and trailing whitespace
        part = part.strip()

        # Check if the part contains a range with "-"
        if "-" in part:
            # Split by '-' and convert to get the start and end of the range as strings
            segments = part.split("-")
            if len(segments) == 2:
                start, end = segments
                # Check if the start and end are integers
                if start.strip().isdigit() and end.strip().isdigit():
                    # Convert to integers
                    start = int(start.strip())
                    end = int(end.strip())
                    # check if start and end are smaller than 1000:
                    if start < 1000 and end < 1000 and end-start < 20 and end>start:
                        result_list.extend(map(str, range(start, end + 1)))
                    else:
                        # Add both values to the result list
                        result_list.append(start)
                        result_list.append(end)
                else:
                    result_list.append(start)
                    result_list.append(end)

            else:
                for segment in segments:
                    result_list.append(segment)

        # Check for keywords indicating a range
        elif "tot" in part.lower() or "t.e.m." in part.lower():
            # Split by keywords and convert to integers
            numbers = [num for num in re.split(r'\D+', part) if num]
            # Add all values within the range to the result list
            if len(numbers) == 2:
                start, end = map(int, numbers)
                if "tot" in part.lower():
                    end-=1
                result_list.extend(map(str, range(start, end + 1)))
            else:
                result_list.append(part)
        # Check if the part contains a "/"
        elif "/" in part and "bus" not in part.lower():
            # Split by '/'
            start, end = part.split("/")
            result_list.append(start.strip())
            result_list.append(end.strip())
        else:
            result_list.append(part)
    return result_list

def extract_house_and_bus_number(housenumber):
    bus_number = None
    house_number = None

    if "bus" in housenumber:
        parts = housenumber.split("bus")
        if len(parts) > 1 and parts[1].strip().isdigit():
            bus_number = int(parts[1].strip())
        if parts[0].strip():
            house_number = parts[0].strip()
    else:
        house_number = housenumber.strip()

    if house_number and "/" in house_number:
        parts = house_number.split("/")
        house_number = parts[0].strip()

    return {"housenumber": house_number, "bus": bus_number}

def form_addresses(entities, from_city="Gent"):
    current_address = {"name": None, "house_number": None, "house_numbers": [], "bus": None, "postcode": None, "city": None, "type": "HOUSE", "spacy_entities": []}
    addresses = []
    
    for entity in entities:
        if entity.label_ == "STREET":
            if current_address["name"] and len(current_address["house_numbers"]) > 0:
                addresses.append(current_address)
                current_address = {"name": None, "house_number": None, "house_numbers": [], "bus": None, "postcode": None, "city": None, "type": "HOUSE", "spacy_entities": []}
            current_address["name"] = entity.text
            current_address["type"] = entity.label_
            current_address["spacy_entities"].append(entity)
        elif entity.label_ == "HOUSENUMBERS":
            current_address["house_numbers"] = clean_house_number(entity.text)
            current_address["spacy_entities"].append(entity)
        elif entity.label_ == "POSTCODE":
            current_address["postcode"] = entity.text
            current_address["spacy_entities"].append(entity)
        elif entity.label_ == "CITY":
            current_address["city"] = entity.text
            current_address["spacy_entities"].append(entity)
            if current_address["name"] and len(current_address["house_numbers"]) > 0:
                addresses.append(current_address)
                current_address = {"name": None, "house_number": None, "house_numbers": [], "bus": None, "postcode": None, "city": None, "type": "HOUSE", "spacy_entities": []}

    if current_address["name"] and len(current_address["house_numbers"]) > 0:
        addresses.append(current_address)

    for address in addresses:
        if not address["city"]:
            address["city"] = from_city

    return addresses

def form_locations(entities, from_city="Gent"):
    current_address = {"name": None, "house_number": None, "house_numbers": [], "bus": None, "postcode": None, "city": None, "type": None, "spacy_entities": []}
    addresses = []

    for entity in entities:
        if entity.label_ in ["DOMAIN", "ROAD", "STREET", 'INTERSECTION']:
            if current_address["name"]:
                addresses.append(current_address)
                current_address = {"name": None, "house_number": None, "house_numbers": [], "bus": None, "postcode": None, "city": None, "type": None, "spacy_entities": []}
            current_address["name"] = entity.text
            current_address["spacy_entities"].append(entity)
            current_address["type"] = entity.label_
        elif entity.label_ == "CITY":
            current_address["city"] = entity.text
            current_address["spacy_entities"].append(entity)
            if current_address["name"]:
                addresses.append(current_address)
                current_address = {"name": None, "house_number": None, "house_numbers": [], "bus": None, "postcode": None, "city": None, "type": None, "spacy_entities": []}

    if current_address["name"]:
        addresses.append(current_address)

    for address in addresses:
        if not address["city"]:
            address["city"] = from_city

    return addresses

def split_addresses(addresses):
    individual_addresses = []
    for multi_address in addresses:
        for house_number_string in multi_address['house_numbers']:
            house_number_object = extract_house_and_bus_number(str(house_number_string))
            individual_address = {
                'name': multi_address['name'],
                'house_number': house_number_object["housenumber"],
                'bus': house_number_object["bus"],
                'postcode': multi_address['postcode'],
                'city': multi_address['city'],
                "type": "HOUSE",
                "spacy_entities": multi_address["spacy_entities"]
            }
            individual_addresses.append(individual_address)
    return individual_addresses

def process_text(text, ner_model, from_city="Gent"):
    doc = ner_model.extract_entities(text)
    if hasattr(doc, 'error'):
        return [], [], doc
    
    detected_addresses = form_addresses(doc.ents, from_city)
    detected_locations = form_locations(doc.ents, from_city)
    individual_addresses = split_addresses(detected_addresses)
    detectables = individual_addresses + detected_locations
    
    return detectables, doc.ents, doc

def geocode_detectable(detectable, geocoder, default_city="Gent"):
    name = detectable.get("name", "")
    if not name:
        return {"success": False, "error": "No name in detectable"}
    
    if detectable.get("type") == "HOUSE" and detectable.get("house_number"):
        query = f"{name} {detectable['house_number']}"
    else:
        query = name
    
    city = detectable.get("city", default_city)
    result = geocoder.search(query, city=city)
    
    if result:
        return {
            "success": True,
            "query": query,
            "display_name": result["display_name"],
            "lat": result["lat"],
            "lon": result["lon"],
            "osm_url": result.get("osm_url"),
            "address": result.get("address"),
            "detectable": detectable
        }
    else:
        return {
            "success": False,
            "query": query,
            "city": city,
            "error": f"No geocoding result found for '{query}' in {city}",
            "detectable": detectable
        }

def render_entities_html(doc):
    """Render entities with custom styling"""
    html_content = ""
    last_end = 0
    
    for ent in doc.ents:
        # Add text before entity
        html_content += doc.text[last_end:ent.start_char]
        
        # Add entity with styling
        entity_class = f"entity-{ent.label_}"
        html_content += f'<span class="entity-highlight {entity_class}" title="{ent.label_}">{ent.text}</span>'
        
        last_end = ent.end_char
    
    # Add remaining text
    html_content += doc.text[last_end:]
    
    return html_content

# Initialize session state
if 'ner_analyzer' not in st.session_state:
    st.session_state.ner_analyzer = None
if 'geocoder' not in st.session_state:
    st.session_state.geocoder = None

# App Header
st.title("🗺️ Location Extraction & Geocoding")

# Configuration
with st.expander("Configuration", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("NER Model")
        model_path = st.text_input(
            "Model Path", 
            value=os.getenv("HF_MODEL_PATH", "D:/OneDrive - Sirus NV/ABB/UC0.1/UC1/models/ner/robbert/model-best")
        )
        ner_labels = st.multiselect(
            "Labels to Extract",
            ['CITY', 'DOMAIN', 'HOUSENUMBERS', 'INTERSECTION', 'POSTCODE', 'PROVINCE', 'ROAD', 'STREET'],
            default=['CITY', 'DOMAIN', 'HOUSENUMBERS', 'INTERSECTION', 'POSTCODE', 'PROVINCE', 'ROAD', 'STREET']
        )
    
    with col2:
        st.subheader("Geocoding")
        nominatim_url = st.text_input("Nominatim URL", value=os.getenv("NOMINATIM_URL", "http://localhost:8080"))
        default_city = st.text_input("Default City", value="Gent")

    # Initialize models button
    if st.button("🔄 Initialize Models"):
        with st.spinner("Loading models..."):
            st.session_state.ner_analyzer = SpacyNERAnalyzer(model_path, ner_labels)
            st.session_state.geocoder = NominatimGeocoder(base_url=nominatim_url, rate_limit=0.5)
            
            # Test geocoder
            test_result = st.session_state.geocoder.search("Zandstraat 1", city=default_city)
            if test_result:
                st.success("✅ Models loaded successfully")
            else:
                st.warning("⚠️ Geocoder test failed")

# Input
st.header("Input Text")
input_method = st.radio("Input method:", ["Paste Text", "Upload File"], horizontal=True)

input_text = ""
if input_method == "Paste Text":
    input_text = st.text_area(
        "Text to analyze:",
        height=150,
        placeholder="Paste the text you want to analyze for locations..."
    )
else:
    uploaded_file = st.file_uploader("Choose a text file", type=['txt'])
    if uploaded_file is not None:
        input_text = str(uploaded_file.read(), "utf-8")
        st.text_area("File content:", input_text, height=150, disabled=True)

# Processing
if input_text and st.session_state.ner_analyzer and st.session_state.geocoder:
    with st.spinner("Processing..."):
        cleaned_text = clean_string(input_text)
        detectables, entities, doc = process_text(cleaned_text, st.session_state.ner_analyzer, default_city)
        
        if hasattr(doc, 'error'):
            st.error(f"Error: {doc['error']}")
        else:
            # Display annotated text
            st.header("🏷️ Detected Entities")
            annotated_html = render_entities_html(doc)
            st.markdown(f'<div class="annotation-box">{annotated_html}</div>', unsafe_allow_html=True)

            # Geocoding Results
            if detectables:
                st.header("Geocoding Results")
                
                # Geocode all detectables
                geocoded_results = []
                progress_bar = st.progress(0)
                
                for i, detectable in enumerate(detectables):
                    result = geocode_detectable(detectable, st.session_state.geocoder, default_city)
                    geocoded_results.append(result)
                    progress_bar.progress((i + 1) / len(detectables))
                
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
                            "Found Location": f"❌ Not found",
                            "Coordinates": "",
                            "OpenStreetMap": ""
                        })
                
                if results_data:
                    df = pd.DataFrame(results_data)
                    st.dataframe(
                        df, 
                        use_container_width=True,
                        column_config={
                            "OpenStreetMap": st.column_config.LinkColumn(
                                "OpenStreetMap",
                                help="View location on OpenStreetMap",
                                validate="^https://www\.openstreetmap\.org/.*",
                                max_chars=100,
                                display_text="View on OSM"
                            )
                        }
                    )
                    
                    # Simple map for successful results
                    successful_results = [r for r in geocoded_results if r["success"]]
                    if successful_results:
                        center_lat = sum(r["lat"] for r in successful_results) / len(successful_results)
                        center_lon = sum(r["lon"] for r in successful_results) / len(successful_results)
                        
                        m = Map(location=[center_lat, center_lon], zoom_start=12)
                        for result in successful_results:
                            Marker(
                                [result["lat"], result["lon"]],
                                popup=result["detectable"]["name"],
                                tooltip=result["detectable"]["name"]
                            ).add_to(m)
                        
                        st.components.v1.html(m._repr_html_(), height=400)
            else:
                st.info("No location entities detected.")

elif input_text and (not st.session_state.ner_analyzer or not st.session_state.geocoder):
    st.warning("Please initialize the models first using the configuration section above.")
