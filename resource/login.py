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

from functions import check_user, get_naver_token, get_naver_profile, refresh_naver_token


# 같은 이름의 라이브러리 임포트할 때 팁
# >>> from foo import bar as first_bar
# >>> from baz import bar as second_bar


# 클라이언트(web user) 에게서 받아 (로그인 결과) 리턴해주는 api
class UserLoginResource(Resource) :
    
    def post(self) : 
        # 파라미터에서 외부 로그인이 무엇인지 가져오기
        external_type = request.args.get('external_type')

        # 네이버로 로그인을 하였을  때
        if external_type == "naver" :
            # 1-1. 클라이언트로부터 정보를 받아온다.
            data = request.get_json()
            # 1-2. DB에 연결
            try : 
                connection = get_connection()
                cursor = connection.cursor(dictionary = True)
                # 2-1. code가 있다면 회원가입
                if "code" in data :
                    # request 의 body 에서 code 와 state 값 받기
                    print("회원가입 절차 시작")
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
                    
                    # db에 회원정보 저장
                    try :
                        print("회원 등록 중")
                        query = '''insert into user
                                (external_type ,external_id, email, nickname, profile_img)
                                values
                                ("naver",%s,%s, %s, %s);'''
                                                    
                        param = (profile_info["id"], profile_info["email"],profile_info["name"],profile_info["profile_image"])
                        
                        # 쿼리문을 커서에 넣어서 실행한다.
                        cursor.execute(query, param)

                        # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                        connection.commit()

                        # 회원가입 결과 보내주기.
                        print("회원가입 성공")
                        
                        # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                    except Error as e :
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500, 'message' : str(e)} 



                # 2-2. access_token 이 있다면 프로필을 불러와 유효성 검사 및 id 확인
                elif  "access_token" in data :

                    access_token = data["access_token"]
                    profile_result = get_naver_profile(access_token)
                    if profile_result["result_code"] == "00" :
                        profile_info = profile_result["profile_info"]
                    else :
                        # todo access token 만료이므로 재발급
                        print(profile_result["message"] )
                        print("access token 인증에 문제 발생")
                        return {'status' : 400 , 'message' :profile_result["message"]} 


                # 2-3. 바디에 code, access_token 이 없다면 필요한 값이 전달되지 않은것.
                else :
                    return {'status' : 400 , 'message' : '필수조건을 만족하지 못했습니다.'} 

                # 3-1. 회원가입 되었는지 확인
                check_result = check_user(cursor, "naver", profile_info["id"])

                # 3-2. db에 유저가 있을시 로그인 결과 리턴
                if check_result["status"] == 200 :
                    if "code" in data :
                        resp = Response(
                                response=json.dumps({
                                                        "status" : 200,
                                                        "message": "success" ,
                                                        "userInfo" : check_result["message"],
                                                        "token" : access_token
                                                    }),
                                        status=200,
                                        mimetype="application/json"
                                        )

                        # 헤더에 access 토큰 이 아니라 바디
                        # resp.headers['access_Token'] = access_token
                        # 보내줄때 쿠키에 refresh 토큰
                        resp.set_cookie('refresh_token', refresh_token )
                        return resp
                    else :
                        return { "status" : 200, "message": "success" , "userInfo" : check_result["message"], "token" : access_token }
                else :
                    return {'status' : 500 , 'message' : '회원정보를 찾을 수 없습니다.'} 

                
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
                    
                    return {'status' : 200 , 'message' : "success", "userInfo": check_result["message"]} 

                else :    
                    # 4-1. 회원가입이 되어있지 않다면 db에 유저 정보를 등록해준다.
                    try :
                        print("회원 등록 중")
                        query = '''insert into user
                                (external_type ,external_id, email, nickname, profile_img)
                                values
                                ("google",%s,%s, %s, %s);'''
                                                    
                        param = (id_info["sub"], id_info["email"],id_info["name"],id_info["picture"])
                        
                        # 쿼리문을 커서에 넣어서 실행한다.
                        cursor.execute(query, param)

                        # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                        connection.commit()

                        # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                    except Error as e :
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500, 'message' : str(e)} 


                    # 4-2. 회원가입 결과 보내주기.
                    print("회원가입 성공")

                    #  4-3. 회원가입 되어있는지 다시 확인
                    check_result = check_user(cursor, "google", id_info["sub"])

                    # db에 유저가 있을시로그인 결과 리턴
                    if check_result["status"] == 200 :
                        
                        return {'status' : 200 , 'message' : "register success", "userInfo": check_result["message"]} 

                    else :
                        return {'status' : 500 , 'message' : "회원정보가 확인되지 않았습니다."} 



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

            # # 테스트를 위해 code, state 값은 반환하는 리턴문
            return {"code" : code, "state": state}

            # state = request.args.get('state')

            # # 함수를 사용하여 access_token, refresh_token를 받는다.
            # token_result = get_naver_token(code, state)
            # access_token = token_result["access_token"]
            # refresh_token = token_result["refresh_token"]
            # return {'status' : 200, 'access_token' : access_token}


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

