import json
import os
from pytest import fixture


@fixture
def emr_med_request_bundle(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(
            data_dir, "MedicationRequestBundleR4.json"), 'r') as json_file:
        data = json.load(json_file)
    return data


@fixture
def pdmp_med_request_bundle(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(
            data_dir, "PDMP-MedicationRequestBundleR4.json"), 'r') as json_file:
        data = json.load(json_file)
    return data


def test_emr_med_request(app, requests_mock, emr_med_request_bundle):
    with app.test_client() as c:

        # Mock session having captured the emr url as `iss`
        emr_endpoint = "https://launch.smarthealthit.org/v/r4/fhir"
        with c.session_transaction() as sess:
            sess['iss'] = emr_endpoint

        # Mock a requests.get response for MedicationRequest
        requests_mock.get(
            '/'.join((emr_endpoint, 'MedicationRequest')),
            json=emr_med_request_bundle)

        result = c.get('/v/r2/fhir/emr/MedicationRequest')
        assert result.json == emr_med_request_bundle


def test_pdmp_med_request(app, requests_mock, pdmp_med_request_bundle):
    pdmp_url = "https://cosri-pdmp.cirg.washington.edu"
    app.config['PDMP_URL'] = pdmp_url

    with app.test_client() as c:
        pdmp_api = f"{pdmp_url}/v/r4/fhir/MedicationOrder"
        requests_mock.get(pdmp_api, json=pdmp_med_request_bundle)
        result = c.get('/v/r2/fhir/pdmp/MedicationRequest')
        assert result.json == pdmp_med_request_bundle


def test_combine_bundles(emr_med_request_bundle, pdmp_med_request_bundle):
    from sof_wrapper.api.fhir import collate_results
    result = collate_results(emr_med_request_bundle, pdmp_med_request_bundle)
    assert result['resourceType'] == 'Bundle'
    assert len(result['entry']) == len(emr_med_request_bundle['entry']) + len(
        pdmp_med_request_bundle['entry'])
