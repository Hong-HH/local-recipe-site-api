from flask import request, json, Response
from flask.json import jsonify
from flask_restful import Resource
from http import HTTPStatus
import requests
import time

from mysql_connection import get_connection
from mysql.connector.errors import Error

from config import Config

from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests as google_requests

from functions_for_recipe import recipe_detail_query
from functions_for_users import get_external_id, get_refresh_token

import datetime


class ClassResource(Resource) :
    
    def get(self, class_id) : 
        # 요청한 레시피에 대한 상세정보 리턴하는 api

        start_time = time.time()
        params = request.args.to_dict()
        # 파라미터에서 external_type 가져오기
        # external_type = request.args.get('external_type')


        try :       
            # 1. db 접속
            connection = get_connection()
            cursor = connection.cursor(dictionary = True)

         # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        
        
        try :
        
            # 2. 해당 테이블, recipe 테이블에서 select
            query = ''' select c3.*, cg.name as category_name
                        from (select c2.*, ch.name, ch.email, ch.img, ch.desc, ch.details , ch.contact
                        from 
                        (select c1.* ,  ifnull(count(cph.created_at), 0) as participants
                        from 
                        (select * 
                        from class
                        where id = %s
                        ) as c1
                        left join class_purchase_history as cph
                        on c1.id = cph.class_id) as c2
                        left join class_host as ch
                        on c2.host_id = ch.id) as c3
                        left join category as cg
                        on c3.category = cg.id '''
            record = (class_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 0
            for record in record_list:
                time_required = record['time_required']                
                start_datetime = record['date_time']
                end_datetime = start_datetime +time_required
                # time_required 요청에 맞게 min 으로 변환
                time_min = int(time_required.total_seconds() / 60)

                # date "12월 25일" 
                date = str(start_datetime.month) + "월 " + str(start_datetime.day) + "일"

                # date_time  "10:30 ~ 11:20"

                start_min = str(start_datetime.minute)
                end_min = str(end_datetime.minute) 
                
                if start_min == "0" :
                    start_min = "00"
                if end_min == "0" :
                    end_min = "00"
                    

                date_time = str(start_datetime.hour) + ":" + start_min + " ~ "
                print(date_time)
                date_time = date_time +  str(end_datetime.hour) + ":" + end_min


                # print(type(record['time_required'])) //  <class 'datetime.timedelta'>
                
                recipe = {"id": record['id'],
                            "header_img":record['header_img'],
                            "header_title": record['header_title'],
                            "header_desc": record['header_desc'],
                            "price": record['price'],     
                            "time_required": time_min,                            
                            "date": date,
                            "date_time": date_time,
                            "email": record['email'],
                            "limit": record['maximum_participants'],
                            "place": record['place'],
                            "class_desc": record['intro'],
                            "classHost": {
                                            "img": record['img'],
                                            "desc": record['desc'],
                                            "details":record['details']
                                        },
                            "sales": record['participants']
                            }
                print("i의 값은" + str(i))
                i = i +1

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        
        
        try :
            print("class food 진입")
            query = '''  select * from class_food
                        where class_id = %s  
                        order by id;'''
            record = (class_id, )
            cursor.execute(query, record)
            # select 문은 아래 내용이 필요하다.
            # 커서로 부터 실행한 결과 전부를 받아와라.
            record_list = cursor.fetchall()
            i = 1
            food_list = []
            for record in record_list:
                food_list.append({ "name": record['name'] ,  "img": record['img'] , "order": i } )
                i = i + 1

            recipe["classFoods"] = food_list
 
        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

       

        # 유저가 로그인을 했다면 ... 좋아요 여부 리턴
        try :
            print("AuthType 진입")            
            if "AuthType" in request.headers:
                # 파라미터에서 external_type 가져오기
                external_type = request.args.get('external_type')
                token =  request.headers.get('Token') 

                id_result = get_external_id(external_type, token)

                if id_result["status"] == 200 :
                    external_id = id_result["external_id"]

                else :
                    # 나중에 통합한 토큰 재발급 함수 추가
                    print("토큰 만료")

                try :
                    query = recipe_detail_query["get_user_id"]
                    record = (external_id, )
                    cursor.execute(query, record)
                    # select 문은 아래 내용이 필요하다.
                    # 커서로 부터 실행한 결과 전부를 받아와라.
                    record_list = cursor.fetchall()
                    user_id = record_list[0]["user_id"]
                except Error as e :
                    # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
                    print('Error while connecting to MySQL', e)
                    return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  


                # 2. 해당 테이블에서 select
                query = '''  select * from class_purchase_history
                                where user_id = %s and class_id =  %s;  '''
                record = (user_id, class_id )
                cursor.execute(query, record)
                # select 문은 아래 내용이 필요하다.
                # 커서로 부터 실행한 결과 전부를 받아와라.
                record_list = cursor.fetchall()
                
                if len(record_list) == 1 :
                    recipe["isPurchased"]= True
                    
                else :
                    recipe["isPurchased"]= False


            else :
                recipe["isPurchased"] = False

        # 3. 클라이언트에 보낸다. 
        except Error as e :
            # 뒤의 e는 에러를 찍어라 error를 e로 저장했으니까!
            print('Error while connecting to MySQL', e)
            return {'status' : 500 ,'message' : str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR  



        # finally 는 try에서 에러가 나든 안나든, 무조건 실행하라는 뜻.
        finally : 
            print('finally')
            if connection.is_connected():
                cursor.close()
                connection.close()
                print('MySQL connection is closed')
            else :
                print('connection does not exist')

            print("---{}s seconds---".format(str(time.time()-start_time)))

        return {'status' : 200, 'recipeInfo' : recipe }, HTTPStatus.OK



    