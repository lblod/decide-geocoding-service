import re
import unicodedata

class LocationEntitiesSolver:
    def __init__(self, ner_model, default_city="Gent"):
        self.default_city = default_city
        self.ner_model = ner_model

    @staticmethod
    def clean_string(input_string):
        cleaned_string = input_string.replace('\n', ' ')
        cleaned_string = cleaned_string.strip()
        cleaned_string = re.sub(r'\s+', ' ', cleaned_string)
        cleaned_string = unicodedata.normalize('NFKD', cleaned_string)
        return cleaned_string

    @staticmethod
    def clean_house_number(housenumber):
        housenumber = housenumber.replace("  ", " ").replace("tot en met",'t.e.m.').replace("TOT EN MET",'t.e.m.')
        housenumber = re.sub(r'\b(huisnummer|huisnr|nr|nummer)\b', '', housenumber, flags=re.IGNORECASE)
        housenumber = re.sub(r'\s+', ' ', housenumber).strip()
        parts = [item.strip() for item in re.split(r',|en', housenumber) if item]
        result_list = []
        for part in parts:
            part = part.strip()
            if "-" in part:
                segments = part.split("-")
                if len(segments) == 2:
                    start, end = segments
                    if start.strip().isdigit() and end.strip().isdigit():
                        start = int(start.strip())
                        end = int(end.strip())
                        if start < 1000 and end < 1000 and end-start < 20 and end>start:
                            result_list.extend(map(str, range(start, end + 1)))
                        else:
                            result_list.append(start)
                            result_list.append(end)
                    else:
                        result_list.append(start)
                        result_list.append(end)
                else:
                    for segment in segments:
                        result_list.append(segment)
            elif "tot" in part.lower() or "t.e.m." in part.lower():
                numbers = [num for num in re.split(r'\D+', part) if num]
                if len(numbers) == 2:
                    start, end = map(int, numbers)
                    if "tot" in part.lower():
                        end-=1
                    result_list.extend(map(str, range(start, end + 1)))
                else:
                    result_list.append(part)
            elif "/" in part and "bus" not in part.lower():
                start, end = part.split("/")
                result_list.append(start.strip())
                result_list.append(end.strip())
            else:
                result_list.append(part)
        return result_list

    @staticmethod
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

    def form_addresses(self, entities):
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
                current_address["house_numbers"] = self.clean_house_number(entity.text)
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
                address["city"] = self.default_city
        return addresses

    def form_locations(self, entities):
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
                address["city"] = self.default_city
        return addresses

    def split_addresses(self, addresses):
        individual_addresses = []
        for multi_address in addresses:
            for house_number_string in multi_address['house_numbers']:
                house_number_object = self.extract_house_and_bus_number(str(house_number_string))
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

    def process_text(self, text):
        doc = self.ner_model.extract_entities(text)
        if hasattr(doc, 'error'):
            return [], [], doc
        detected_addresses = self.form_addresses(doc.ents)
        detected_locations = self.form_locations(doc.ents)
        individual_addresses = self.split_addresses(detected_addresses)
        detectables = individual_addresses + detected_locations
        return detectables, doc
