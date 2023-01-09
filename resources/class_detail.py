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

from functions_for_recipe import recipe_detail_query
from functions_for_users import get_external_id, get_refresh_token


class ClassResource(Resource) :
    
    def get(self, recipe_id) : 
        # 요청한 레시피에 대한 상세정보 리턴하는 api

        start_time = time.time()
        params = request.args.to_dict()
        # 파라미터에서 external_type 가져오기
        # external_type = request.args.get('external_type')


        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)
            # 2. 해당 테이블, recipe 테이블에서 select
            query = ''' select c3.*, cg.name as category_name
                        from (select c1.* ,  ifnull(count(cph.created_at), 0) as participants
                        from 
                        (select * 
                        from class
                        where id = 6
                        ) as c1
                        left join class_purchase_history as cph
                        on c1.id = cph.class_id) as c3
                        left join category as cg
                        on c3.category = cg.id; '''
            record = (recipe_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 0
            for record in record_list:
                
                recipe = {"id": record['id'],
                            "header_img":record['title'],
                            "header_title": record['mainSrc'],
                            "header_desc": record['intro'],
                            "price": record['created_at'].isoformat(),     
                            "time_required": record['updated_at'].isoformat(),
                            "date": [record['c_type'],record['c_ctx'],record['c_ind']],
                            "details":  [record['c_s'],record['c_time'],record['c_level']]
                            }
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
            query = recipe_detail_query["recipe_ingredient"]
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
                        ingredients_list.append({ "title": bundle , "contents": contents_list})
        

                        # bundle, contents_list 재정의 후 재료 저장
                        bundle = record["bundle"]
                        contents_list = []
                        contents_list.append([record["name"], record["amount"]])                
                i = i +1
            # 마지막으로 저장된 재료들도 리스트에 넣어주자.
            ingredients_list.append({ "title": bundle , "contents": contents_list})
            # 리턴할 딕셔너리에 넣어주자.
            recipe["ingredients"] = ingredients_list

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR


        try :
            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query["step"]
            record = (recipe_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()

            recipe["steps"] = record_list
            
        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR       
        

        try :
            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query["like_view"]
            record = (recipe_id, recipe_id, recipe_id, recipe_id)
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()

            print(record_list)


            recipe["view"]= record_list[0]["views"]
            recipe["like"]= record_list[0]["like_cnt"]


        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  



        # 유저가 로그인을 했다면 ... 좋아요 여부 리턴
        try :            
            if "external_type" in params:
                # 파라미터에서 external_type 가져오기
                external_type = request.args.get('external_type')
                token =  request.headers.get('Token') 

                id_result = get_external_id(external_type, token)

                if id_result["status"] == 200 :
                    external_id = id_result["external_id"]

                else :
                    # 나중에 통합한 토큰 재발급 함수 추가
                    print("토큰 만료")

                try :
                    query = recipe_detail_query["get_user_id"]
                    record = (external_id, )
                    cursor.execute(query, record)
                    # select 문은 아래 내용이 필요하다.
                    # 커서로 부터 실행한 결과 전부를 받아와라.
                    record_list = cursor.fetchall()
                    user_id = record_list[0]["user_id"]
                except Error as e :
                    # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                    print('Error while connecting to MySQL', e)
                    return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  


                # 2. 해당 테이블, recipe 테이블에서 select
                query = recipe_detail_query["is_liked"]
                record = (recipe_id, user_id)
                cursor.execute(query, record)
                # select 문은 아래 내용이 필요하다.
                # 커서로 부터 실행한 결과 전부를 받아와라.
                record_list = cursor.fetchall()
                
                if len(record_list) == 1 :
                    recipe["isLiked"]= True
                    
                else :
                    recipe["isLiked"]= False


            else :
                print("로그인 하지 않은 대상이 레시피에 접속")

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  

        
        # 조회수 올리자...
        try :
            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query["add_view"]
            if "external_type" in params :
              record = (user_id, recipe_id)
            else :
              record = (14, recipe_id)
            cursor.execute(query, record)
            connection.commit()
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

            print("---{}s seconds---".format(str(time.time()-start_time)))

        return {'status' : 200, 'recipeInfo' : recipe }, HTTPStatus.OK



    