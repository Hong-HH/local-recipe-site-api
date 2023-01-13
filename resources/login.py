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

from functions_for_users import check_user, get_naver_token, get_naver_profile, refresh_naver_token


# 같은 이름의 라이브러리 임포트할 때 팁
# >>> from foo import bar as first_bar
# >>> from baz import bar as second_bar


# 클라이언트(web user) 에게서 받아 (로그인 결과) 리턴해주는 api
class UserLoginResource(Resource) :
    
    def post(self) : 
        # 헤더에서 AuthType 가져오기
        AuthType = request.headers.get("AuthType")
        print("post methon 시작")

        # 네이버로 로그인을 하였을  때
        if AuthType == "naver" :
            # 1-1. 클라이언트로부터 정보를 받아온다.
            data = request.get_json()
            # 1-2. DB에 연결
            try : 
                connection = get_connection()
                cursor = connection.cursor(dictionary = True)
                
                if "code" in data :
                    # data 에서 code 와 state 값 받기
                    print("access_token 발급 시작")
                    code = data["code"]
                    state = data["state"]

                    # 함수를 사용하여 access_token, refresh_token를 받는다.
                    token_result = get_naver_token(code, state)
                    access_token = token_result["access_token"]
                    refresh_token = token_result["refresh_token"]
                    
                    
                # 2-1. access_token 없으면 access_token 발급
                else :
                    # 2-1. access_token 있으면 변수에 저장
                    access_token =  request.headers.get('Authorization') 
                    refresh_token = request.headers.get('Rft')
                    

                    
                # 3. access_token 유효성 검사 및 유저 정보 겟
                profile_result = get_naver_profile(access_token)
                if profile_result["result_code"] == "00" :
                    profile_info = profile_result["profile_info"]
                else :
                    # todo access token 만료이므로 재발급
                    print("access token 이 유효하지 않음")
                    print(profile_result["message"] )

                    access_token = refresh_naver_token(refresh_token)
                    profile_result = get_naver_profile(access_token)
                    if profile_result["result_code"] == "00" :
                        profile_info = profile_result["profile_info"]
                    else :
                        print("access token 발급에 문제 발생")
                        return {"status" : 500 , 'message' : "access token 발급에 문제 발생"} , 500

                # db에 등록된 유저인지 체크
                check_result = check_user(cursor, "naver", profile_info["id"])

                if check_result["status"] == 200 :
                    # db에 유저가 있음 --> 로그인 결과 리턴
                    resp = Response(
                        response=json.dumps({ 'status' : 200 , 
                                            'message' : "success", 
                                            "userInfo": userInfo, 
                                            "token": access_token
                                            }),
                                status=200,
                                mimetype="application/json"
                                )

                    # 보내줄때 쿠키에 refresh 토큰
                    resp.set_cookie('refresh_token', refresh_token )
                    return resp
                    
                elif check_result["status"] == 400 :
                    # db에 유저가 없음 --> 정보 쥐어주고 회원가입으로 보내버리기

                    userInfo = { "nickname" : profile_info["nickname"], "email" : profile_info["email"] , "external_type": AuthType }

                    resp = Response(
                        response=json.dumps({"isRegistered": False,
                                            'status' : 202 , 
                                            'message' : "go_register", 
                                            "userInfo": userInfo, 
                                            "token": {
                                                        "act" : access_token,
                                                        "rft" : refresh_token,
                                                        } 
                                            }),
                                status=202,
                                mimetype="application/json"
                                )

                    # 보내줄때 쿠키에 refresh 토큰
                    resp.set_cookie('refresh_token', refresh_token )
                    return resp
    
                else :
                    return {'status' : 500 , 'message' : 'check_user() 에서 알 수 없는 에러 발생'} , 500

            except Error as e:
                print('Error', e)

                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} , 500

            # finally는 필수는 아니다.
            finally :
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print('MySQL connection is closed')
                else :
                    print('MySQL connection failed connect')



        # 구글로 로그인을 하였을 때
        elif  AuthType == "google" :
            # 1. 클라이언트로부터 헤더에 있는 id 토큰 정보를 받아온다.
            # werkzeug.datastructures.EnvironHeaders 에 대한 설명 링크 참고  (https://tedboy.github.io/flask/generated/generated/werkzeug.EnvironHeaders.html)
            id_token =  request.headers.get('Authorization') 
            split_text = id_token.split(' ')
            token = split_text[-1]

            print(token)

            # 2. id 토큰 유효성 검사
            #  공식문서 : https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                id_info = id_token_module.verify_oauth2_token(token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)

            except ValueError:
                # Invalid token
                print("Invalid token")

                # todo 만약 id_token 이 만료되었다면 재발급


                # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 
                return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}, 500


            # 3-1. DB에 연결
            try : 
                connection = get_connection()

                cursor = connection.cursor(dictionary = True)

                # 3-2. 회원가입 되어있는지 확인
                check_result = check_user(cursor, "google", id_info["sub"])

                print(check_result["status"])

                # 3-3. db에 유저가 있을시 로그인 결과 리턴
                if check_result["status"] == 200 :
                    print("회원가입이 되어있습니다.")
                    return {'status' : 200 , 'message' : "success", "userInfo": check_result["userInfo"] } , 200

                else :    
                    # 4-1. 회원가입이 되어있지 않다면 회원가입이 필요하다는 메세지를 리턴해준다.
                    print("회원가입이 되어있지 않습니다.")
                    userInfo = { "nickname" : id_info["name"], "email" : id_info["email"] , "external_type": AuthType }
                    return { "isRegistered": False, 'status' : 202 , 'message' : "go_register", "userInfo" : userInfo } , 202


            except Error as e:
                print('Error', e)

                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} , 500

            # finally는 필수는 아니다.
            finally :
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print('MySQL connection is closed')
                else :
                    print('MySQL connection failed connect')


