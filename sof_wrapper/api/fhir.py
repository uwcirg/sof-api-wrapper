from flask import Blueprint, current_app
import json
import requests


blueprint = Blueprint('fhir', __name__, url_prefix='/v/r2/fhir/')


@blueprint.route('/MedicationOrder')
def medication_order():
    pdmp_url = current_app.config['PDMP_URL']
    response = requests.get(pdmp_url)
    response.raise_for_status()

    log = open("/tmp/pdmp.log", "a")
    log.write(json.dumps(response.json(), sort_keys=True, indent = 2))
    log.close()

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
    log.write(phr_url + "\n")
    log.write(json.dumps(phr_observations.json(), sort_keys=True, indent = 2))
    log.close()

    return phr_observations.json()


@blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
