# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from datetime import datetime

import csv
import enum

from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

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
    wishes = db.relationship("Wishes", secondary="wishes_groups", back_populates="groups", lazy="dynamic")
    
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
    def get_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

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
    camping_on_site = db.Column(db.Boolean, default=False, nullable=False)
    brunch_sunday = db.Column(db.Boolean, default=False, nullable=False)

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
    
class Wishes(db.Model):
    """Model representing Wish."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(512))
    picture_url = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    groups = db.relationship("Groups", secondary="wishes_groups", back_populates="wishes", lazy="dynamic")

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def toDICT(self):
        cls_dict = {}
        cls_dict['_id'] = self.id
        cls_dict['title'] = self.title
        cls_dict['description'] = self.description
        cls_dict['pictureUrl'] = self.picture_url
        cls_dict['quantity'] = self.quantity
        cls_dict['price'] = self.price
        cls_dict['groups'] = [group.toDICT() for group in self.groups]

        return cls_dict

    def toJSON(self):

        return self.toDICT()

@event.listens_for(Wishes.__table__, 'after_create')
def init_wishes(*args, **kwargs):
    # Read ./data/wishes.csv to populate default data
    with open("./data/wishes.csv", "r") as f:
        csvreader = csv.reader(f)
        # Skip headers on first line
        next(csvreader)
        for row in csvreader:
            wish = Wishes(
                title=row[0],
                description=row[1],
                picture_url="https://fathers.com.sg/wp-content/uploads/2020/09/star-icon.png",
                quantity=row[7],
                price=row[6]
            )
            wish.save()

@event.listens_for(Groups.__table__, 'after_create')
def init_wishes(*args, **kwargs):
    # Read ./data/groups.csv to populate default data
    with open("./data/groups.csv", "r") as f:
        csvreader = csv.reader(f)
        # Skip headers on first line
        next(csvreader)
        for row in csvreader:
            group = Groups(
                name=row[0],
                super_group=True if row[2] == "TRUE" else False,
            )
            group.set_password(row[1])
            group.save()

@event.listens_for(Users.__table__, 'after_create')
def init_wishes(*args, **kwargs):
    # Read ./data/users.csv to populate default data
    with open("./data/users.csv", "r") as f:
        csvreader = csv.reader(f)
        # Skip headers on first line
        next(csvreader)
        for row in csvreader:
            group = Groups.query.filter_by(name=row[2]).first()
            if group is None:
                print(f"GROUP {row[2]} NOT FOUND! SKIPPING")
                continue
            user = Users(
                first_name=row[0],
                last_name=row[1],
                group_id=group.id
            )
            user.save()

# Association table for n to n relationship between Wishes and Groups
wishes_groups = db.Table(
    'wishes_groups',
    db.Model.metadata,
    db.Column('wish_id', db.Integer, db.ForeignKey('wishes.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), primary_key=True)
)


class JWTTokenBlocklist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    jwt_token = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False)

    def __repr__(self):
        return f"Expired Token: {self.jwt_token}"

    def save(self):
        db.session.add(self)
        db.session.commit()
