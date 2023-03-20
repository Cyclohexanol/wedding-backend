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
    users = db.relationship("Users", backref="group", lazy=True, cascade="all, delete-orphan")
    super_group = db.Column(db.Boolean, default=False, nullable=False)
    wishes = db.relationship("Wishes", secondary="wishes_groups", back_populates="groups", lazy="dynamic")
    paid = db.Column(db.Boolean, default=False, nullable=False)

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
        cls_dict['users'] = [user.toDICT() for user in self.users]
        cart_wishes = [wish.toDICT() for wish in self.wishes]
        for wish in cart_wishes:
            wg = wishes_groups.get_by_ids(wish['_id'], self.id)
            wish['quantity'] = wg.quantity
        cls_dict['cart'] = cart_wishes
        cls_dict['paid'] = self.paid
        cls_dict['superGroup'] = self.super_group

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
    camping = db.Column(db.Boolean, default=False, nullable=False)
    brunch = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"{self.id=}, {self.first_name}, {self.camping}, {self.brunch}"

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

    def delete(self):
        db.session.delete(self)
        db.session.commit()

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
        cls_dict['camping'] = self.camping
        cls_dict['brunch'] = self.brunch

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
    def get_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def get_quantity_left(self):
        quantityTmp = self.quantity
        wish_group = wishes_groups.query.filter_by(wish_id=self.id).all()
        if len(wish_group) > 0:
            for rel in wish_group:
                quantityTmp -= rel.quantity
        return quantityTmp if quantityTmp > 0 else 0 # TODO check for concurrent access

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
        cls_dict['quantity'] = self.get_quantity_left()
        cls_dict['totalQuantity'] = self.quantity
        cls_dict['price'] = self.price
        # cls_dict['groups'] = [group.toDICT() for group in self.groups] TODO no need for now, taking from group -> cart

        return cls_dict

    def toJSON(self):

        return self.toDICT()

class PaymentInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    address = db.Column(db.String(512), nullable=False)
    iban = db.Column(db.String(32), nullable=False)
    swift = db.Column(db.String(32), nullable=False)
    bank = db.Column(db.String(64), nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

@event.listens_for(PaymentInfo.__table__, 'after_create')
def init_payment_info(*args, **kwargs):
    # Read ./data/info.csv to populate default data
    with open("./data/info.csv", "r") as f:
        csvreader = csv.reader(f)
        # Skip headers on first line
        next(csvreader)
        for row in csvreader:
            pi = PaymentInfo(
                name=row[0],
                address=row[1],
                iban=row[2],
                swift=row[3],
                bank=row[4]
            )
            pi.save()


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
def init_groups(*args, **kwargs):
    # Read ./data/groups.csv to populate default data
    with open("./data/groups.csv", "r") as f:
        csvreader = csv.reader(f)
        # Skip headers on first line
        next(csvreader)
        for row in csvreader:
            group = Groups(
                name=row[0].lower(),
                super_group=True if row[2] == "TRUE" else False,
            )
            group.set_password(row[1])
            group.save()

@event.listens_for(Users.__table__, 'after_create')
def init_users(*args, **kwargs):
    # Read ./data/users.csv to populate default data
    with open("./data/users.csv", "r") as f:
        csvreader = csv.reader(f)
        # Skip headers on first line
        next(csvreader)
        for row in csvreader:
            group = Groups.query.filter_by(name=row[2].lower()).first()
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
class wishes_groups(db.Model):
    wish_id = db.Column(db.Integer, db.ForeignKey('wishes.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)

    # wish = db.relationship("Wishes", back_populates="groups")
    # group = db.relationship("Groups", back_populates="wishes")

    @classmethod
    def get_by_ids(cls, wish_id, group_id):
        records = cls.query.filter_by(wish_id=wish_id, group_id=group_id)
        if records.count() > 1:
            print("DB ERROR: Multiple records found for wish_id and group_id")
        return records.first()

    def __repr__(self):
        return f"wishes_groups('{self.wish_id}', '{self.group_id}', '{self.quantity}')"
    

    def toDICT(self):
        cls_dict = {}
        cls_dict['wishId'] = self.wish_id
        cls_dict['groupId'] = self.group_id
        cls_dict['quantity'] = self.quantity

        return cls_dict

    def toJSON(self):

        return self.toDICT()

# wishes_groups = db.Table(
#     'wishes_groups',
#     db.Model.metadata,
#     db.Column('wish_id', db.Integer, db.ForeignKey('wishes.id'), primary_key=True),
#     db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), primary_key=True),
#     db.Column('quantity', db.Integer, nullable=False)
# )

class JWTTokenBlocklist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    jwt_token = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False)

    def __repr__(self):
        return f"Expired Token: {self.jwt_token}"

    def save(self):
        db.session.add(self)
        db.session.commit()
