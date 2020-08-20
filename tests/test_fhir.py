import json
import os
from pytest import fixture

emr_endpoint = "https://launch.smarthealthit.org/v/r4/fhir"


@fixture
def app_w_iss(app):
    # Fixture to push url for 'iss' into session
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['iss'] = emr_endpoint
    yield c


def json_from_file(request, filename):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, filename), 'r') as json_file:
        data = json.load(json_file)
    return data


@fixture
def emr_med_request_bundle(request):
    return json_from_file(request, "MedicationRequestBundleR4.json")


@fixture
def patient_b_jackson(request):
    return json_from_file(request, "PatientBJackson.json")


@fixture
def pdmp_med_request_bundle(request):
    return json_from_file(request, "PDMP-MedicationRequestBundleR4.json")


def test_emr_med_request(app_w_iss, requests_mock, emr_med_request_bundle):
    """Test EMR MedicationRequest"""
    # Mock EMR response for MedicationRequest
    requests_mock.get(
        '/'.join((emr_endpoint, 'MedicationRequest')),
        json=emr_med_request_bundle)

    result = app_w_iss.get('/v/r4/fhir/emr/MedicationRequest')
    assert result.json == emr_med_request_bundle


def test_pdmp_med_request(client, requests_mock, pdmp_med_request_bundle):
    pdmp_url = "https://cosri-pdmp.cirg.washington.edu"
    client.application.config['PDMP_URL'] = pdmp_url
    pdmp_api = f"{pdmp_url}/v/r4/fhir/MedicationOrder"

    # mock PDMP MedicationRequest
    requests_mock.get(pdmp_api, json=pdmp_med_request_bundle)

    result = client.get('/v/r4/fhir/pdmp/MedicationRequest')
    assert result.json == pdmp_med_request_bundle


def test_combine_bundles(emr_med_request_bundle, pdmp_med_request_bundle):
    from sof_wrapper.api.fhir import collate_results
    result = collate_results(emr_med_request_bundle, pdmp_med_request_bundle)
    assert result['resourceType'] == 'Bundle'
    assert len(result['entry']) == len(emr_med_request_bundle['entry']) + len(
        pdmp_med_request_bundle['entry'])


def test_patient_by_id(app_w_iss, requests_mock, patient_b_jackson):
    patient_id = '5c41cecf-cf81-434f-9da7-e24e5a99dbc2'
    path = f'/v/r4/fhir/Patient/{patient_id}'

    # Mock EHR Patient request
    requests_mock.get(path, json=patient_b_jackson)

    result = app_w_iss.get(path)
    assert result.json == patient_b_jackson
