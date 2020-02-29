"""Default configuration

Use env var to override
"""
import os

SERVER_NAME = os.getenv("SERVER_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")


SOF_CLIENT_ID = os.getenv("SOF_CLIENT_ID")
SOF_CLIENT_SECRET = os.getenv("SOF_CLIENT_SECRET")
SOF_CLIENT_SCOPES = os.getenv("SOF_CLIENT_SCOPES", "patient/*.read launch/patient")


LAUNCH_DEST = os.getenv("LAUNCH_DEST")

PDMP_URL = os.getenv("PDMP_URL")

PHR_URL = os.getenv("PHR_URL")
PHR_TOKEN = os.getenv("PHR_TOKEN")
