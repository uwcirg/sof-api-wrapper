from pytest import fixture
from sof_wrapper.auth.helpers import extract_payload, format_as_jwt

@fixture
def encoded_payload():
    return 'eyJhIjoiMSIsImIiOiI0MTcwMiIsImUiOiJTTUFSVC0xMjM0In0'


@fixture
def example_token():
    return '.'.join((
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9',
        'eyJwcm9maWxlIjoiUHJhY3RpdGlvbmVyL1NNQVJULTEyMzQiLCJzdWIiOiI3NmQ1M2Zm'
        'NmNjZDY5ZWEyN2YzMjM5MzgwYjMwMzliNGE4NzI5OTJmODE1MWViMzE4Y2UxODZlZDlm'
        'MmYzMTNjIiwiaXNzIjoiaHR0cHM6Ly9zbWFydC1kZXYtc2FuZGJveC1sYXVuY2hlci5j'
        'aXJnLndhc2hpbmd0b24uZWR1IiwiaWF0IjoxNTg4MDIwNDU3LCJleHAiOjE1ODgwMjQw'
        'NTd9',
        'PyWKOdkS1AUGF6R0s1RWkhLXF2rFKq9m-Xdw4LaJSHKchpDRVpZ_jlpv73D09F3pIRJn'
        'Tq10EJDv34V0UNRiD53IVgdTS680p-kj5t1fpE66aOU-aLQHkaH0mdvGVdXKGHaidda2'
        'Uq-QdoVT17RtKHeVzfKdEOMGbKPUDbKktgVw57JuTrUgtsOihsYKMu5j09J6ZB1K1deg'
        'm2ppl_0DMhP_UJgbniOlgpIyR2QYLTS2Dz-DLsYmPr-anK8d_wVHdXqt3TCnCnYOww8o'
        '6eBsFF_BtbWNO-CYTsnhQB_UKs1TNVrneVoTDGSLZPdcnK1ay23IiA2PTybPrFja6kdz'
        'qQ'))


def test_extract(example_token):
    extracted = extract_payload(example_token)
    assert 'profile' in extracted
    assert extracted['profile'] == 'Practitioner/SMART-1234'


def test_enc_payload_extract(encoded_payload):
    jwt = format_as_jwt(encoded_payload)
    assert len(jwt.split('.')) == 3
    assert extract_payload(jwt) == {'a': '1', 'b': '41702', 'e': 'SMART-1234'}


def test_bad_extract():
    jwt = format_as_jwt('ill formed string')
    assert len(jwt.split('.')) == 3
    assert extract_payload(jwt) == {}
