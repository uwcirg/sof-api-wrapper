"""Default configuration

Use env var to override
"""
import os

SERVER_NAME = os.getenv("SERVER_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")


SOF_CLIENT_ID = os.getenv("SOF_CLIENT_ID")
SOF_CLIENT_SECRET = os.getenv("SOF_CLIENT_SECRET")
