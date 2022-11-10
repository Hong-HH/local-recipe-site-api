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

from functions import check_user


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
            # 1. 클라이언트로부터 정보를 받아온다.
            # request 의 body 에서 code 와 state 값 받기
            data = request.get_json()
            code = data["code"]
            state = data["state"]

            # 2. access_token과 유저 프로필 정보를 받는다.
            client_id = Config.NAVER_LOGIN_CLIENT_ID
            client_secret = Config.NAVER_LOGIN_CLIENT_SECRET

            redirect_uri = Config.LOCAL_URL + "v1/user/login"

            url = Config.NAVER_TOKEN_URL
            url = url + "client_id=" + client_id + "&client_secret=" + client_secret + "&redirect_uri=" + redirect_uri + "&code=" + code + "&state=" + state


            token_result = requests.get(url).json()
            print("token_result     :")
            print(token_result)

            access_token = token_result.get("access_token")
            refresh_token = token_result.get("refresh_token")

            header = {"Authorization" : "Bearer " + access_token}

            profile_result = requests.get("https://openapi.naver.com/v1/nid/me", headers = header).json()
            profile_info = profile_result["response"]

            print("profile_info     :")
            print(profile_info)

            # 3-1. DB에 연결
            try : 
                connection = get_connection()

            except Error as e:
                print('Error', e)

                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} 
            

            # 3. 유저 정보를 바탕으로 회원가입을 했는지 db에서 확인
            try :
                print("회원가입 확인중")
                query = '''SELECT  email, nickname, profile_img, profile_desc, created_at 
                            FROM user
                            where external_type = "naver"
                            and external_id = %s;'''
                                            
                param = (profile_info["id"], )
                
                cursor = connection.cursor(dictionary = True)

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

                    
                    
                    # https://stackoverflow.com/questions/57355326/can-flask-restful-return-response-object
                    # https://stackoverflow.com/questions/25860304/how-do-i-set-response-headers-in-flask
                    
                    resp = Response(
                            response=json.dumps({
                                                    "status" : 200,
                                                    "message": "success" ,
                                                    "userInfo" : record_list,
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
                    # 4-1. 회원가입이 되어있지 않다면 db에 유저 정보를 등록해준다.
                    try :
                        print("회원 등록 중")
                        query = '''insert into user
                                (external_type ,external_id, email, nickname, profile_img)
                                values
                                ("naver",%s,%s, %s, %s);'''
                                                    
                        param = (profile_info["id"], profile_info["email"],profile_info["name"],profile_info["profile_image"])
                        
                        # 커넥션으로부터 커서를 가져온다
                        cursor = connection.cursor()
                        # 쿼리문을 커서에 넣어서 실행한다.
                        cursor.execute(query, param)

                        # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                        connection.commit()


                        # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                    except Error as e :
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500, 'message' : str(e)} 


                    # 4-2. 로그인 결과 보내주기.
                    print("회원가입 성공")
                    try :
                        print("db 정보 확인 중")
                        query = '''SELECT  email, nickname, profile_img, profile_desc, created_at 
                                    FROM user
                                    where external_type = "naver"
                                    and external_id = %s;'''
                                                    
                        param = (profile_info["id"], )
                        
                        cursor = connection.cursor(dictionary = True)

                        cursor.execute(query, param)

                        # select 문은 아래 내용이 필요하다.
                        record_list = cursor.fetchall()
                        print("record_list    :   ")
                        print(record_list)

                        # 저장된 정보를 로그인 결과로 보내준다.
                        if len( record_list ) == 1 :
                            print("회원가입 되어있음")
                            ### 중요. 파이썬의 시간은, JSON으로 보내기 위해서
                            ### 문자열로 바꿔준다.
                            i = 0
                            for record in record_list:
                                record_list[i]['created_at'] = record['created_at'].isoformat()
                                i = i + 1

                            resp = Response(
                            response=json.dumps({
                                                    'status' : 200,
                                                    "message": "success" ,
                                                    "userInfo" : record_list,
                                                    "token" : access_token
                                                }),
                                        status=200,
                                        mimetype="application/json"
                                        )

                            # resp.headers['access_Token'] = access_token
                            resp.set_cookie('refresh_token', refresh_token )
                            
                            return resp

                    # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                    except Error as e :
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500, 'message' : str(e)} 


                    
            # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
            except Error as e :
                print('Error while connecting to MySQL', e)
                return {'status' : 500, 'message' : str(e)} 

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
            # 1. 클라이언트로부터 정보를 받아온다.
            # 헤더에 있는 id 토큰 얻기
            # werkzeug.datastructures.EnvironHeaders 에 대한 설명 아래 링크 참고
            # https://tedboy.github.io/flask/generated/generated/werkzeug.EnvironHeaders.html
            get_header = request.headers
            #  request.headers.get('Token') 해보자!
            print("get_header    :")
            print(get_header)
            print(type(get_header))
            id_token = get_header['Token']
            print(type(id_token))
            print(id_token)

            # 2. id 토큰 유효성 검사
            #  공식문서 : https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
            try:
                # Specify the CLIENT_ID of the app that accesses the backend:
                id_info = id_token_module.verify_oauth2_token(id_token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)

                # 확인용 print 문
                print("id info 프린트")
                print(id_info)

            except ValueError:
                # Invalid token
                print("Invalid token")

                # 만약 access_token 이 만료되었다면 재발급


                # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 
                return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김"}


            # 3-1. DB에 연결
            try : 
                connection = get_connection()

            except Error as e:
                print('Error', e)

                return {'status' : 500 , 'message' : 'db연결에 실패했습니다.'} 
                       
            # 3-2. 회원가입 여부 확인
            try :
                print("회원가입 확인중")
                query = '''SELECT  email, nickname, profile_img, profile_desc, created_at 
                            FROM user
                            where external_type = "google"
                            and external_id = %s;'''
                                            
                param = (id_info["sub"], )
                
                cursor = connection.cursor(dictionary = True)

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
                    # 4-1. 회원가입이 되어있지 않다면 db에 유저 정보를 등록해준다.
                    try :
                        print("회원 등록 중")
                        query = '''insert into user
                                (external_type ,external_id, email, nickname, profile_img)
                                values
                                ("google",%s,%s, %s, %s);'''
                                                    
                        param = (id_info["sub"], id_info["email"],id_info["name"],id_info["picture"])
                        
                        # 커넥션으로부터 커서를 가져온다
                        cursor = connection.cursor()
                        # 쿼리문을 커서에 넣어서 실행한다.
                        cursor.execute(query, param)

                        # 커넥션을 커밋한다. => 디비에 영구적으로 반영하라는 뜻.
                        connection.commit()

                        # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                    except Error as e :
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500, 'message' : str(e)} 


                    # 4-2. 로그인 결과 보내주기.
                    print("회원가입 성공")
                    try :
                        print("db 정보 확인 중")
                        query = '''SELECT  email, nickname, profile_img, profile_desc, created_at 
                                    FROM user
                                    where external_type = "google"
                                    and external_id = %s;'''
                                                    
                        param = (id_info["sub"], )
                        
                        cursor = connection.cursor(dictionary = True)

                        cursor.execute(query, param)

                        # select 문은 아래 내용이 필요하다.
                        record_list = cursor.fetchall()
                        print("record_list    :   ")
                        print(record_list)

                        # 저장된 정보를 로그인 결과로 보내준다.
                        if len( record_list ) == 1 :
                            print("회원가입 되어있음")
                            ### 중요. 파이썬의 시간은, JSON으로 보내기 위해서
                            ### 문자열로 바꿔준다.
                            i = 0
                            for record in record_list:
                                record_list[i]['created_at'] = record['created_at'].isoformat()
                                i = i + 1
                            return {'status' : 200, 'message' : record_list}

                    # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
                    except Error as e :
                        print('Error while connecting to MySQL', e)
                        return {'status' : 500, 'message' : str(e)} 


                    
            # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
            except Error as e :
                print('Error while connecting to MySQL', e)
                return {'status' : 500, 'message' : str(e)} 

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

    # def get(self) : 
    #     # 구글과 네이버를 가르는 분기문
    #     state = request.args.get('state')

    #     print(request.args.to_dict())


    #     if state  :
    #         # flask 프론트에서 값을 받아올 때
            
    #         code = request.args.get('code')


    #         client_id = Config.NAVER_LOGIN_CLIENT_ID
    #         client_secret = Config.NAVER_LOGIN_CLIENT_SECRET

    #         redirect_uri = Config.LOCAL_URL + "v1/user/login"

    #         url = Config.NAVER_TOKEN_URL
    #         url = url + "client_id=" + client_id + "&client_secret=" + client_secret + "&redirect_uri=" + redirect_uri + "&code=" + code + "&state=" + state


    #         token_result = requests.get(url).json()
    #         print("token_result     :")
    #         print(token_result)


    #         #  dict 를 dict.get('key') 로 엑섹스 함
    #         access_token = token_result.get("access_token")

    #         header = {"Authorization" : "Bearer " + access_token}

    #         #  프로필 요청
    #         profile_result = requests.get("https://openapi.naver.com/v1/nid/me", headers = header).json()

    #         print("profile_result     :")
    #         print(profile_result)

    #         return {'status' : 200, 'message' : {'token_result' : token_result, 'profile_result' : profile_result }}

    #     elif state is None :
    #         print("state is None")
    #         print("so this is google login")

    #         code = request.args.get('code')
    #         client_id = Config.GOOGLE_LOGIN_CLIENT_ID
    #         client_secret = Config.GOOGLE_LOGIN_CLIENT_SECRET
    #         redirect_uri =  Config.LOCAL_URL + "v1/user/login"
            
    #         url = Config.GOOGLE_TOKEN_UTL
    #         url = url + "grant_type=authorization_code"
    #         url = url + "&client_id="+ client_id +"&client_secret="+ client_secret +"&code=" + code +"&redirect_uri=" + redirect_uri

    #         # header = {'Content-type': 'application/x-www-form-urlencoded'}

    #         print(url)
    #         # , headers=header

    #         login_result = requests.post(url).json()
    #         print(login_result)

    #         id_token = login_result['id_token']
    #         print("id token 의 type")
    #         print(type(id_token))
    #         print("id token         :")
    #         print(id_token)

    #         # 안되면 Bearer 붙여서 하기
            
    #         #  Google ID 토큰의 유효성을 검사
    #         #  공식문서 : https://developers.google.com/identity/gsi/web/guides/verify-google-id-token

    #         try:
    #             # Specify the CLIENT_ID of the app that accesses the backend:
    #             idinfo = id_token_module.verify_oauth2_token(id_token, google_requests.Request(), Config.GOOGLE_LOGIN_CLIENT_ID)
    #             # Or, if multiple clients access the backend server:
    #             # idinfo = id_token.verify_oauth2_token(token, requests.Request())
    #             # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
    #             #     raise ValueError('Could not verify audience.')

    #             # ID token is valid. Get the user's Google Account ID from the decoded token.
    #             userid = idinfo['sub']
    #             print(type(idinfo))
    #             print(idinfo)


    #         except ValueError:
    #             # Invalid token
    #             print("Invalid token")

    #             # 토큰이 유효하지 않을 때 리턴값으로 분기문 설정 

    #             # 만약 access_token 이 만료되었다면 재발급
                
    #             pass    




    #         return {'status' : 200, 'message' : login_result}
