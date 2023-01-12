from flask import Flask, request, redirect
from flask.json import jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_jwt_extended.exceptions import RevokedTokenError
from jwt.exceptions import ExpiredSignatureError
from flask_cors import CORS 
import logging


from http import HTTPStatus
from urllib import parse

from config import Config
from resources.login import UserLoginResource
from resources.register import UserRegisterResource
from resources.recipe_list import RescipeListResource
from resources.recipe import RescipeResource
from resources.recipe_comment import RecipeCommentListResource, RecipeCommentResource
from resources.user_info import UserLikeRecipeResource, UserRecipeResource, UserPurchaseResource
from resources.likes import LikeResource
from resources.class_list import ClassListResource
from resources.class_detail import ClassResource


from mysql_connection import get_connection
from mysql.connector.errors import Error

from config import Config


from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests as google_requests


from functions_for_users import check_user, get_naver_profile, refresh_naver_token



#  버전 체크
import sys
from platform import python_version


app = Flask(__name__)

CORS(app, origins=["https://localhost:3000",  "https://myrecipetest.tk/" , "http://my-recipe-front.s3-website.ap-northeast-2.amazonaws.com"], supports_credentials=True)

# 환경 변수 세팅
app.config.from_object(Config)

# 로그아웃한 유저인지 확인하는 코드 
# @jwt.token_in_blocklist_loader
# def check_if_token_is_revoked(jwt_header, jwt_payload) :
#     print("Function check_if_token_is_revoked is activated")
#     jti = jwt_payload['jti']
#     result = check_blocklist(jti)
#     # True 일때 이미 로그아웃한 유저, False 일때 로그아웃 아직 안한 유저
#     print("check_blocklist 결과는 {} 입니다.".format(str(result)))
    
#     return result


# catch 하고싶은 에러 
CUSTOM_ERRORS = {
    'RevokedTokenError': {
        'message': "이미 로그아웃 되었습니다(401 Unauthorized).", 'status' : 401
    }, 
    'ExpiredSignatureError' : {
        'message': "jwt 토큰이 만료되었습니다. 다시로그인해주세요.", 'status' : 401
    }
}


api = Api(app, errors=CUSTOM_ERRORS)


# resources 와 연결

# 로그인 관련
api.add_resource(UserRegisterResource, '/v1/user/register')
api.add_resource(UserLoginResource, '/v1/user/login')
# api.add_resource(LogoutResource, '/v1/user/logout')

# 레시피 관련
api.add_resource(RescipeListResource, '/v1/recipe')
api.add_resource(RescipeResource, '/v1/recipe/<int:recipe_id>')
api.add_resource(RecipeCommentListResource, '/v1/recipe/<int:recipe_id>/comment')
api.add_resource(RecipeCommentResource, '/v1/comment/<int:comment_id>')

# 유저 정보 관련
api.add_resource(UserRecipeResource, '/v1/user/recipe')                              
api.add_resource(UserLikeRecipeResource,'/v1/user/likes' )
api.add_resource(UserPurchaseResource, '/v1/user/purchase')

# 좋아요 추가/삭제
api.add_resource(LikeResource, '/v1/like/<int:recipe_id>')

# 클래스 관련
api.add_resource(ClassListResource, '/v1/class')
api.add_resource(ClassResource, '/v1/class/<int:class_id>')





# 연결확인용 
@app.route("/" , methods=['POST','GET'])
def hello_world():
    if request.method =='GET':
        print(sys.version) 
        print(python_version())
        cooks =  request.cookies
        print (cooks)
        
        return "Hello, World!" 

    else : 

        return "<p>Hello, World! Do Not Post Here!!!</p>"



@app.before_request
def before_request() :
    print(request)
    print(type(request))  # <class 'werkzeug.local.LocalProxy'>
    print(request.path)

    if request.path == '/v1/user/register' :
        pass  

    # token 의 유효성 체크
    elif "AuthType" in request.headers:

        print("토큰 유효성 검사 시작")
        AuthType = request.headers.get("AuthType")
        token =  request.headers.get('Authorization') 

        if AuthType == "naver" :
            profile_result = get_naver_profile(access_token)

            if profile_result["result_code"] == "00" :
                pass
            else :
                # 토큰이 유효하지 않음으로 재발급 후 재검사
                refresh_token = request.headers.get('Rft')
                access_token = refresh_naver_token(refresh_token)
                profile_result = get_naver_profile(access_token)

                if profile_result["result_code"] == "00" :
                    pass
                else :
                    print("access token 발급에 문제 발생")
                    return {"status" : 500 , 'message' : "access token 발급에 문제 발생, 재로그인 필요"}, 500

        elif AuthType == "google" :
            print(token)
 
            # split_text = token.split(' ')
            # token = split_text[-1]
            token = token[7:]

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
                return {'status' : 500, 'message' : "id 토큰 유효성 검사에서 문제 생김, 재로그인 필요"}, 500




logging.getLogger('flask_cors').level = logging.DEBUG


@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Authtype')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE, OPTIONS')
  response.headers.add('Vary', 'Origin')
  return response

if __name__ == "__main__" :
    app.run()


