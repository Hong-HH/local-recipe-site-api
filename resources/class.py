from flask import request, json, Response
from flask.json import jsonify
from flask_restful import Resource
from http import HTTPStatus
import requests
import time

from mysql_connection import get_connection
from mysql.connector.errors import Error

from config import Config

from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests as google_requests

from functions_for_recipe import recipe_detail_query, get_category_query
from functions_for_users import get_external_id, get_refresh_token


class ClassResource(Resource) :
    
    def get(self) : 
        # 파라미터 딕셔너리 형태로 가져오기
        params = request.args.to_dict()
        # 현재 파라미터로 고려중인 값 : 카테고리 종류("전체, 반찬 등"),정렬방식(좋아요, 최신, 조회순),검색어(선택),offset,limit
        # list_type = params["list_type"]

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)
            # 2. 해당 테이블, recipe 테이블에서 select
            result_list = get_category_query(params)
            category_id_list = []
            c_list = []
            if result_list is not None :
                query = result_list[0]
                c_list = result_list[1]
                cursor.execute(query)
                # select 문은 아래 내용이 필요하다.
                # 커서로 부터 실행한 결과 전부를 받아와라.
                record_list = cursor.fetchall()
                category_id_list = record_list
                print(category_id_list)
                # [{"id" : },{"id" :}]

        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        try :

            query = recipe_list_map(params, category_id_list, c_list) 
            print(query)
            
            cursor.execute(query)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            print(record_list)
            return_list = []
            i = 0
            for record in record_list:
                # record_list[i]['created_at'] = record['created_at'].isoformat()
                recipe = {"recipe_id": record['id'],
                            "like": record['likes_cnt'],
                            "view": record['views'],
                            "userInfo":[record['profile_img'], record['nickname']],
                            "public": record['public'],
                            "src": record['header_img'],
                            "title":record['header_title'],
                            "created_at": record['created_at'].isoformat()}
                return_list.append(recipe)
                i = i +1

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR
        # finally 는 try에서 에러가 나든 안나든, 무조건 실행하라는 뜻.
        finally : 
            print('finally')
            if connection.is_connected():
                cursor.close()
                connection.close()
                print('MySQL connection is closed')
            else :
                print('connection does not exist')
        return {'status' : 200, 'list' : return_list }, HTTPStatus.OK