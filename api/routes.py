# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from cgitb import reset
from datetime import datetime, timezone, timedelta

from functools import wraps

from flask import request
from flask_restx import Api, Resource, fields

import jwt

from .models import db, Users, Groups, JWTTokenBlocklist
from .config import BaseConfig

rest_api = Api(version="1.0", title="Saamb API")


"""
    Flask-Restx models for api request and response data
"""


login_model = rest_api.model('LoginModel', {"name": fields.String(required=True, min_length=4, max_length=64),
                                            "password": fields.String(required=True, min_length=4, max_length=20)
                                            })

user_edit_model = rest_api.model('UserEditModel', {"user_id": fields.Integer(required=True),
                                                   "first_name": fields.String(required=False, min_length=2, max_length=32),
                                                   "last_name": fields.String(required=False, min_length=2, max_length=32),
                                                   "registerationStatus": fields.String(required=False, min_length=0, max_length=32),
                                                   "attendanceStatus": fields.String(required=False, min_length=0, max_length=32),
                                                   "dietaryRestrictions": fields.String(required=False, min_length=0, max_length=32),
                                                   "dietaryInfo": fields.String(required=False, min_length=0, max_length=512),
                                                   "songRequest": fields.String(required=False, min_length=0, max_length=512)
                                                   })

user_add_model = rest_api.model('UserAddModel', {"first_name": fields.String(required=True, min_length=2, max_length=32),
                                                    "last_name": fields.String(required=True, min_length=2, max_length=32),
                                                    "group_id": fields.Integer(required=True)
                                                    })

group_add_model = rest_api.model('GroupAddModel', {"name": fields.String(required=True, min_length=2, max_length=32),
                                                    "password": fields.String(required=True, min_length=10, max_length=20),
                                                    "super_group": fields.Boolean(required=False)
                                                    })

group_edit_model = rest_api.model('GroupEditModel', {"group_id": fields.Integer(required=True),
                                                    "name": fields.String(required=True, min_length=2, max_length=32),
                                                    "password": fields.String(required=True, min_length=10, max_length=20)
                                                    })

group_delete_model = rest_api.model('GroupDeleteModel', {"group_id": fields.Integer(required=True)
                                                    })

user_delete_model = rest_api.model('UserDeleteModel', {"user_id": fields.Integer(required=True)
                                                    })

group_get_users_model = rest_api.model('GroupGetUsersModel', {"group_id": fields.Integer(required=True)
                                                    })

user_get_model = rest_api.model('UserGetModel', {"user_id": fields.Integer(required=True)
                                                    })

self_edit_model = rest_api.model('SelfEditModel', {"user_id": fields.Integer(required=True),
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
            print (e.message)
			
            return {"success": False, "msg": "Token is invalid", "class": e.__class__.__name__}, 400

        return f(current_group, *args, **kwargs)

    return decorator


"""
    Flask-Restx routes
"""


@rest_api.route('/api/groups/add')
class AddGroup(Resource):
    """
       Creates a new user by taking 'group_add_model' input
    """

    @rest_api.expect(group_add_model, validate=True)
    @token_required
    def post(self):

        req_data = request.get_json()

        _name = req_data.get("name")
        _password = req_data.get("password")

        group_exists = Groups.get_by_name(_name)
        if group_exists:
            return {"success": False,
                    "msg": "Group name already taken"}, 400

        new_group = Groups(name=_name)

        new_group.set_password(_password)
        new_group.save()

        return {"success": True,
                "userID": new_group.id,
                "msg": "The user was successfully registered"}, 200

@rest_api.route('/api/groups/edit')
class EditGroup(Resource):
    """
       Edits a group by taking 'group_edit_model' input
    """

    @rest_api.expect(group_edit_model, validate=True)
    @token_required
    def post(self, current_group):

        req_data = request.get_json()

        _groupID = req_data.get("groupID")
        _name = req_data.get("name")
        _password = req_data.get("password")

        group = Groups.get_by_id(_groupID)
        if not group:
            return {"success": False,
                    "msg": "Group does not exist"}, 400

        group.name = _name
        group.set_password(_password)
        group.save()

        return {"success": True,
                "msg": "The group was successfully edited"}, 200

@rest_api.route('/api/groups/delete')
class DeleteGroup(Resource):
    """
       Deletes a group by taking 'group_delete_model' input
    """

    @rest_api.expect(group_delete_model, validate=True)
    @token_required
    def post(self, current_group):

        req_data = request.get_json()

        _groupID = req_data.get("groupID")

        group = Groups.get_by_id(_groupID)
        if not group:
            return {"success": False,
                    "msg": "Group does not exist"}, 400

        group.delete()

        return {"success": True,
                "msg": "The group was successfully deleted"}, 200


@rest_api.route('/api/groups/login')
class Login(Resource):
    """
       Login user by taking 'login_model' input and return JWT token
    """

    @rest_api.expect(login_model, validate=True)
    def post(self):

        req_data = request.get_json()

        _name = req_data.get("name")
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


@rest_api.route('/api/users/add')
class AddUser(Resource):
    """
       Creates a new user by taking 'user_add_model' input
    """

    @rest_api.expect(user_add_model, validate=True)
    @token_required
    def post(self, current_group):

        req_data = request.get_json()

        _first_name = req_data.get("first_name")
        _last_name = req_data.get("last_name")
        _group = req_data.get("group_id")

        user_exists = Users.get_by_name(_first_name, _last_name)
        if user_exists:
            return {"success": False,
                    "msg": "User already exists"}, 400

        new_user = Users(first_name=_first_name, last_name=_last_name, group_id=_group)
        new_user.save()

        return {"success": True,
                "userID": new_user.id,
                "msg": "The user was successfully registered"}, 200

@rest_api.route('/api/user/edit')
class EditUser(Resource):
    """
       Edit user by taking 'user_edit_model' input
    """

    @rest_api.expect(user_edit_model, validate=True)
    @token_required
    def post(self, current_group):

        req_data = request.get_json()

        _user_id = req_data.get("userID")
        _first_name = req_data.get("first_name")
        _last_name = req_data.get("last_name")
        _registerationStatus = req_data.get("registerationStatus")
        _addendingStatus = req_data.get("addendingStatus")
        _dietaryRestrictions = req_data.get("dietaryRestrictions")
        _dietaryInfo = req_data.get("dietaryInfo")
        _songRequest = req_data.get("songRequest")
        _group = req_data.get("group")

        user_exists = Users.get_by_id(_user_id)
        if not user_exists:
            return {"success": False,
                    "msg": "User does not exist"}, 400

        # Check if user is in group
        if(current_group.id != user_exists.groupId or not current_group.super_group):
            return {"success": False, "msg": "User is not in group"}, 400

        user_exists.first_name = _first_name
        user_exists.last_name = _last_name
        user_exists.registerationStatus = _registerationStatus
        user_exists.addendingStatus = _addendingStatus
        user_exists.dietaryRestrictions = _dietaryRestrictions
        user_exists.dietaryInfo = _dietaryInfo
        user_exists.songRequest = _songRequest
        user_exists.group = _group
        user_exists.save()

        return {"success": True,
                "msg": "The user was successfully edited"}, 200

@rest_api.route('/api/self/register')
class EditSelf(Resource):
    """
        Edit self by taking 'self_edit_model' input
    """
    @rest_api.expect(self_edit_model, validate=True)
    @token_required
    def post(self, current_group):
    
        req_data = request.get_json()
    
        _user_id = req_data.get("userID")
        _registerationStatus = req_data.get("registerationStatus")
        _addendingStatus = req_data.get("addendingStatus")
        _dietaryRestrictions = req_data.get("dietaryRestrictions")
        _dietaryInfo = req_data.get("dietaryInfo")
        _songRequest = req_data.get("songRequest")
    
        user_exists = Users.get_by_id(_user_id)
        if not user_exists:
            return {"success": False,
                    "msg": "User does not exist"}, 400
    
        user_exists.registerationStatus = _registerationStatus
        user_exists.addendingStatus = _addendingStatus
        user_exists.dietaryRestrictions = _dietaryRestrictions
        user_exists.dietaryInfo = _dietaryInfo
        user_exists.songRequest = _songRequest
        user_exists.save()
    
        return {"success": True,
                "msg": "The user was successfully edited"}, 200
   

@rest_api.route('/api/users/delete')
class DeleteUser(Resource):
    """
       Delete user by taking 'user_delete_model' input
    """

    @rest_api.expect(user_delete_model, validate=True)
    @token_required
    def post(self, current_group):

        req_data = request.get_json()

        _user_id = req_data.get("userID")

        user_exists = Users.get_by_id(_user_id)
        if not user_exists:
            return {"success": False,
                    "msg": "User does not exist"}, 400

        user_exists.delete()

        return {"success": True,
                "msg": "The user was successfully deleted"}, 200

@rest_api.route('/api/users/get')
class GetUser(Resource):
    """
       Get user by taking 'user_get_model' input
    """

    @rest_api.expect(user_get_model, validate=True)
    @token_required
    def get(self, current_group):

        req_data = request.get_json()

        _user_id = req_data.get("userID")

        user_exists = Users.get_by_id(_user_id)
        if not user_exists:
            return {"success": False,
                    "msg": "User does not exist"}, 400

        return {"success": True,
                "user": user_exists.toJSON()}, 200

@rest_api.route('/api/groups/getUsers')
class GetGroupUsers(Resource):
    """
       Get all users in a group using "group_get_users_model" input
    """
    
    @rest_api.expect(group_get_users_model, validate=True)
    @token_required
    def get(self, current_group):

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
    def get(self, current_group):

        groups = Groups.get_all()
        json_groups = [g.toJSON() for g in groups]

        return {"success": True,
                "groups": json_groups}, 200