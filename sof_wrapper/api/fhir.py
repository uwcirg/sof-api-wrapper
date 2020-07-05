from flask import Blueprint, current_app
import requests


blueprint = Blueprint('fhir', __name__, url_prefix='/v/r2/fhir/')


@blueprint.route('/MedicationOrder')
def medication_order():
    pdmp_url = current_app.config['PDMP_URL']
    response = requests.get(pdmp_url)
    response.raise_for_status()
    return response.json()


@blueprint.route('/Observation')
def observations():
    phr_url = current_app.config['PHR_URL']

    phr_observations = requests.get(
        url=phr_url,
        headers={
            'Authorization': 'Bearer %s' % current_app.config['PHR_TOKEN'],
            'Accept': 'application/json',
        },
    )
    phr_observations.raise_for_status()

    log = open("/tmp/phr.log", "a")
    log.write(phr_observations.json())
    log.close()

    return phr_observations.json()


@blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
