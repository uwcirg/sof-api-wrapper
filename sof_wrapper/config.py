"""Default configuration

Use env var to override
"""
import os
import redis

SERVER_NAME = os.getenv("SERVER_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
# URL scheme to use outside of request context
PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", 'http')

SESSION_TYPE = os.getenv("SESSION_TYPE", 'redis')
SESSION_REDIS = redis.from_url(os.getenv("SESSION_REDIS", "redis://127.0.0.1:6379"))

SOF_CLIENT_ID = os.getenv("SOF_CLIENT_ID")
SOF_CLIENT_SECRET = os.getenv("SOF_CLIENT_SECRET")
SOF_CLIENT_SCOPES = os.getenv("SOF_CLIENT_SCOPES", "patient/*.read launch/patient")

SOF_ACCESS_TOKEN_URL = os.getenv("SOF_ACCESS_TOKEN_URL")
SOF_AUTHORIZE_URL = os.getenv("SOF_AUTHORIZE_URL")


LAUNCH_DEST = os.getenv("LAUNCH_DEST")

PDMP_URL = os.getenv("PDMP_URL")

PHR_URL = os.getenv("PHR_URL")
PHR_TOKEN = os.getenv("PHR_TOKEN")
