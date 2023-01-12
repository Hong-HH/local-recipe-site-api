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


#  todo 통합으로 토큰 재발급 하는 거 코드 만들기


# 통합 : 토큰 유효성 검사 및 external_id 값 리턴
def get_external_id(external_type, token) :
    # 받아온 토큰으로 유효성 검사를 해보자.
    if external_type == "naver" :
        # 3. access_token 유효성 검사 및 유저 정보 겟
        profile_result = get_naver_profile(token)
        if profile_result["result_code"] == "00" :
            profile_info = profile_result["profile_info"]
            return  {"status" : 200 , 'message' : "success", 'external_id' : profile_info["id"] , 'user_info' : profile_info }
        else :
            # todo access token 만료이므로 재발급
            print("access token 이 유효하지 않음")
            return {"status" : 400 , 'message' : "access token 만료"}

    elif external_type == "google" :
        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            id_info = id_token_module.verify_oauth2_token(token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)
            print({"status" : 200 , 'message' : "success", 'external_id' : id_info["sub"] , 'user_info' : id_info })
            return {"status" : 200 , 'message' : "success", 'external_id' : id_info["sub"] , 'user_info' : id_info }

        except ValueError:
            # Invalid token
            print("Invalid token")

            # todo 만약 id_token 이 만료되었다면 재발급


            # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 
            return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}



# 음 .. 위에거랑 합쳐서 하나로 만들자..
def get_user_id(external_id) :

     '''select id, external_id
                                            from user
                                            where external_id = %s;'''




def get_refresh_token(external_type, refresh_token):
    # todo 구글 리플레시 토큰 추가하기

    if external_type == "naver" :
        access_token = refresh_naver_token(refresh_token)
        profile_result = get_naver_profile(access_token)
        if profile_result["result_code"] == "00" :
            profile_info = profile_result["profile_info"]
            return {"status" : 200 , 'message' : "success", 'token' : access_token}
        else :
            print("access token 발급에 문제 발생")
            return {"status" : 500 , 'message' : "access token 발급에 문제 발생"}


    elif external_type == "google" :
        # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 
        return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}









# 회원가입 여부 확인
def check_user(cursor, external_type,external_id) :

    try :
        print("회원가입 확인중")
        query = '''SELECT  email, nickname, profile_img, profile_desc, external_type ,created_at as createdAt, updated_at as updatedAt
                    FROM user
                    where external_type = %s
                    and external_id = %s;'''
                                    
        param = (external_type,external_id )
        
        cursor.execute(query, param)

        # select 문은 아래 내용이 필요하다.
        record_list = cursor.fetchall()
        print("record_list    :   ")
        print(record_list)

        # 3-3. 회원가입이 되어있다면 로그인 결과로 보내준다.
        if len( record_list ) == 1 :
            print("회원가입 되어있음")
            ### 중요. 파이썬의 시간은, JSON으로 보내기 위해서
            ### 문자열로 바꿔준다.
            i = 0
            for record in record_list:
                record_list[i]['createdAt'] = record['createdAt'].isoformat()
                record_list[i]['updatedAt'] = record['updatedAt'].isoformat()
                i = i + 1
            return {'status' : 200, 'message' : "회원입니다.","userInfo":record_list[0]}

        else :
            return {'status' : 400, 'message' : "회원이 아닙니다."}

    # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
    except Error as e :
        print('Error while connecting to MySQL', e)
        return {'status' : 500, 'message' : str(e)} 

    # finally :
    #     cursor.close()




def get_naver_token (code, state) :
    # 사용등록을 해놓은 네이버 client 계정을 사용한다.
    client_id = Config.NAVER_LOGIN_CLIENT_ID
    client_secret = Config.NAVER_LOGIN_CLIENT_SECRET

    # 토큰을 얻는 naver api 사용
    redirect_uri = Config.LOCAL_URL + "v1/user/login"

    url = Config.NAVER_TOKEN_URL
    url = url + "grant_type=authorization_code"
    url = url + "&client_id=" + client_id + "&client_secret=" + client_secret + "&redirect_uri=" + redirect_uri + "&code=" + code + "&state=" + state


    token_result = requests.get(url).json()
    print("token_result     :")
    print(token_result)

    return {"access_token" : token_result["access_token"], "refresh_token" : token_result["refresh_token"]}




def get_naver_profile(access_token) :

    header = {"Authorization" :  access_token}

    profile_result = requests.get("https://openapi.naver.com/v1/nid/me", headers = header).json()

    print(profile_result)
    
    result_code =  profile_result["resultcode"]

    if result_code == "00" :
        profile_info = profile_result["response"]

        return {"result_code" : result_code, "profile_info" : profile_info}

    # {'resultcode': '024', 'message': 'Authentication failed (인증 실패하였습니다.)'}

    elif result_code == "024" :
        return {"result_code" : result_code, "message" : "Authentication failed (인증 실패하였습니다.)"}

    return {"result_code" : result_code, "message" : "문제 발생"}


# 네이버 access_token 만료시

def refresh_naver_token (refresh_token) :
    # 사용등록을 해놓은 네이버 client 계정을 사용한다.
    client_id = Config.NAVER_LOGIN_CLIENT_ID
    client_secret = Config.NAVER_LOGIN_CLIENT_SECRET

    # 토큰을 얻는 naver api 사용
    url = Config.NAVER_TOKEN_URL
    url = url + "grant_type=refresh_token"
    url = url + "&client_id=" + client_id + "&client_secret=" + client_secret + "&refresh_token=" + refresh_token

    token_result = requests.get(url).json()
    
    print("token_result     :")
    print(token_result)

    access_token = token_result["access_token"]

    return access_token



# external_type 을 넣으면 id 값이 나오는 함수


# todo id_token 이 만료되었다면 재발급 함수






