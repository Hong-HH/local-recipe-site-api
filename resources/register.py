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



# 회원가입 api
class UserRegisterResource(Resource) :
    
    def post(self) : 
        print("회원가입 시작")
         # 바디에서 AuthType 가져오기
        data = request.get_json()
        AuthType = data["external_type"]

        if AuthType is None :
            print("필수요소 없음")
            return {'status' : 400 , 'message' : "external_type 누락"}  , 400


        # 네이버로 로그인을 하였을  때
        # 회원가입을 했는지 여부를 구분하는 것은 code, state 가 아니다. --> 코드 수정 필요

        if AuthType == "naver" :
            # request 의 body 에서 code 와 state 값 받기
            # 1-1. 클라이언트로부터 정보를 받아온다.
            
            print("회원가입 절차 시작")

            # 엑세스 토큰 확인
            access_token =  request.headers.get('Authorization') 
            refresh_token = request.headers.get('Rft')


            # 엑세스 토큰 유효성 검사 겸 유저 정보 겟
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

            try : 
                # db 연결
                connection = get_connection()
                # 커서 가져오기
                cursor = connection.cursor(dictionary = True)
                # db에 등록된 유저인지 체크
                check_result = check_user(cursor, "naver", profile_info["id"])

                if check_result["status"] == 200 :
                    # db에 유저가 있음 --> 회원가입함 리턴
                    return {'status' : 400 , 'message' : "registered"}  , 400
                elif check_result["status"] == 400 :
                    # db에 유저가 없음 
                    if "access_token" in data :
                        # 유저가 없고 엑세스 토큰이 data에 담겨왔다면
                        # db 에 유저 등록
                        try :
                            print("회원 등록 중")
                            query = '''insert into user
                                    (external_type ,external_id, email, nickname, profile_img, profile_desc)
                                    values
                                    ("naver",%s,%s, %s, %s);'''
                                                        
                            param = (profile_info["id"], data["email"],data["nickname"],profile_info["profile_img"],profile_info["profile_desc"] )
                            
                            # 쿼리문을 커서에 넣어서 실행한다.
                            cursor.execute(query, param)

                            # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                            connection.commit()

                            # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                        except Error as e :
                            print('Error while connecting to MySQL', e)
                            return {'status' : 500, 'message' : str(e)} , 500

                        # 회원가입 결과 보내주기.
                        print("회원가입 성공")

                        # 회원가입 되어있는지 다시 확인
                        check_result = check_user(cursor, "naver", profile_info["id"])

                        # db에 유저가 있을시 회원가입 결과 리턴
                        if check_result["status"] == 200 :
                            resp = Response(
                                response=json.dumps({  'status' : 200 , 
                                                    'message' : "success", 
                                                    "userInfo": check_result["userInfo"], 
                                                    }),
                                        status=202,
                                        mimetype="application/json"
                                        )

                        # 보내줄때 쿠키에 refresh 토큰
                        resp.set_cookie('refresh_token', refresh_token )
                        return resp


                    else :
                        return {'status' : 500 , 'message' : "회원정보를 db에 등록하는데 실패하였습니다."} , 500



            except Error as e:
                print('Error', e)
                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} ,500

            # finally는 필수는 아니다.
            finally :
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print('MySQL connection is closed')
                else :
                    print('MySQL connection failed connect')
            
            
        
        # 구글로 회원가입을 하였을 때
        elif  AuthType == "google" :            
            id_token =  request.headers.get('Authorization') 
            print(id_token)
            split_text = id_token.split(' ')
            token = split_text[-1]

            print(token)

            # 바디에서 수정한 정보들 받기 
            data = request.get_json()
            print(data)

            # 2. id 토큰 유효성 검사
            #  공식문서 : https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                id_info = id_token_module.verify_oauth2_token(token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)
                print("유효한 토큰입니다.")

            except ValueError:
                # Invalid token
                print("Invalid token")

                # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 
                return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}, 500
                


            # 3-1. DB에 연결
            try : 
                connection = get_connection()

                cursor = connection.cursor(dictionary = True)

                # 3-2. 회원가입 되어있는지 확인
                check_result = check_user(cursor, "google", id_info["sub"])

                # 3-3. db에 유저가 있을시 로그인 결과 리턴
                if check_result["status"] == 200 :
                    # 이미 회원가입 된 유저입니다 리턴
                    return {'status' : 400 , 'message' : "registered"} , 400


                else :    
                    # 이메일 키가 바디에 있다면, 이는 이미 유저에 대한 정보를 한 번 보내 
                    # 수정된 정보를 담고 있는 것이기에 바로 db 저장
                    if "email" in data :
                        print("email 확인 중")
                        try :
                            print("회원 등록 중")
                            query = '''insert into user
                                    (external_type ,external_id, email, nickname, profile_img)
                                    values
                                    ("google",%s,%s, %s, %s);'''
                                                        
                            param = (id_info["sub"], data["email"],data["nickname"],id_info["picture"])
                            
                            # 쿼리문을 커서에 넣어서 실행한다.
                            cursor.execute(query, param)

                            # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                            connection.commit()

                            # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                        except Error as e :
                            print('Error while connecting to MySQL', e)
                            return {'status' : 500, 'message' : str(e)}  , 500

                        # 회원가입 결과 보내주기.
                        print("회원가입 성공")

                        # 회원가입 되어있는지 다시 확인
                        check_result = check_user(cursor, "google", id_info["sub"])

                        # db에 유저가 있을시로그인 결과 리턴
                        if check_result["status"] == 200 :
                            return {'status' : 200 , 'message' : "success", "userInfo": check_result["userInfo"]} , 200

                        else :
                            return {'status' : 500 , 'message' : "회원정보를 db에 등록하는데 실패하였습니다."}  , 500



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

