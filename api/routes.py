# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from cgitb import reset
from datetime import datetime, timezone, timedelta

from functools import wraps
import json

from flask import request
from flask_restx import Api, Resource, fields

import jwt

from .models import AttendanceStatus, DietaryRestrictions, RegistrationStatus, db, Users, Groups, Wishes, JWTTokenBlocklist, wishes_groups, PaymentInfo
from .config import BaseConfig

rest_api = Api(version="1.0", title="Saamb API", doc=False)


"""
    Flask-Restx models for api request and response data
"""


login_model = rest_api.model('LoginModel', {
    "name": fields.String(required=True, min_length=4, max_length=64),
    "password": fields.String(required=True, min_length=4, max_length=20)
})

user_edit_model = rest_api.model('UserEditModel', {
    "user_id": fields.Integer(required=True),
    "firstName": fields.String(required=False, min_length=2, max_length=32),
    "lastName": fields.String(required=False, min_length=2, max_length=32),
    "registerationStatus": fields.String(required=False, min_length=0, max_length=32),
    "attendanceStatus": fields.String(required=False, min_length=0, max_length=32),
    "dietaryRestrictions": fields.String(required=False, min_length=0, max_length=32),
    "dietaryInfo": fields.String(required=False, min_length=0, max_length=512),
    "songRequest": fields.String(required=False, min_length=0, max_length=512),
    "groupId": fields.Integer(required=False),
    "camping": fields.Boolean(required=False),
    "brunch": fields.Boolean(required=False),
})

user_add_model = rest_api.model('UserAddModel', {
    "firstName": fields.String(required=True, min_length=2, max_length=32),
    "lastName": fields.String(required=True, min_length=2, max_length=32),
    "group_id": fields.Integer(required=True)
})

group_add_model = rest_api.model('GroupAddModel', {
    "name": fields.String(required=True, min_length=2, max_length=32),
    "password": fields.String(required=True, min_length=10, max_length=20),
    "superGroup": fields.Boolean(required=False),
    "members_id": fields.List(fields.Integer, required=False)
})

group_edit_model = rest_api.model('GroupEditModel', {
    "group_id": fields.Integer(required=True),
    "name": fields.String(required=True, min_length=2, max_length=32),
    "password": fields.String(required=True, min_length=10, max_length=20),
    "superGroup": fields.Boolean(required=False),
    "members_id": fields.List(fields.Integer, required=False)
})

group_delete_model = rest_api.model('GroupDeleteModel', {
    "group_id": fields.Integer(required=True)
})

user_delete_model = rest_api.model('UserDeleteModel', {
    "user_id": fields.Integer(required=True)
})

group_get_users_model = rest_api.model('GroupGetUsersModel', {
    "group_id": fields.Integer(required=True)
})

user_get_model = rest_api.model('UserGetModel', {
    "user_id": fields.Integer(required=True)
})

self_edit_model = rest_api.model('SelfEditModel', {
    "user_id": fields.Integer(required=True),
    "registerationStatus": fields.String(required=False, min_length=0, max_length=32),
    "attendanceStatus": fields.String(required=False, min_length=0, max_length=32),
    "dietaryRestrictions": fields.String(required=False, min_length=0, max_length=32),
    "dietaryInfo": fields.String(required=False, min_length=0, max_length=512),
    "songRequest": fields.String(required=False, min_length=0, max_length=512)
})

"""
    Flask-Restx models for api request and response data
"""

"""
   Helper function for JWT token required
"""

def admin_only(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if "authorization" in request.headers:
            token = request.headers["authorization"]
        if not token:
            return {"success": False, "msg": "Valid JWT token is missing"}, 400
        try:
            data = jwt.decode(token, BaseConfig.SECRET_KEY, algorithms=["HS256"])
            current_group = Groups.get_by_name(data["name"])
            if not current_group.super_group:
                return {"success": False, "msg": "Token is invalid"}, 400
        except:
            return {"success": False, "msg": "Token is invalid"}, 400
        return f(*args, **kwargs)
    return decorator

def token_required(f):

    @wraps(f)
    def decorator(*args, **kwargs):

        token = None

        if "authorization" in request.headers:
            token = request.headers["authorization"]

        if not token:
            return {"success": False, "msg": "Valid JWT token is missing"}, 400

        try:
            data = jwt.decode(token, BaseConfig.SECRET_KEY, algorithms=["HS256"])
            # print("JWT token decoded successfully")
            current_group = Groups.get_by_name(data["name"])

            if not current_group:
                return {"success": False,
                        "msg": "Sorry. Wrong auth token. This user does not exist."}, 400

            token_expired = db.session.query(JWTTokenBlocklist.id).filter_by(jwt_token=token).scalar()

            if token_expired is not None:
                return {"success": False, "msg": "Token revoked."}, 400

            if not current_group.check_jwt_auth_active():
                return {"success": False, "msg": "Token expired."}, 400

        except Exception as e:
            print (e.__class__.__name__)
            return {"success": False, "msg": "Token is invalid", "class": e.__class__.__name__}, 400

        return f(current_group, *args, **kwargs)

    return decorator


"""
    Flask-Restx routes
"""

############## GROUPS #################
@rest_api.route('/api/groups')
class GroupsEP(Resource):

    @token_required
    def get(current_group, self):
        """Get own group."""
        return {"success": True,
                "group": current_group.toDICT()}, 200

    @admin_only
    @rest_api.expect(group_add_model, validate=True)
    def post(self):
        """Create a new group."""
        req_data = request.get_json()

        _name = req_data.get("name").lower()
        _password = req_data.get("password")
        if "super_group" in req_data:
            _super_group = req_data.get("superGroup")
        else:
            _super_group = False
        if "members_ids" in req_data:
            _members = req_data.get("members_ids")
        else:
            _members = None

        group_exists = Groups.get_by_name(_name)
        if group_exists is not None:
            return {"success": False,
                    "msg": "Group name already taken"}, 400

        new_group = Groups(name=_name, super_group=_super_group)

        new_group.set_password(_password)
        if _members is not None:
            users_to_update = []
            for user_id in _members:
                user = Users.get_by_id(user_id)
                if user is None:
                    return {"success": False,
                            "msg": "User does not exist"}, 400
                user.group_id = new_group.id
                users_to_update.append(user)
            for user in users_to_update:
                user.save()
        new_group.save()
        
        return {"success": True,
                "groupID": new_group.id,
                "msg": "The user was successfully registered"}, 200

    @admin_only
    @rest_api.expect(group_edit_model, validate=True)
    def put(self):
        """Update an existing group."""
        req_data = request.get_json()
        _id = req_data.get("group_id")
        _name = req_data.get("name").lower() if "name" in req_data else None
        _password = req_data.get("password") if "password" in req_data else None
        _superGroup = req_data.get("superGroup") if "superGroup" in req_data else None
        _members = req_data.get("members_id") if "members_id" in req_data else None

        group = Groups.get_by_id(_id)
        if group is None:
            return {"success": False,
                    "msg": "Group does not exist"}, 400
        if _name:
            if Groups.get_by_name(_name) is not None:
                return {"success": False,
                        "msg": "Group name already taken"}, 400
            group.name = _name
        if _superGroup:
            group.super_group = _superGroup
        if _password:
            group.set_password(_password)
        if _members is not None:
            users_to_update = []
            for user_id in _members:
                user = Users.get_by_id(user_id)
                if user is None:
                    return {"success": False,
                            "msg": "User does not exist"}, 400
                user.group_id = group.id
                users_to_update.append(user)
            for user in users_to_update:
                user.save()
        group.save()
        return {"success": True,
                "groupID": group.id,
                "msg": "The group was successfully updated"}, 200
    
    @admin_only
    @rest_api.expect(group_delete_model, validate=True)
    def delete(self):
        """Delete a group."""
        req_data = request.get_json()
        _id = req_data.get("group_id")

        group = Groups.get_by_id(_id)
        if group is None:
            return {"success": False,
                    "msg": "Group does not exist"}, 400
        group.delete()
        return {"success": True,
                "msg": "The group was successfully deleted"}, 200

############## USERS #################
@rest_api.route('/api/users')
class UsersEP(Resource):

    @rest_api.expect(user_get_model, validate=True)
    @token_required
    def get(current_group, self):

        req_data = request.get_json()

        _user_id = req_data.get("userID")

        user = Users.get_by_id(_user_id)
        if user.group_id != current_group.id and not current_group.super_group:
            return {"success": False,
                    "msg": "Unauthorized"}, 400
        if not user:
            return {"success": False,
                    "msg": "User does not exist"}, 400

        return {"success": True,
                "user": user.toJSON()}, 200

    @admin_only
    @rest_api.expect(user_add_model, validate=True)
    def post(self):
        """Create a User."""
        req_data = request.get_json()

        _first_name = req_data.get("firstName")
        _last_name = req_data.get("lastName")
        _group_id = req_data.get("group_id")
        group = Groups.get_by_id(_group_id)
        if group is None:
            return {"success": False,
                    "msg": "Group does not exist"}, 400
        user = Users.get_by_name(first_name=_first_name, last_name=_last_name)
        if user is not None:
            return {"success": False,
                    "msg": "User name already taken"}, 400

        user = Users(first_name=_first_name, last_name=_last_name, group_id=_group_id)
        user.save()
        return {"success": True,
                "userID": user.id,
                "msg": "The user was successfully registered"}, 200

    @token_required
    @rest_api.expect(user_edit_model, validate=True)
    def put(current_group, self):
        """Update a User."""
        req_data = request.get_json()
        _id = req_data.get("user_id")
        _firstName = req_data.get("firstName") if "firstName" in req_data else None
        _lastName = req_data.get("lastName") if "lastName" in req_data else None
        _registration_status = req_data.get("registerationStatus").lower() if "registerationStatus" in req_data else None
        _attendance_status = req_data.get("attendanceStatus").lower() if "attendanceStatus" in req_data else None
        _dietary_restrictions = req_data.get("dietaryRestrictions").lower() if "dietaryRestrictions" in req_data else None
        _dietary_info = req_data.get("dietaryInfo") if "dietaryInfo" in req_data else None
        _song_request = req_data.get("songRequest") if "songRequest" in req_data else None
        _group_id = req_data.get("group_id") if "group_id" in req_data else None
        _camping = req_data.get("camping") if "camping" in req_data else None
        _brunch = req_data.get("brunch") if "brunch" in req_data else None

        user = Users.get_by_id(_id)
        if user is None:
            return {"success": False,
                    "msg": "User does not exist"}, 400
        if user.group_id != current_group.id and not current_group.super_group:
            return {"success": False,
                    "msg": "Not authorized"}, 400
        if _firstName:
            user.first_name = _firstName
        if _lastName:
            user.last_name = _lastName
        if _registration_status:
            match(_registration_status):
                case "registered":
                    user.registration_status = RegistrationStatus.REGISTERED
                case "not registered":
                    user.registration_status = RegistrationStatus.NOT_REGISTERED
        if _attendance_status:
            match(_attendance_status):
                case "attending":
                    user.attendance_status = AttendanceStatus.ATTENDING
                case "not attending":
                    user.attendance_status = AttendanceStatus.NOT_ATTENDING
                case "unknown":
                    user.attendance_status = AttendanceStatus.UNKNOWN
        if _dietary_restrictions:
            match(_dietary_restrictions):
                case "vegetarian":
                    user.dietary_restrictions = DietaryRestrictions.VEGETARIAN
                case "vegan":
                    user.dietary_restrictions = DietaryRestrictions.VEGAN
                case "none":
                    user.dietary_restrictions = DietaryRestrictions.NONE
        if _dietary_info:
            user.dietary_info = _dietary_info
        if _song_request:
            user.song_request = _song_request
        if _group_id:
            if Groups.get_by_id(_group_id) is None:
                return {"success": False,
                        "msg": "Group does not exist"}, 400
            user.group_id = _group_id
        if _camping is not None:
            user.camping = _camping
        if _brunch is not None:
            user.brunch = _brunch
        user.save()
        return {"success": True,
                "msg": "The user was successfully updated"}, 200

    @admin_only
    @rest_api.expect(user_delete_model, validate=True)
    def delete(self):
        """Delete a User."""
        req_data = request.get_json()
        _id = req_data.get("user_id")
        user = Users.get_by_id(_id)
        if user is None:
            return {"success": False,
                    "msg": "User does not exist"}, 400
        user.delete()
        return {"success": True,
                "msg": "The user was successfully deleted"}, 200

############ WISHES ###############
create_wish_model = rest_api.model('CreateWishModel', {
    "title": fields.String(required=True, min_length=0, max_length=64),
    "price": fields.Integer(required=True),
    "description": fields.String(required=False, min_length=0, max_length=512),
    "picture_url": fields.String(required=False, min_length=0, max_length=100),
    "quantity": fields.Integer(required=False)
})
update_wish_model = rest_api.model('CreateWishModel', {
    "wish_id": fields.Integer(required=True),
    "title": fields.String(required=False, min_length=0, max_length=64),
    "price": fields.Integer(required=False),
    "description": fields.String(required=False, min_length=0, max_length=512),
    "picture_url": fields.String(required=False, min_length=0, max_length=100),
    "quantity": fields.Integer(required=False)
})
delete_wish_model = rest_api.model('DeleteWishModel', {
    "wish_id": fields.Integer(required=True)
})
# TODO that's nearly the same model as for deleting a wish, generic models yo?
purchase_wish_model = rest_api.model('PurchaseWishModel', {
    "wish_id": fields.Integer(required=True),
    "is_purchasing": fields.Boolean(required=True)
})
@rest_api.route('/api/wishlist')
class WishList(Resource):
    """WishList endpoints."""
    @admin_only
    @rest_api.expect(create_wish_model, validate=True)
    def post(self):
        """Create new Wish."""
        req_data = request.get_json()
        _title = req_data.get("title")
        _price = req_data.get("price")
        _description = req_data.get("description") if "description" in req_data else None
        _picture_url = req_data.get("picture_url") if "picture_url" in req_data else None
        _quantity = req_data.get("quantity") if "quantity" in req_data else 1
        wish = Wishes(
            title=_title,
            price=_price,
            description=_description,
            picture_url=_picture_url,
            quantity=_quantity
        )
        wish.save()
        return {"success": True,
                "msg": "The wish was successfully created"}, 200
    
    @admin_only
    @rest_api.expect(update_wish_model, validate=True)
    def put(self):
        """Update a Wish."""
        req_data = request.get_json()
        _id = req_data.get("wish_id")
        _title = req_data.get("title") if "title" in req_data else None
        _price = req_data.get("price") if "price" in req_data else None
        _description = req_data.get("description") if "description" in req_data else None
        _picture_url = req_data.get("picture_url") if "picture_url" in req_data else None
        _quantity = req_data.get("quantity") if "quantity" in req_data else None
        wish = Wishes.get_by_id(_id)
        if wish is None:
            return {"success": False,
                    "msg": "Wish does not exist"}, 400
        if _title:
            wish.title = _title
        if _price:
            wish.price = _price
        if _description:
            wish.description = _description
        if _picture_url:
            wish.picture_url = _picture_url
        if _quantity:
            wish.quantity = _quantity
        wish.save()
        return {"success": True,
                "msg": "The wish was successfully updated"}, 200

    @admin_only
    @rest_api.expect(delete_wish_model, validate=True)
    def delete(self):
        """Delete a Wish."""
        req_data = request.get_json()
        _id = req_data.get("wish_id")
        wish = Wishes.get_by_id(_id)
        if wish is None:
            return {"success": False,
                    "msg": "Wish does not exist"}, 400
        wish.delete()
        return {"success": True,
                "msg": "The wish was successfully deleted"}, 200

    
    @token_required
    def get(self, _):
        """Get all wishes."""
        wishes = Wishes.get_all()
        return {"success": True,
                "wishes": [
            # TODO to add the quantity of items left ```wish.toDICT().update({"quantity_left": wish.quantity - len(wish.groups)})``` or smth like that you feel me!
            # Border case when a group takes more than 1 Wish from the same category. Think about adding a quantity field in the association table mdr lolilol
                wish.toDICT() for wish in wishes
            ]}, 200
    
    @token_required
    @rest_api.expect(purchase_wish_model, validate=True)
    def patch(current_group, self):
        """Purchase/Unpurchase a Wish."""
        req_data = request.get_json()
        _id = req_data.get("wish_id")
        _is_purchasing = req_data.get("is_purchasing")
        _quantity = req_data.get("quantity")
        wish = Wishes.get_by_id(_id)
        if wish is None:
            return {"success": False,
                    "msg": "Wish does not exist"}, 404
        # TODO check toussa wesh
        if not _is_purchasing:
            if current_group in wish.groups:
                wish.groups.remove(current_group)
                wish.save()
                return {"success": True,
                        "msg": "The wish was successfully unpurchased"}, 200
            else:
                return {"success": False,
                        "msg": "You cannot unpurchase a wish you did not purchase"}, 400
        else:
            if current_group in wish.groups: # Adding more item to already present relationship
                wish_group = wishes_groups.get_by_ids(wish_id=wish.id, group_id=current_group.id)
                if _quantity <= wish.quantity:
                    wish_group.quantity = _quantity
                else:
                    return {"success": False,
                            "msg": "You cannot purchase more than the quantity of the wish"}, 400
            else: # Does not have item in cart yet
                if _quantity <= wish.get_quantity_left():
                    wg = wishes_groups(wish_id=wish.id, group_id=current_group.id, quantity=_quantity)    
                    db.session.add(wg)
                else:
                    return {"success": False,
                            "msg": "You cannot purchase more than the quantity of the wish"}, 400
            wish.save()
            return {"success": True,
                    "msg": "The wish was successfully purchased"}, 200

############ SINGLE METHODS ###############
@rest_api.route('/api/groups/login')
class Login(Resource):
    """
       Login user by taking 'login_model' input and return JWT token
    """

    @rest_api.expect(login_model, validate=True)
    def post(self):

        req_data = request.get_json()

        _name = req_data.get("name").lower()
        _password = req_data.get("password")

        group_exists = Groups.get_by_name(_name)

        if not group_exists:
            return {"success": False,
                    "msg": "This group name does not exist."}, 400

        if not group_exists.check_password(_password):
            return {"success": False,
                    "msg": "Wrong credentials."}, 400

        # create access token uwing JWT
        token = jwt.encode({'name': _name, 'exp': datetime.utcnow() + timedelta(minutes=30)}, BaseConfig.SECRET_KEY, algorithm='HS256')

        group_exists.set_jwt_auth_active(True)
        group_exists.save()
        
        users = Users.get_by_group_id(group_exists.id)
        json_users = [u.toJSON() for u in users]

        return {"success": True,
                "token": token,
                "group": group_exists.toJSON(),
                "users": json_users
                }, 200

@rest_api.route('/api/groups/getAllInfo')
class GetAllInfo(Resource):
    """Get all info about groups."""
    @admin_only
    def get(self):
        groups = Groups.get_all()
        response = {}
        for g in groups:
            response[g.name] = [member.toJSON() for member in g.users]

        return {"success": True,
                    "data": json.dumps(response)}, 200

@rest_api.route('/api/groups/getUsers')
class GetGroupUsers(Resource):
    """
       Get all users in a group using "group_get_users_model" input
    """
    
    @rest_api.expect(group_get_users_model, validate=True)
    @token_required
    def get(current_group, self):

        req_data = request.get_json()

        _group = req_data.get("group")

        group_exists = Groups.get_by_id(_group)
        if not group_exists:
            return {"success": False,
                    "msg": "Group does not exist"}, 400

        users = Users.get_by_group(_group)

        return {"success": True,
                "users": users}, 200

@rest_api.route('/api/groups/getAll')
class GetGroups(Resource):
    """
       Get all groups
    """

    @token_required
    def get(current_group, _):

        groups = Groups.get_all()
        json_groups = [g.toJSON() for g in groups]

        return {"success": True,
                "groups": json_groups}, 200

pay_model = rest_api.model('Pay', {
    'paid': fields.Boolean(required=True, description='True if paid, False if not paid'),
})

@rest_api.route('/api/pay')
class Pay(Resource):
    @token_required
    @rest_api.expect(pay_model, validate=True)
    def patch(current_group, self):
        """Pay for the group."""
        req_data = request.get_json()
        _paid = req_data.get("paid")
        current_group.paid = _paid
        current_group.save()
        return {"success": True,
                "msg": "The group was successfully paid"}, 200

@rest_api.route('/api/payment-info')
class GetPaymentInfo(Resource):
    """
    Get the first entry of the PaymentInfo table.
    """

    @token_required
    def get(current_group, _):
        payment_info = PaymentInfo.query.first()

        if payment_info:
            response = {
                "success": True,
                "payment_info": {
                    "id": payment_info.id,
                    "name": payment_info.name,
                    "address": payment_info.address,
                    "iban": payment_info.iban,
                    "swift": payment_info.swift,
                    "bank": payment_info.bank,
                }
            }
            return response, 200
        else:
            return {"success": False, "msg": "No payment info available"}, 404

@rest_api.route('/api/users/getAll')
class GetAllUsers(Resource):
    """
       Get all users
    """

    @token_required
    def get(current_user, _):

        users = Users.get_all()
        json_users = [u.toJSON() for u in users]

        return {"success": True,
                "users": json_users}, 200