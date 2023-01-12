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


from functions_for_recipe import recipe_list_map, recipe_detail_query, get_category_query
from functions_for_users import get_external_id, get_refresh_token


# 메인 페이지의 베스트 레시피의 경우 
# 필요 리턴 값 : 레시피 테이블 전체 + 유저정보 + 좋아요 개수 + 조회수
# 정렬 기준 : 좋아요 개수
# best_not_enough 의 경우 좋아요가 있는 레시피의 개수가 10개 미만일 때 작동



# 레시피 리스트를 불러오는 함수 (옵션으로 검색이나 페이징 , 처리, 추천순 등 처리)

class RescipeListResource(Resource) :
    
    def get(self) : 
        # 파라미터 딕셔너리 형태로 가져오기
        params = request.args.to_dict()
        # 현재 파라미터로 고려중인 값 : 카테고리 종류("전체, 반찬 등"),정렬방식(좋아요, 최신, 조회순),검색어(선택),offset,limit
        # list_type = params["list_type"]
        category_id_list = []

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

    def post(self) :

        # 1. 요소가 다 있는지 체크 , 없으면 return 


        # 2. 클라이언트로 부터 데이터 받기
        data = request.get_json()

        try :       
            # 3. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # 4. 유저 인증 과정 거쳐서 유저 id 겟
            # 헤더에서 AuthType 가져오기
            AuthType = request.headers.get("AuthType")

            token =  request.headers.get('Authorization') 
            id_result = get_external_id(AuthType, token)

            if id_result["status"] == 200 :
                    external_id = id_result["external_id"]

            else :
                # 나중에 통합한 토큰 재발급 함수 추가
                if AuthType == "naver" :
                    refresh_token = request.cookies.get('refresh_token')
                    token = get_refresh_token(AuthType, refresh_token )
                    #  다시한번 유저 인증 과정 거쳐서 유저 id 겟 시도
                    id_result = get_external_id(AuthType, token)
                    if id_result["status"] == 200 :
                        external_id = id_result["external_id"]

                    else :
                        return {"status" : 500 , 'message' : "access token 발급에 문제 발생"}


                elif AuthType == "google" :
                     {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}

                print("토큰 만료")
        
            query = recipe_detail_query["get_user_id"]
            record = (external_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            user_id = record_list[0]["id"]

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
                        print(content)      
                        print(content[0])            
                        query = recipe_detail_query["get_ingredient_id"]
                        record = (content[0], )
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
                            record = (content[0], )
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
                            record = (recipe_id,content_id, content[1], bundle_id )
                            cursor.execute(query, record)
                            # select 문은 아래 내용이 필요하다.
                            # 커서로 부터 실행한 결과 전부를 받아와라.
                            connection.commit()
                                                
                    except Error as e :
                        # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR       
                    

                    

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
