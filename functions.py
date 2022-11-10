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
def check_user(connection, external_type,external_id) :

    try :
        print("회원가입 확인중")
        query = '''SELECT  email, nickname, profile_img, profile_desc, created_at 
                    FROM user
                    where external_type = %s
                    and external_id = %s;'''
                                    
        param = (external_type,external_id )
        
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
            return {'status' : 400, 'message' : "회원이 아닙니다."}

    # 위의 코드를 실행하다가, 문제가 생기면, except를 실행하라는 뜻.
    except Error as e :
        print('Error while connecting to MySQL', e)
        return {'status' : 500, 'message' : str(e)} 









