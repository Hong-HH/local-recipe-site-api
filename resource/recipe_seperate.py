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


list_type_map = {
    "best" :'''select * from memo
                        where user_id=%s
                        order by date desc
                        limit''',
    "best_not_enough" : '''select * from memo
                        where user_id=%s
                        order by date desc
                        limit'''
}




# 메인 페이지의 베스트 레시피의 경우 
# 필요 리턴 값 : 레시피 테이블 전체 + 유저정보 + 좋아요 개수 + 조회수
# 정렬 기준 : 좋아요 개수
# best_not_enough 의 경우 좋아요가 있는 레시피의 개수가 10개 미만일 때 작동



# 레시피 리스트를 불러오는 함수 (옵션으로 검색이나 페이징 , 처리, 추천순 등 처리)

class RescipeListSeperateResource(Resource) :
    
    def get(self) : 
        # 파라미터 딕셔너리 형태로 가져오기
        params = request.args.to_dict()
        # 현재 파라미터로 고려중인 값 : 카테고리 종류("전체, 반찬 등"),정렬방식(좋아요, 최신, 조회순),검색어(선택),offset,limit
        list_type = params["list_type"]


        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)
            # 2. 해당 테이블, recipe 테이블에서 select
            query = list_type_map[list_type]
            
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            print(record_list)

            ### 중요. 파이썬의 시간은, JSON으로 보내기 위해서
            ### 문자열로 바꿔준다.
            # if record_list is None:
            #     print("저장된 메모 없음")
            #     memo_lenth = 0

            # else :
            i = 0
            for record in record_list:
                record_list[i]['created_at'] = record['created_at'].isoformat()
                record_list[i]['updated_at'] = record['updated_at'].isoformat()
                record_list[i]['date'] = record['date'].isoformat()
                i = i +1
            memo_lenth = len(record_list)



        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'error' : 500, 'count' : 0, 'list' : []}, HTTPStatus.INTERNAL_SERVER_ERROR
        # finally 는 try에서 에러가 나든 안나든, 무조건 실행하라는 뜻.
        finally : 
            print('finally')
            if connection.is_connected():
                cursor.close()
                connection.close()
                print('MySQL connection is closed')
            else :
                print('connection does not exist')
        return {'error' : 200, 'count' : memo_lenth, 'list' : record_list }, HTTPStatus.OK
