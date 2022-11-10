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



# 회원가입 여부 확인
def check_user(cursor, external_type,external_id) :

    try :
        print("회원가입 확인중")
        query = '''SELECT  email, nickname, profile_img, profile_desc, created_at 
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
                record_list[i]['created_at'] = record['created_at'].isoformat()
                i = i + 1
            return {'status' : 200, 'message' : record_list}

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

    header = {"Authorization" : "Bearer " + access_token}

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




# todo id_token 이 만료되었다면 재발급 함수









