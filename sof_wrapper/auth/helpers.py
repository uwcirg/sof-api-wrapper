from jose import jwt


def extract_payload(token):
    """Given JWT, extract the payload and return as dict"""
    if not token:
        return None
    return jwt.get_unverified_claims(token)
