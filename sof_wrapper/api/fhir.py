from flask import Blueprint, current_app, session
import requests


blueprint = Blueprint('fhir', __name__, url_prefix='/v/r2/fhir/')


def collate_results(*result_sets):
    """Compile given result sets into a single bundle"""
    results = {'resourceType': 'Bundle', 'entry': []}

    for rs in result_sets:
        results['entry'].extend(rs['entry'])

    results['total'] = len(results['entry'])
    return results


@blueprint.route('/emr/MedicationRequest')
def emr_med_requests():
    base_url = session['iss']
    emr_url = f'{base_url}/MedicationRequest'
    response = requests.get(emr_url)
    response.raise_for_status()
    return response.json()


@blueprint.route('/pdmp/MedicationRequest')
def pdmp_med_requests():
    # PDMP refers to r4 MedicationRequest as MedicationOrder
    pdmp_url = '{base_url}/v/r4/fhir/MedicationOrder'.format(
        base_url=current_app.config['PDMP_URL'],
    )
    response = requests.get(pdmp_url)
    response.raise_for_status()
    return response.json()


@blueprint.route('/MedicationRequest')
def medication_requests():
    """Return compiled list of MedicationRequests from available endpoints"""
    return collate_results((pdmp_med_requests(), emr_med_requests()))


@blueprint.route('/MedicationOrder')
def medication_order():
    pdmp_url = '{base_url}/v/r2/fhir/MedicationOrder'.format(
        base_url=current_app.config['PDMP_URL'],
    )
    response = requests.get(pdmp_url)
    response.raise_for_status()
    return response.json()


@blueprint.route('/Observation')
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


@blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
