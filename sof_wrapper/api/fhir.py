from flask import Blueprint, current_app
import requests


blueprint = Blueprint('fhir', __name__, url_prefix='/v/r2/fhir/')


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
