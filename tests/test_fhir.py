import json
import os
import pickle
from pytest import fixture
from pytest_redis import factories
from sof_wrapper.config import SESSION_REDIS

emr_endpoint = "https://launch.smarthealthit.org/v/r4/fhir"
patient_id = '5c41cecf-cf81-434f-9da7-e24e5a99dbc2'
session_id = 'mock-session'


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


real_redis_connection = SESSION_REDIS.connection_pool.get_connection('testing-connection')
redis_factory = factories.redis_noproc(host=real_redis_connection.host)
redis_handle = factories.redisdb('redis_factory')


@fixture
def redis_session(client, redis_handle):
    """Loads a redis-session with a mock patient id and iss"""
    session_prefix = client.application.config.get(
        'SESSION_KEY_PREFIX', 'session:')
    session_key = f'{session_prefix}{session_id}'
    session_data = {
        'iss': emr_endpoint,
        'token_response': {'patient': patient_id}
    }

    redis_handle.set(session_key, pickle.dumps(session_data))


@fixture
def auth_extensions():
    """Returns a set of extensions typically used for auth, a subset of a FHIR conformance statement"""
    return [
        {
            "url": "token",
            "valueUri": "https://cpsapisandbox.virenceaz.com:9443/demoAPIServer/oauth2/token"
        },
        {
            "url": "authorize",
            "valueUri": "https://cpsapisandbox.virenceaz.com:9443/demoAPIServer/oauth2/authorize"
        },
        {
            "url": "register",
            "valueUri": "https://cpsapisandbox.virenceaz.com:9443/demoAPIServer/oauth2/registration"
        }
    ]


@fixture
def pdmp_medication_request():
    """Returns a sample FHIR R4 MedicationRequest from the PDMP SCRIPT facade"""

    return {
      "authoredOn": "2018-09-20",
      "dispenseRequest": {
        "expectedSupplyDuration": {
          "code": "d",
          "system": "http://unitsofmeasure.org",
          "unit": "days",
          "value": 10
        },
        "quantity": {
          "value": 25
        }
      },
      "medicationCodeableConcept": {
        "coding": [
          {
            "code": "16714062201",
            "display": "ZOLPIDEM TARTRATE 10 MG TABLET",
            "system": "http://hl7.org/fhir/sid/ndc"
          },
          {
            "code": "854873",
            "display": "ZOLPIDEM TARTRATE 10 MG TABLET",
            "system": "http://www.nlm.nih.gov/research/umls/rxnorm"
          }
        ],
        "text": "ZOLPIDEM TARTRATE 10 MG TABLET"
      },
      "requester": {
        "display": "HID TEST PRESCRIBER"
      },
      "resourceType": "MedicationRequest"
    }


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
    path = f'/v/r4/fhir/Patient/{patient_id}'

    # Mock EHR Patient request
    requests_mock.get(path, json=patient_b_jackson)

    result = app_w_iss.get(path)
    assert result.json == patient_b_jackson


def test_fhir_router_requires_patient(client):
    """Without a patient, expect 400"""
    result = client.get('/fhir-router/')
    assert result.status_code == 400


def test_fhir_router_with_patient_param(client, mocker, redis_session):
    """Mock function routed to - confirm correct calling parameters"""
    from sof_wrapper.api import fhir
    mocker.patch.object(fhir, 'medication_request')
    fhir.medication_request.return_value = {'mock': 'results'}

    result = client.get(f'/fhir-router/{session_id}/MedicationRequest')
    fhir.medication_request.assert_called_once_with(patient_id=patient_id)


def test_extension_lookup(auth_extensions):
    """Test extension lookup by extension URL"""
    from sof_wrapper.auth.views import get_extension_value
    authorize_url = get_extension_value(url='authorize', extensions=auth_extensions)
    assert authorize_url == 'https://cpsapisandbox.virenceaz.com:9443/demoAPIServer/oauth2/authorize'

    token_url = get_extension_value(url='token', extensions=auth_extensions)
    assert token_url == 'https://cpsapisandbox.virenceaz.com:9443/demoAPIServer/oauth2/token'


def test_dosage_instruction(pdmp_medication_request):
    """Test MedicationRequest.dosageInstruction CDS annotations"""
    supply = pdmp_medication_request['dispenseRequest']['expectedSupplyDuration']['value']
    quantity = pdmp_medication_request['dispenseRequest']['quantity']['value']

    from sof_wrapper.api import fhir
    annotated_pdmp_med = fhir.add_cds_extensions(pdmp_medication_request)

    assert annotated_pdmp_med['dispenseRequest']['dosageInstruction'][0]['timing']['repeat']['frequency'] == quantity
    assert annotated_pdmp_med['dispenseRequest']['dosageInstruction'][0]['timing']['repeat']['period'] == supply

    assert annotated_pdmp_med['dispenseRequest']['dosageInstruction'][0]['doseAndRate'][0]['doseQuantity']['value'] == supply/quantity
