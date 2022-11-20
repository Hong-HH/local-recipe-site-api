from flask import request, json, Response
from flask.json import jsonify
from flask_restful import Resource
from http import HTTPStatus
import requests

from mysql_connection import get_connection
from mysql.connector.errors import Error

from config import Config

from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests as google_requests


from functions_for_users import get_external_id, get_refresh_token
from functions_for_recipe import recipe_list_map, recipe_detail_query, get_categoru_query



class UserRecipeResource(Resource) :

    #  좋아요 추가

    def post(self, recipe_id) : 
        pass

    def delete(self, recipe_id) :
        pass