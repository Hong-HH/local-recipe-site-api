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
        # 파라미터에서 external_type 가져오기
        external_type = request.args.get('external_type')

        # 네이버로 로그인을 하였을  때
        if external_type == "naver" :
            # 1-1. 클라이언트로부터 정보를 받아온다.
            data = request.get_json()
            # 1-2. DB에 연결
            try : 
                connection = get_connection()
                cursor = connection.cursor(dictionary = True)
                # 2-1. access_token 있으면 변수에 저장
                if "access_token" in data :
                    access_token = data["access_token"]
                    refresh_token = request.cookies.get('refresh_token')
                    
                # 2-1. access_token 없으면 access_token 발급
                else :
                    # data 에서 code 와 state 값 받기
                    print("access_token 발급 시작")
                    code = data["code"]
                    state = data["state"]

                    # 함수를 사용하여 access_token, refresh_token를 받는다.
                    token_result = get_naver_token(code, state)
                    access_token = token_result["access_token"]
                    refresh_token = token_result["refresh_token"]

                    profile_result = get_naver_profile(access_token)
                    if profile_result["result_code"] == "00" :
                        profile_info = profile_result["profile_info"]

                    else :
                        print("access token 발급에 문제 발생")
                        return {"status" : 404}

                    
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
                        return {"status" : 500 , 'message' : "access token 발급에 문제 발생"}

                # db에 등록된 유저인지 체크
                check_result = check_user(cursor, "naver", profile_info["id"])

                if check_result["status"] == 200 :
                    # db에 유저가 있음 --> 로그인 결과 리턴
                    return {'status' : 200 , 'message' : "success", 'userInfo': check_result["userInfo"]} 
                elif check_result["status"] == 400 :
                    # db에 유저가 없음 --> 정보 쥐어주고 회원가입으로 보내버리기
                    userInfo = {"email":profile_info["email"] , "nickname": profile_info["name"], "profile_img": profile_info["profile_image"] }
                    return {'status' : 400 , 'message' : "go_register", "userInfo" : userInfo, "access_token" : access_token} 

                else :
                    return {'status' : 500 , 'message' : 'check_user() 에서 알 수 없는 에러 발생'} 

            except Error as e:
                print('Error', e)

                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} 

            # finally는 필수는 아니다.
            finally :
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print('MySQL connection is closed')
                else :
                    print('MySQL connection failed connect')



        # 구글로 로그인을 하였을 때
        elif  external_type == "google" :
            # 1. 클라이언트로부터 헤더에 있는 id 토큰 정보를 받아온다.
            # werkzeug.datastructures.EnvironHeaders 에 대한 설명 링크 참고  (https://tedboy.github.io/flask/generated/generated/werkzeug.EnvironHeaders.html)
            id_token =  request.headers.get('Token') 

            print(id_token)

            # 2. id 토큰 유효성 검사
            #  공식문서 : https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                id_info = id_token_module.verify_oauth2_token(id_token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)

            except ValueError:
                # Invalid token
                print("Invalid token")

                # todo 만약 id_token 이 만료되었다면 재발급


                # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 
                return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}


            # 3-1. DB에 연결
            try : 
                connection = get_connection()

                cursor = connection.cursor(dictionary = True)

                # 3-2. 회원가입 되어있는지 확인
                check_result = check_user(cursor, "google", id_info["sub"])

                # 3-3. db에 유저가 있을시 로그인 결과 리턴
                if check_result["status"] == 200 :
                    
                    return {'status' : 200 , 'message' : "success", "userInfo": check_result["userInfo"]} 

                else :    
                    # 4-1. 회원가입이 되어있지 않다면 회원가입이 필요하다는 메세지를 리턴해준다.
                    userInfo = {"email":id_info["email"] , "nickname": id_info["name"], "profile_img":id_info["picture"] }
                    return {'status' : 400 , 'message' : "go_register", "userInfo" : userInfo } 


            except Error as e:
                print('Error', e)

                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} 

            # finally는 필수는 아니다.
            finally :
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print('MySQL connection is closed')
                else :
                    print('MySQL connection failed connect')


    # 유기적인 서버와 클라이언트 테스트를 위해 
    # 임시로 app.py에서 코드 값을 받을 수 있는 path 추가함. 
    # code 를 얻는 path : "/naver", "/google"   
    # redirect(url) 로 각 플랫폼의 로그인 승인 페이지로 이동 --> redirect url 로 설정한 페이지 (v1/user/login) 로 이동됨

    def get(self) : 
        # 구글과 네이버를 가르는 분기문
        state = request.args.get('state')

        print(request.args.to_dict())


        if state  :

            code = request.args.get('code')

            # 테스트를 위해 code, state 값은 반환하는 리턴문
            # return {"code" : code, "state": state}

            # 함수를 사용하여 access_token, refresh_token를 받는다.
            token_result = get_naver_token(code, state)
            access_token = token_result["access_token"]
            refresh_token = token_result["refresh_token"]
            return {'status' : 200, 'access_token' : access_token, "refresh_token" : refresh_token}


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
            print("id token 의 type")
            print(type(id_token))
            print("id token         :")
            print(id_token)

            # id 토큰을 얻기위한 임시 

            return {"message" : id_token}

