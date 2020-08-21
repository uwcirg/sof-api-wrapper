from flask import Blueprint, current_app, request, session
import requests


blueprint = Blueprint('fhir', __name__)
r2prefix = '/v/r2/fhir'
r4prefix = '/v/r4/fhir'


def collate_results(*result_sets):
    """Compile given result sets into a single bundle"""
    results = {'resourceType': 'Bundle', 'entry': []}

    for rs in result_sets:
        results['entry'].extend(rs['entry'])

    results['total'] = len(results['entry'])
    return results


@blueprint.route(f'{r4prefix}/emr/MedicationRequest')
@blueprint.route(f'{r4prefix}/emr/MedicationRequest/<string:patient_id>')
def emr_med_requests(patient_id=None):
    base_url = session['iss']
    emr_url = f'{base_url}/MedicationRequest'
    params = {"subject": f"Patient/{patient_id}"} if patient_id else {}
    # TODO: enhance for audit or remove PHI?
    current_app.logger.debug(
        f"fire request for emr meds on {emr_url}/?{params}")
    response = requests.get(emr_url, params)
    response.raise_for_status()
    current_app.logger.debug("emr returned {} MedicationRequests".format(
        len(response.json().get("entry", []))))
    return response.json()


@blueprint.route(f'{r4prefix}/pdmp/MedicationRequest')
def pdmp_med_requests(**kwargs):
    """return results from PDMP request for MedicationRequest

    Include as kwargs or request parameters for remote query.
    - 'subject:Patient.name.given': given name
    - 'subject:Patient.name.family': family name
    - 'subject:Patient.birthdate': DOB in `eqYYYY-MM-DD` format

    """
    # script-fhir-facade refers to r4 MedicationRequest as MedicationOrder
    pdmp_url = '{base_url}/v/r4/fhir/MedicationOrder'.format(
        base_url=current_app.config['PDMP_URL'],
    )
    params = kwargs or request.args
    # TODO: remove hack to generate fake records for Brenda from Darth
    if (
            params.get('subject:Patient.name.family') == 'Jackson' and
            params.get('subject:Patient.name.given') == 'Brenda' and
            params.get('subject:Patient.birthdate') == 'eq1956-10-14'):
        # avoid type errors on request.args by replacing
        params = {
            'subject:Patient.name.family': 'Vader',
            'subject:Patient.name.given': 'Darth',
            'subject:Patient.birthdate': 'eq1945-01-15'
        }

    # TODO: enhance for audit or remove PHI?
    current_app.logger.debug(
        f"fire request for PDMP meds on {pdmp_url}/?{params}")
    response = requests.get(pdmp_url, params=params)
    response.raise_for_status()
    current_app.logger.debug("PDMP returned {} MedicationRequests".format(
        len(response.json().get("entry", []))))
    return response.json()


@blueprint.route(f'{r4prefix}/MedicationRequest')
def medication_requests():
    """Return compiled list of MedicationRequests from available endpoints"""

    # TODO: should patient_id be a request parameter?
    # TODO: determine most reliable source of patient_id.
    patient_id = session.get('launch_token_patient', None)
    pdmp_args = {}
    if patient_id:
        patient_fhir = patient_by_id(patient_id)
        pdmp_args['subject:Patient.name.family'] = patient_fhir[
            'name'][0]['family']
        pdmp_args['subject:Patient.name.given'] = patient_fhir[
            'name'][0]['given'][0]
        pdmp_args['subject:Patient.birthdate'] = (
            f"eq{patient_fhir['birthDate']}")

    return collate_results(
        pdmp_med_requests(**pdmp_args), emr_med_requests(patient_id))


@blueprint.route(f'{r2prefix}/MedicationOrder')
def medication_order():
    pdmp_url = '{base_url}/v/r2/fhir/MedicationOrder'.format(
        base_url=current_app.config['PDMP_URL'],
    )
    response = requests.get(pdmp_url)
    response.raise_for_status()
    return response.json()


@blueprint.route(f'{r2prefix}/Observation')
def observations():
    phr_url = '{base_url}/Observation'.format(
        base_url=current_app.config['PHR_URL'],
    )
    # todo: lookup from frontend with Patient details
    phr_params = {'patient._id': '53b07006-f454-ea11-8241-0a0332b55c97'}

    phr_observations = requests.get(
        url=phr_url,
        params=phr_params,
        headers={
            'Authorization': 'Bearer %s' % current_app.config['PHR_TOKEN'],
            'Accept': 'application/json',
        },
    )
    phr_observations.raise_for_status()
    return phr_observations.json()


@blueprint.route(f'{r4prefix}/Patient/<string:id>')
def patient_by_id(id):
    base_url = session['iss']
    key = f'patient_{id}'
    if key in session:
        return session[key]

    patient_url = f'{base_url}/Patient/{id}'
    response = requests.get(patient_url)
    response.raise_for_status()
    patient_fhir = response.json()
    session[key] = patient_fhir

    return patient_fhir


@blueprint.route('/fhir-router/', defaults={'relative_path': ''})
@blueprint.route('/fhir-router/<path:relative_path>')
def route_fhir(relative_path):
    paths = relative_path.split('/')
    resource_name = paths.pop()

    route_map = {
        #'MedicationOrder': medication_order,
        #'MedicationRequest': medication_requests
    }


    if resource_name in route_map:
        return route_map[resource_name]()

    # TODO: associate session vars correctly
    upstream_fhir_base_url = session.get('iss', 'https://launch.smarthealthit.org/v/r4/fhir')
    upstream_fhir_url = '/'.join((upstream_fhir_base_url, relative_path))
    upstream_headers = {}
    if 'Authorization' in request.headers:
        upstream_headers = {'Authorization': request.headers['Authorization']}

    upstream_response = requests.get(
        url=upstream_fhir_url,
        headers=upstream_headers,
        params=request.args,
    )
    upstream_response.raise_for_status()
    return upstream_response.json()


@blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
