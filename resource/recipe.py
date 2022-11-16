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


class RescipeResource(Resource) :
    
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
            query = recipe_detail_query["recipe_user_info"]
            record = (recipe_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 0
            for record in record_list:
                if record["result_img"] :
                    result_img = record["result_img"]
                else :
                    result_img = record['mainSrc']

                recipe = {"recipeId": record['id'],
                            "title":record['title'],
                            "mainSrc": record['mainSrc'],
                            "intro": record['intro'],
                            "writer":{ "id" : record['user_id'],"nickname," : record['nickname'], "profile_img" : record['profile_img'], "profile_desc" :record['profile_desc'] },
                            "createdAt": record['created_at'].isoformat(),     
                            "updatedAt": record['updated_at'].isoformat(),
                            "category": [record['c_type'],record['c_ctx'],record['c_ind']],
                            "details":  [record['c_s'],record['c_time'],record['c_level']],
                            "resultSrc" : result_img
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



    def post(self) :

        # 1. 요소가 다 있는지 체크 , 없으면 return 


        # 2. 클라이언트로 부터 데이터 받기
        data = request.get_json()

        try :       
            # 3. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # 4. 유저 인증 과정 거쳐서 유저 id 겟
            external_type = request.args.get('external_type')
            token =  request.headers.get('Token') 
            id_result = get_external_id(external_type, token)

            if id_result["status"] == 200 :
                    external_id = id_result["external_id"]

            else :
                # 나중에 통합한 토큰 재발급 함수 추가
                if external_type == "naver" :
                    refresh_token = request.cookies.get('refresh_token')
                    token = get_refresh_token(external_type, refresh_token )
                    #  다시한번 유저 인증 과정 거쳐서 유저 id 겟 시도
                    id_result = get_external_id(external_type, token)
                    if id_result["status"] == 200 :
                        external_id = id_result["external_id"]

                    else :
                        return {"status" : 500 , 'message' : "access token 발급에 문제 발생"}


                elif external_type == "google" :
                     {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}

                print("토큰 만료")
        
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


        try :
            # 5. 카테고리 아이디로 변환 
            query = recipe_detail_query["get_category_id"]
            c1 = data["category"]
            c2 = data["details"]
                        
            record = (c1[0], c1[1], c1[2], c2[0], c2[1], c2[2])
            cursor.execute(query, record)

            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            c_list = []
            i = 0
            for record in record_list:
                c_list.append(record["id"])
                i = i + 1

            print(c_list)

            #  6. 필수가 아닌 값, 없으면 NULL 로 저장
            if "resultSrc" in data :
                resultSrc = data["resultSrc"]
            else :
                resultSrc = None
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  


        try :
            # 2. 해당 테이블, recipe 테이블에서 select
            query = recipe_detail_query["add_recipe"]
            # 아래 것들 중 result_img 는 필수가 아님
            # insert into recipe
            # (user_id,public, category_type, category_context, category_ingredients, header_img, header_title, header_desc,
            #  servings, time, level, result_img)
            # values
            # (2, 1, 1, 13, 21, "img_url", "배추김치", "아삭아삭 배추김치", 35, 44, 49, "result_img_url");

            record = (user_id, data["public"],c_list[0],c_list[1],c_list[2],data["mainSrc"],data["title"],data["intro"],c_list[3],c_list[4],c_list[5],resultSrc)

            cursor.execute(query, record)
            connection.commit()
            recipe_id = cursor.lastrowid

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  


        try :
            # 2. 재료를 넣어보자
            # 번들네임 리스트 생성
            # 반복문 시작
            # 재료 id 를 찾고
            # 없으면 insert 해주고
            #  select * from ingredient
            # where name = "후추";  
            # 번들에 insert 해주고
            # 번들 id 가져와서
            # 레시피 인그리디언트에 삽입

            ingredients_list = data["ingredients"]
            
            row = 0
            i = 0

            for ingredient in ingredients_list :
                # 먼저 재료 타이틀을 번들에 추가하여 id 를 받는다. 
                try :                        
                    query = recipe_detail_query["get_bundle_id"]
                    record = (ingredient['title'], )
                    cursor.execute(query, record)
                    # select 문은 아래 내용이 필요하다.
                    # 커서로 부터 실행한 결과 전부를 받아와라.
                    connection.commit()
                    bundle_id = cursor.lastrowid

                # 3. 클라이언트에 보낸다. 
                except Error as e :
                    # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                    print('Error while connecting to MySQL', e)
                    return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR       

                # 번들 재료 id를 get 하여 insert 하자.
                for content in ingredient['contents'] :
                    #  ingredient 테이블에서 select 
                    try :                        
                        query = recipe_detail_query["get_ingredient_id"]
                        record = (content[row][0], )
                        cursor.execute(query, record)
                        # select 문은 아래 내용이 필요하다.
                        # 커서로 부터 실행한 결과 전부를 받아와라.
                        record_list = cursor.fetchall()
                       
                    # 3. 클라이언트에 보낸다. 
                    except Error as e :
                        # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR       
                    
                    if len(record_list) == 1 :
                        content_id = record_list[0]["id"]

                    else :
                        # 저장된 재료가 아니므로 ingredient 테이블에 추가
                        try :                        
                            query = recipe_detail_query["insert_get_ingredient_id"]
                            record = (content[row][0], )
                            cursor.execute(query, record)
                            # select 문은 아래 내용이 필요하다.
                            # 커서로 부터 실행한 결과 전부를 받아와라.
                            connection.commit()
                            content_id = cursor.lastrowid

                        # 3. 클라이언트에 보낸다. 
                        except Error as e :
                            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                            print('Error while connecting to MySQL', e)
                            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR       
                    
                    try :                        
                            query = recipe_detail_query["insert_recipe_ingredient"]
                            record = (recipe_id,content_id, content[row][1], bundle_id )
                            cursor.execute(query, record)
                            # select 문은 아래 내용이 필요하다.
                            # 커서로 부터 실행한 결과 전부를 받아와라.
                            connection.commit()
                                                
                    except Error as e :
                        # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR       
                    

                    row = row + 1

                i = i + 1

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  


        # 요리 순서를 저장해보자        
        try :
            i = 0                      
            for step in data["steps"] :  
                order = i+1
                query = '''insert into
                            recipe_step
                            (recipe_id, step, description, img)
                            values
                            (%s, %s, %s, %s);'''
                record = (recipe_id, order ,step[0], step[1])
                cursor.execute(query, record)
                # select 문은 아래 내용이 필요하다.
                # 커서로 부터 실행한 결과 전부를 받아와라.
                connection.commit()

                i= i+1

            # return {'status' : 200 ,'message' : "success"}
                                    
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

        return {'status' : 200 ,'message' : "success"}