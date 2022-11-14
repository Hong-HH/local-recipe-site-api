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

from functions_for_recipe import recipe_detail_query


class RescipeResource(Resource) :
    
    def get(self, recipe_id) : 
        # 요청한 레시피에 대한 상세정보 리턴하는 api

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)
            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query("recipe_user_info")
            record = (recipe_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 0
            for record in record_list:
                recipe = {"recipe_id": record['id'],
                            "title":record['title'],
                            "mainSrc": record['mainSrc'],
                            "intro": record['intro'],
                            "writer":{ "id" : record['user_id'],"nickname," : record['nickname'], "profile_img" : record['profile_img']},
                            "public": record['public'],
                            "created_at": record['created_at'].isoformat(),     
                            "updated_at": record['updated_at'].isoformat(),
                            "category": [record['c_type'],record['c_ctx'],record['c_ind']],
                            "recipeInfo":  [record['c_s'],record['c_time'],record['c_level']]}
                print("i의 값은" + str(i))
                i = i +1

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        
        
        try :
            ingredients_list = []     
            bundle = ""
            contents_list =  []

            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query("recipe_ingredient")
            record = (recipe_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 0
            for record in record_list:
                if i == 0 :
                    bundle = record["bundle"]
                    contents_list.append([record["name"], record["amount"]])
                    
                else :
                    if record["bundle"] == bundle:
                        contents_list.append([record["name"], record["amount"]])

                    else : 
                        # bundle 변수의 값이  record["bundle"]  와 다르다면 ingredients_list 에 기존 값들을 저장해준 후 
                        ingredients_list.append({ "name": bundle , "contents": contents_list})
                        # bundle 재정의 후 재료 저장

                        bundle = record["bundle"]
                        contents_list.append([record["name"], record["amount"]])                
                i = i +1
            # 마지막으로 저장된 재료들도 리스트에 넣어주자.
            ingredients_list.append({ "name": bundle , "contents": contents_list})
            # 리턴할 딕셔너리에 넣어주자.
            recipe["ingredients"] = ingredients_list

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR


        try :
            step_list = []

            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query("step")
            record = (recipe_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 0
            for record in record_list:          
                step_list.append([record["description"], record["img"]])
                i = i +1

            recipe["steps"] = step_list
            
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
        return {'status' : 200, 'recipeInfo' : recipe }, HTTPStatus.OK