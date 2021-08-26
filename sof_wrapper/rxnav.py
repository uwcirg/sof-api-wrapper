import requests
import json
import os

def add_drug_classes(med, rxnav_url):
    """Add Drug Classes"""

    for med_code in med["medicationCodeableConcept"]["coding"]:
        if med_code["system"] == "http://www.nlm.nih.gov/research/umls/rxnorm":
            break
    else:
        # exit early if no RxNorm code found
        return med

    rxcui = med_code["code"]

    rxnav_response = get_drug_classes(rxcui, rxnav_url)
    drug_class_map = load_drug_class_map()
    drug_classes = set(
        drug_class_map[drug_class]
        for drug_class in drug_class_filter(rxnav_response) if drug_class in drug_class_map
    )

    annotated_med = med.copy()
    med_cc_extensions = annotated_med["medicationCodeableConcept"].get("extension", [])

    for drug_class in drug_classes:
        med_cc_extensions.append({
            "url": "http://cosri.org/fhir/drug_class",
            "valueString": drug_class,
        })

    annotated_med["medicationCodeableConcept"]["extension"] = med_cc_extensions
    return annotated_med


def get_drug_classes(rxcui, rxnav_url):
    """Get all drug classes from RxNav API

    https://rxnav.nlm.nih.gov/api-RxClass.getClassByRxNormDrugId.html
    """

    # NB requests-cached
    response = requests.get(
        url=f"{rxnav_url}/REST/rxclass/class/byRxcui.json",
        params={"rxcui": rxcui},
    )
    return response.json()


def drug_class_filter(rxnav_response):
    """Generator for collecting drug class names from RxNav JSON response"""
    for rx_class in rxnav_response["rxclassDrugInfoList"]["rxclassDrugInfo"]:
        yield rx_class["rxclassMinConceptItem"]["className"]


def load_drug_class_map(filename="rx-class-map.json"):
    # TODO cache contents
    # TODO move datafile and rxnav to separate directory
    module_path = os.path.dirname(__file__)
    filepath = os.path.join(module_path, filename)

    with open(filepath, 'r') as map_file:
        drug_class_map = json.loads(map_file.read())
    return drug_class_map
