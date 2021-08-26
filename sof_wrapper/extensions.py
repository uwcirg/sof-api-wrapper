from authlib.integrations.flask_client import OAuth
from flask_session import Session
from requests_cache import CachedSession

cached_session = CachedSession()
oauth = OAuth()
sess = Session()
