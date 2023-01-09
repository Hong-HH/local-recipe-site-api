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
from functions_for_recipe import recipe_list_map, recipe_detail_query, get_category_query


class UserRecipeResource(Resource) :

    #  유저가 쓴 레시피 리턴

    def get(self) : 
        # 파라미터로 order_by 받기
        params = request.args.to_dict()

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # user_id get
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
            user_id = record_list[0]["id"]

            

        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        try :
            if params["order_by"] == "like" :
                order_query = "likes_cnt"
            elif  params["order_by"] == "created_at" :
                order_query = "rn.id"

            # 유저 아이디로 유저 레시피 정보 겟
            query = '''  select r.* , count(uh.created_at) as views
                            from 
                            (select rn.*, count(l.created_at) as likes_cnt
                            from 
                            (select *
                            from recipe
                            where user_id = %s
                            limit ''' + params["offset"] + ''' , ''' +  params["limit"] + ''' ) as rn
                            left join likes as l
                            on rn.id = l.recipe_id
                            group by rn.id
                            order by %s desc) as r
                            left join user_history as uh
                            on r.id = uh.recipe_id
                            group by r.id;   '''
            record = (user_id, order_query)
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            print(record_list)
            return_list = []
            i = 0
            for record in record_list:
                recipe = {"recipe_id": record['id'],
                            "like": record['likes_cnt'],
                            "view": record['views'],
                            "public": record['public'],
                            "src": record['header_img'],
                            "title":record['header_title'],
                            "created_at": record['created_at'].isoformat(),
                            "updated_at" : record['updated_at'].isoformat()}
                return_list.append(recipe)

                i = i + 1


        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR



        finally : 
            print('finally')
            if connection.is_connected():
                cursor.close()
                connection.close()
                print('MySQL connection is closed')
            else :
                print('connection does not exist')

        return {'status' : 200,'message':'success', 'list' : return_list }, HTTPStatus.OK



class UserLikeRecipeResource(Resource) :

    #  유저가 쓴 레시피 리턴

    def get(self) : 
        # 파라미터로 order_by 받기
        params = request.args.to_dict()

        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

            # user_id get
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
            user_id = record_list[0]["id"]

            

        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        try :

            # 유저 아이디로 유저가 좋아요 누른 레시피 정보 겟
            query = '''  select  rlv.*, r.*, u.nickname, u.profile_img
                            from 
                            (select rl.*, count(uh.id) as views
                            from 
                            (select rn.*, count(l.created_at) as likes_cnt
                            from 
                            ( select recipe_id
                            from likes
                            where user_id = %s
                            order by created_at desc
                            limit ''' + params["offset"] + ''' , ''' +  params["limit"]  + ''' ) as rn
                            left join likes as l
                            on rn.recipe_id = l.recipe_id
                            group by rn.recipe_id) as rl
                            left join user_history as uh
                            on rl.recipe_id = uh.recipe_id
                            group by rl.recipe_id) as rlv

                            left join recipe as r
                            on rlv.recipe_id = r.id
                            left join user as u
                            on r.user_id = u.id;   '''
            record = (user_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            print(record_list)
            return_list = []
            i = 0
            for record in record_list:
                recipe = {"recipe_id": record['id'],
                            "like": record['likes_cnt'],
                            "view": record['views'],
                            "userInfo":[record['profile_img'], record['nickname']],
                            "public": record['public'],
                            "src": record['header_img'],
                            "title":record['header_title'],
                            "created_at": record['created_at'].isoformat(),
                            "updated_at" : record['updated_at'].isoformat()}
                return_list.append(recipe)

                i = i + 1


        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR



        finally : 
            print('finally')
            if connection.is_connected():
                cursor.close()
                connection.close()
                print('MySQL connection is closed')
            else :
                print('connection does not exist')

        return {'status' : 200,'message':'success', 'list' : return_list }, HTTPStatus.OK




class UserPurchaseResource(Resource) :

    #  유저의 구매내역 리턴

    def get(self) : 
        pass

    #  유저의 구매내역 추가

    def post(self) : 
        pass



