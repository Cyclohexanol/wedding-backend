# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from datetime import datetime

import json
import enum

from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class RegistrationStatus(str, enum.Enum):
    NOT_REGISTERED = "Not registered"
    REGISTERED = "Registered"

class AttendanceStatus(str, enum.Enum):
    NOT_ATTENDING = "Not Attending"
    ATTENDING = "Attending"
    UNKNOWN = "Unknown"

class DietaryRestrictions(str, enum.Enum):
    NONE = "None"
    VEGETARIAN = "Vegetarian"
    VEGAN = "Vegan"

class Groups(db.Model):

    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    users = db.relationship("Users", backref="group", lazy=True)
    super_group = db.Column(db.Boolean, default=False, nullable=False)
    
    jwt_auth_active = db.Column(db.Boolean())

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def update(self, name):
        self.name = name
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def check_jwt_auth_active(self):
        return self.jwt_auth_active

    def set_jwt_auth_active(self, set_status):
        self.jwt_auth_active = set_status

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def __repr__(self):
        return f"{self.name}"

    def serialize(self):
        return {"id": self.id, "name": self.name}

    def toDICT(self):

        cls_dict = {}
        cls_dict['_id'] = self.id
        cls_dict['name'] = self.name

        return cls_dict

    def toJSON(self):

        return self.toDICT()

class Users(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    registration_status = db.Column(db.Enum(RegistrationStatus), default=RegistrationStatus.NOT_REGISTERED)
    dietary_restrictions = db.Column(db.Enum(DietaryRestrictions), default=DietaryRestrictions.NONE)
    attendance_status = db.Column(db.Enum(AttendanceStatus), default=AttendanceStatus.UNKNOWN)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    dietary_info = db.Column(db.String(512))
    song_request = db.Column(db.String(512))


    def __repr__(self):
        return f"User {self.username}"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update_first_name(self, first_name):
        self.first_name = first_name

    def update_last_name(self, last_name):
        self.last_name = last_name

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_by_group_id(cls, group_id):
        return cls.query.filter_by(group_id=group_id).all()

    @classmethod
    def get_by_name(cls, first_name, last_name):
        return cls.query.filter_by(first_name=first_name, last_name=last_name).first()

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def toDICT(self):

        cls_dict = {}
        cls_dict['_id'] = self.id
        cls_dict['firstName'] = self.first_name
        cls_dict['lastName'] = self.last_name
        cls_dict['registrationStatus'] = self.registration_status
        cls_dict['dietaryRestrictions'] = self.dietary_restrictions
        cls_dict['attendanceStatus'] = self.attendance_status
        cls_dict['groupId'] = self.group_id
        cls_dict['dietaryInfo'] = self.dietary_info
        cls_dict['songRequest'] = self.song_request

        return cls_dict

    def toJSON(self):

        return self.toDICT()


class JWTTokenBlocklist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    jwt_token = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False)

    def __repr__(self):
        return f"Expired Token: {self.jwt_token}"

    def save(self):
        db.session.add(self)
        db.session.commit()
