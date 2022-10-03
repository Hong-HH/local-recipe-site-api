from flask import request
from flask.json import jsonify
from flask_restful import Resource
from http import HTTPStatus
import requests

from mysql_connection import get_connection
from mysql.connector.errors import Error

from email_validator import validate_email, EmailNotValidError

from utils import check_password, hash_password

from flask_jwt_extended import  get_jwt, get_jwt_header
from config import Config

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests



# 같은 이름의 라이브러리 임포트할 때 팁
# >>> from foo import bar as first_bar
# >>> from baz import bar as second_bar



class UserLoginResource(Resource) :
    def post(self) : 
        # 협의를 봐서 분기문 추가하기

        login_type = request.args.get('login_type')

        if login_type == "naver" :
            # 1. 클라이언트로부터 정보를 받아온다.
            # request 의 body 에서 code 와 state 값 받기
            data = request.get_json()
            code = data["code"]
            state = data["state"]


            client_id = Config.NAVER_LOGIN_CLIENT_ID
            client_secret = Config.NAVER_LOGIN_CLIENT_SECRET

            redirect_uri = Config.LOCAL_URL + "v1/user/login"

            url = Config.NAVER_TOKEN_URL
            url = url + "client_id=" + client_id + "&client_secret=" + client_secret + "&redirect_uri=" + redirect_uri + "&code=" + code + "&state=" + state


            token_result = requests.get(url).json()
            print("token_result     :")
            print(token_result)

            access_token = token_result.get("access_token")

            header = {"Authorization" : "Bearer " + access_token}

            profile_result = requests.get("https://openapi.naver.com/v1/nid/me", headers = header).json()

            print("profile_result     :")
            print(profile_result)

            return {'status' : 200, 'message' : {'token_result' : token_result, 'profile_result' : profile_result }}








    def get(self) : 
        # 구글과 네이버를 가르는 분기문
        state = request.args.get('state')

        print(request.args.to_dict())


        if state  :
            # flask 프론트에서 값을 받아올 때
            
            code = request.args.get('code')


            client_id = Config.NAVER_LOGIN_CLIENT_ID
            client_secret = Config.NAVER_LOGIN_CLIENT_SECRET

            redirect_uri = Config.LOCAL_URL + "v1/user/login"

            url = Config.NAVER_TOKEN_URL
            url = url + "client_id=" + client_id + "&client_secret=" + client_secret + "&redirect_uri=" + redirect_uri + "&code=" + code + "&state=" + state


            token_result = requests.get(url).json()
            print("token_result     :")
            print(token_result)


            #  dict 를 dict.get('key') 로 엑섹스 함
            access_token = token_result.get("access_token")

            header = {"Authorization" : "Bearer " + access_token}

            profile_result = requests.get("https://openapi.naver.com/v1/nid/me", headers = header).json()

            print("profile_result     :")
            print(profile_result)

            return {'status' : 200, 'message' : {'token_result' : token_result, 'profile_result' : profile_result }}

        elif state is None :
            print("state is None")
            print("so this is google login")

            code = request.args.get('code')
            client_id = Config.GOOGLE_LOGIN_CLIENT_ID
            client_secret = Config.GOOGLE_LOGIN_CLIENT_SECRET
            redirect_uri =  Config.LOCAL_URL + "v1/user/login"
            
            url = Config.GOOGLE_TOKEN_UTL
            url = url + "grant_type=authorization_code"
            url = url + "&client_id="+ client_id +"&client_secret="+ client_secret +"&code=" + code +"&redirect_uri=" + redirect_uri

            # header = {'Content-type': 'application/x-www-form-urlencoded'}

            print(url)
            # , headers=header

            login_result = requests.post(url).json()
            print(login_result)

            id_token = login_result['id_token']
            
            #  Google ID 토큰의 유효성을 검사
            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                idinfo = id_token.verify_oauth2_token(id_token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)
                # Or, if multiple clients access the backend server:
                # idinfo = id_token.verify_oauth2_token(token, requests.Request())
                # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
                #     raise ValueError('Could not verify audience.')

                # ID token is valid. Get the user's Google Account ID from the decoded token.
                userid = idinfo['sub']
                print(type(idinfo))
                print(idinfo)


            except ValueError:
                # Invalid token
                print("Invalid token")
                pass    



            # tokeninfo 엔드포인트 호출
            # 요청이 제한되거나 간헐적인 오류가 발생할 수 있으므로 프로덕션 코드에서 사용하기에 적합하지 않습니다.
            token_info_url = 'ttps://oauth2.googleapis.com/tokeninfo?id_token=' + id_token
            token_info_result = requests.get(token_info_url).json
            print (token_info_result)




            return {'status' : 200, 'message' : login_result}
