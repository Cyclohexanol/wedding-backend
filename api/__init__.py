# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import json

from flask import Flask
from flask_cors import CORS

from .routes import rest_api
from .models import db, Groups, Users

app = Flask(__name__)

app.config.from_object('api.config.BaseConfig')

db.init_app(app)
rest_api.init_app(app)
CORS(app)

# Setup database
@app.before_first_request
def initialize_database():
    db.create_all()
    if Groups.query.filter_by(super_group=True).first() is None:
        super_group = Groups(name="lovebirds", super_group=True)
        super_group.set_password("lovers_in_vevey_2023")
        super_group.save()
    
    saamb_group = Groups.query.filter_by(super_group=True).first()
    saamb_group_id = saamb_group.id

    # If saamb group does not contain 2 users create an user for Ambroise and Sarah
    if len(Users.get_by_group_id(saamb_group_id)) < 2:
        ambroise = Users(first_name="Ambroise", last_name="Mean",group_id=saamb_group_id)
        ambroise.save()
        sarah = Users(first_name="Sarah", last_name="Bertrand",group_id=saamb_group_id)
        sarah.save()


"""
   Custom responses
"""

@app.after_request
def after_request(response):
    """
       Sends back a custom error with {"success", "msg"} format
    """

    if int(response.status_code) >= 400:
        response_data = json.loads(response.get_data())
        if "errors" in response_data:
            response_data = {"success": False,
                             "msg": list(response_data["errors"].items())[0][1]}
            response.set_data(json.dumps(response_data))
        response.headers.add('Content-Type', 'application/json')
    return response
