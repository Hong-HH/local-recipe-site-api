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



class RecipeCommentListResource(Resource) :

    # offset , limit 방식보다
    # 커서 방식
    
    def get(self, recipe_id) : 

        params = request.args.to_dict()
        return_dict = {}

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)


            if "target_id" in params :
                query = '''select r.id, r.user_id, r.recipe_id, r.comment, r.created_at, u.nickname, u.profile_img
                            from 
                            (select *
                            from recipe_comment as rc
                            where recipe_id = %s and id < %s
                            order by  id desc
                            limit ''' +   params["limit"]   + ''') as r
                            left join user as u
                            on r.user_id = u.id;'''
                            
                record = (recipe_id, params["target_id"] )

            else : 
                query = '''select r.id, r.user_id, r.recipe_id, r.comment, r.created_at, u.nickname, u.profile_img
                            from 
                            (select *
                            from recipe_comment as rc
                            where recipe_id = %s
                            order by  id desc
                            limit ''' +   params["limit"]   + ''') as r
                            left join user as u
                            on r.user_id = u.id;'''
                record = (recipe_id,  )

            
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            return_list = []
            i = 0
            for record in record_list:
                return_list.append({
                                    "id": record["id"],
                                    "content": record["comment"],
                                    "createdAt": record["created_at"].isoformat(),
                                    "writer": {
                                        "nickname": record["nickname"],
                                        "profile_img": record["profile_img"]
                                                }
                                    })

                i = i + 1

            return_dict["rows"] = return_list



        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        try :
            if "target_id" in params :
                pass
            else : 
                query = ''' select count(id) as cnt
                            from recipe_comment
                            where recipe_id = %s
                            group by recipe_id; '''

                record = (recipe_id,  )
                cursor.execute(query, record)
                # select 문은 아래 내용이 필요하다.
                # 커서로 부터 실행한 결과 전부를 받아와라.
                record_list = cursor.fetchall()
                
                return_dict["count"] = record_list[0]["cnt"]



            
            


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
        return {'status' : 200, 'message' :  "success" ,'comments' : return_dict }, HTTPStatus.OK



    def post (self, recipe_id) :

        params = request.args.to_dict()
        data = request.get_json()

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # user_id get
            external_type = params['external_type']
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

            query = '''select id, external_id
                        from user
                        where external_id = %s;'''
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
            # 2. 해당 테이블, recipe 테이블에서 select
            query = '''insert into recipe_comment
                        (user_id, recipe_id, comment)
                        values
                        (%s, %s, %s);'''

            record = ( user_id, recipe_id, data["comment"])
            cursor.execute(query, record)
            # 커넥션 커밋              
            connection.commit()

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
        return {'status' : 200, 'message' : "success" }, HTTPStatus.OK



class RecipeCommentResource(Resource) :

    def put(self, comment_id) :

        params = request.args.to_dict()
        data = request.get_json()

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # user_id get
            external_type = params['external_type']
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

            query = '''select id, external_id
                        from user
                        where external_id = %s;'''
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
            # 2. 해당 테이블, recipe 테이블에서 select
            query = '''UPDATE recipe_comment
                        SET comment = %s
                        WHERE id = %s and user_id = %s; '''

            record = (comment_id, user_id, data["comment"]) 
            cursor.execute(query, record)
            # 커넥션 커밋              
            connection.commit()
            
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
        return {'status' : 200, 'message' : "success" }, HTTPStatus.OK


    def delete(self, comment_id) :
        params = request.args.to_dict()

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # user_id get
            external_type = params['external_type']
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

            query = '''select id, external_id
                        from user
                        where external_id = %s;'''
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
            # 2. 해당 테이블, recipe 테이블에서 select
            query = '''DELETE FROM recipe_comment 
                        WHERE id = %s and user_id = %s;'''

            record = (comment_id, user_id )
            cursor.execute(query, record)
            # 커넥션 커밋              
            connection.commit()
            
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
        return {'status' : 200, 'message' : "success" }, HTTPStatus.OK