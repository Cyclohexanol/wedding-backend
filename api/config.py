import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

class BaseConfig():
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join('/app/db', 'apidata.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "saamblove-2023"
    JWT_SECRET_KEY = "saamblove-2023"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8500)
    PRODUCTION=True if os.getenv("BRANCH") == "main" else False