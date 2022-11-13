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
        # 파라미터에서 external_type 가져오기
        external_type = request.args.get('external_type')

        # 네이버로 로그인을 하였을  때
        # 회원가입을 했는지 여부를 구분하는 것은 code, state 가 아니다. --> 코드 수정 필요

        if external_type == "naver" :
            # request 의 body 에서 code 와 state 값 받기
            # 1-1. 클라이언트로부터 정보를 받아온다.
            data = request.get_json()
            print("회원가입 절차 시작")

            # 엑세스 토큰 확인
            if "access_token" in data :
                access_token = data["access_token"]
                refresh_token = request.cookies.get('refresh_token')

            # else :
            #     # 엑세스 토큰이 없다면 엑세스 토큰 발급
            #     code = data["code"]
            #     state = data["state"]

            #     # 함수를 사용하여 access_token, refresh_token를 받는다.
            #     token_result = get_naver_token(code, state)
            #     access_token = token_result["access_token"]
            #     refresh_token = token_result["refresh_token"]


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
                    return {"status" : 500 , 'message' : "access token 발급에 문제 발생"}

            try : 
                # db 연결
                connection = get_connection()
                # 커서 가져오기
                cursor = connection.cursor(dictionary = True)
                # db에 등록된 유저인지 체크
                check_result = check_user(cursor, "naver", profile_info["id"])

                if check_result["status"] == 200 :
                    # db에 유저가 있음 --> 회원가입함 리턴
                    return {'status' : 400 , 'message' : "registered"} 
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
                                                        
                            param = (profile_info["id"], data["email"],data["nickname"],data["profile_img"],data["profile_desc"] )
                            
                            # 쿼리문을 커서에 넣어서 실행한다.
                            cursor.execute(query, param)

                            # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                            connection.commit()

                            # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                        except Error as e :
                            print('Error while connecting to MySQL', e)
                            return {'status' : 500, 'message' : str(e)} 

                        # 회원가입 결과 보내주기.
                        print("회원가입 성공")

                        # 회원가입 되어있는지 다시 확인
                        check_result = check_user(cursor, "naver", profile_info["id"])

                        # db에 유저가 있을시 회원가입 결과 리턴
                        if check_result["status"] == 200 :
                            return {'status' : 200 , 'message' : "register success", "userInfo": check_result["userInfo"]} 

                        else :
                            return {'status' : 500 , 'message' : "회원정보를 db에 등록하는데 실패하였습니다."} 


                    # else :
                    #     # data에 access_token 이 없다면 정보를 수정할 수 있게
                    #     # external user info 반환

                    #     userInfo = {"email":profile_info["email"] , "nickname": profile_info["name"], "profile_img": profile_info["profile_image"] }
                        
                    #     resp = Response(
                    #     response=json.dumps({'status' : 200 , 
                    #                         'message' : "success", 
                    #                         "userInfo": userInfo, 
                    #                         "access_token": access_token}),
                    #             status=200,
                    #             mimetype="application/json"
                    #             )

                    #     # 헤더에 access 토큰 이 아니라 바디
                    #     # resp.headers['access_Token'] = access_token
                    #     # 보내줄때 쿠키에 refresh 토큰
                    #     resp.set_cookie('refresh_token', refresh_token )
                    #     return resp

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
            
            
        
        # 구글로 회원가입을 하였을 때
        elif  external_type == "google" :
            id_token =  request.headers.get('Token') 
            print(id_token)

            # 바디에서 수정한 정보들 받기 
            data = request.get_json()

            # 2. id 토큰 유효성 검사
            #  공식문서 : https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                id_info = id_token_module.verify_oauth2_token(id_token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)

            except ValueError:
                # Invalid token
                print("Invalid token")

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
                    # 이미 회원가입 된 유저입니다 리턴
                    return {'status' : 400 , 'message' : "registered"} 


                else :    
                    # 이메일 키가 바디에 있다면, 이는 이미 유저에 대한 정보를 한 번 보내 
                    # 수정된 정보를 담고 있는 것이기에 바로 db 저장
                    if "email" in data :
                        try :
                            print("회원 등록 중")
                            query = '''insert into user
                                    (external_type ,external_id, email, nickname, profile_img, profile_desc)
                                    values
                                    ("google",%s,%s, %s, %s);'''
                                                        
                            param = (id_info["sub"], data["email"],data["nickname"],data["profile_img"],data["profile_desc"] )
                            
                            # 쿼리문을 커서에 넣어서 실행한다.
                            cursor.execute(query, param)

                            # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                            connection.commit()

                            # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                        except Error as e :
                            print('Error while connecting to MySQL', e)
                            return {'status' : 500, 'message' : str(e)} 

                        # 회원가입 결과 보내주기.
                        print("회원가입 성공")

                        # 회원가입 되어있는지 다시 확인
                        check_result = check_user(cursor, "google", id_info["sub"])

                        # db에 유저가 있을시로그인 결과 리턴
                        if check_result["status"] == 200 :
                            return {'status' : 200 , 'message' : "register success", "userInfo": check_result["userInfo"]} 

                        else :
                            return {'status' : 500 , 'message' : "회원정보를 db에 등록하는데 실패하였습니다."} 


                    # else : 
                    #     # 이 경우 회원가입을 진행하기 전 정보를 수정할 수 있게 
                    #     # external site에서 가져온 회원정보 보내주기
                    #     userInfo = {"email":id_info["email"] , "nickname": id_info["name"], "profile_img":id_info["picture"] }
            
                    #     return {'status' : 200 , 'message' : "success", "userInfo": userInfo}


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



# 3-2. db에 유저가 없을시 회원가입 결과 리턴
# if check_result["status"] == 200 :
#     if "code" in data :
#         resp = Response(
#                 response=json.dumps({
#                                         "status" : 200,
#                                         "message": "success" ,
#                                         "userInfo" : check_result["userInfo"],
#                                         "token" : access_token
#                                     }),
#                         status=200,
#                         mimetype="application/json"
#                         )

#         # 헤더에 access 토큰 이 아니라 바디
#         # resp.headers['access_Token'] = access_token
#         # 보내줄때 쿠키에 refresh 토큰
#         resp.set_cookie('refresh_token', refresh_token )
#         return resp
#     else :
#         return { "status" : 200, "message": "success" , "userInfo" : check_result["userInfo"], "token" : access_token }
# else :
#     return {'status' : 500 , 'message' : '회원정보를 찾을 수 없습니다.'} 