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
    #return {'ok':True}

@blueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response
