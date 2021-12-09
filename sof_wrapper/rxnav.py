from flask import current_app
import json
import timeit
import os

from sof_wrapper.audit import audit_entry
from sof_wrapper.extensions import CS_Singleton


def add_drug_classes(med, rxnav_url):
    """Add Drug Classes"""

    meds = []
    med_text = med["medicationCodeableConcept"]["text"]

    for med_code in med["medicationCodeableConcept"]["coding"]:
        meds.append(f"{med_code['system']}|{med_code['code']}")
        if med_code["system"] == "http://www.nlm.nih.gov/research/umls/rxnorm":
            break
    else:
        # exit early if no RxNorm code found
        audit_entry(
            f"RxNorm code unavailable: '{med_text}' ({meds})",
            extra={'tags': ['RxNorm', 'rxnorm-code-lookup-failed']},
            level='warn')
        return med

    rxcui = med_code["code"]

    rxnav_response = get_drug_classes(rxcui, rxnav_url)
    drug_class_map = load_drug_class_map()
    cosri_drug_classes = set(
        drug_class_map[drug_class_id]
        for drug_class_id in drug_class_filter(rxnav_response) if drug_class_id in drug_class_map
    )

    if not cosri_drug_classes:
        msg = f"drug class unavailable: {med_text} ({meds})"
        audit_entry(
            msg,
            extra={'tags': ['RxNorm', 'rxnorm-drug-class-not-found']},
            level='warn',
        )
        # submit error for ELK alerts as this should get attention
        current_app.logger.error(msg)

    annotated_med = med.copy()
    med_cc_extensions = annotated_med["medicationCodeableConcept"].get("extension", [])

    for cosri_drug_class in cosri_drug_classes:
        med_cc_extensions.append({
            "url": "http://cosri.org/fhir/drug_class",
            "valueString": cosri_drug_class,
        })

    annotated_med["medicationCodeableConcept"]["extension"] = med_cc_extensions
    return annotated_med


def get_drug_classes(rxcui, rxnav_url):
    """Get all drug classes from RxNav API

    https://rxnav.nlm.nih.gov/api-RxClass.getClassByRxNormDrugId.html
    """
    start_time = timeit.default_timer()
    cached_session = CS_Singleton().cached_session
    response = cached_session.get(
        url=f"{rxnav_url}/REST/rxclass/class/byRxcui.json",
        params={"rxcui": rxcui},
    )
    request_time = timeit.default_timer() - start_time
    if request_time > 0.01:
        current_app.logger.debug(f"uncached rxnav {rxcui} request time: {request_time}")
    return response.json()


def drug_class_filter(rxnav_response):
    """Generator for collecting drug class names from RxNav JSON response"""
    for rx_class in rxnav_response["rxclassDrugInfoList"]["rxclassDrugInfo"]:
        yield rx_class["rxclassMinConceptItem"]["classId"]


def load_drug_class_map(filename="rx-class-map.json"):
    # TODO cache contents
    # TODO move datafile and rxnav to separate directory
    module_path = os.path.dirname(__file__)
    filepath = os.path.join(module_path, filename)

    with open(filepath, 'r') as map_file:
        drug_class_map = json.loads(map_file.read())
    return drug_class_map
