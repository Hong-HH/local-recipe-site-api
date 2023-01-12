from flask import Flask, request, redirect ,  json, Response
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


app = Flask(__name__)
#  CORS 에러 
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
        return "<p>Hello, World!</p>"
    else : 

        return "<p>Hello, World! Do Not Post Here!!!</p>"


# 쿠키확인용2
@app.route("/a")
def hello_cookie():
    if request.method =='GET':
        print("상태 1 도달")
        resp = Response(
                        response=json.dumps({'status' : 200 , 
                                            'message' : "success"}),
                                status=200,
                                mimetype="application/json"
                                )
        print("상태 2 도달")
        print(resp)
        print("상태 3 도달")
        # 보내줄때 쿠키에 refresh 토큰
        resp.set_cookie('Token', "test-token" )
        return resp


@app.route("/naver" )
def naver_login():
    #  code 획득을 위한 임시 프론트
      
    client_id = Config.NAVER_LOGIN_CLIENT_ID
    redirect_uri = Config.LOCAL_URL + "v1/user/login"
    state = parse.quote('no_error_plz')
    print(state)


    url = "https://nid.naver.com/oauth2.0/authorize?"
    url = url + "response_type=code"
    url = url + "&client_id=" + client_id
    url = url + "&redirect_uri="+redirect_uri 
    url = url + "&state=" +  state
    
    
    
    print(url)

    return redirect(url)



@app.route("/google" )
def google_login():
    #  code 획득을 위한 임시 프론트


    client_id = Config.GOOGLE_LOGIN_CLIENT_ID
    redirect_uri =  Config.LOCAL_URL + "v1/user/login"
    
    # 값이 부족하다면 &scope=profile 로 값을 변경해보자. 현재는 &scope=https://www.googleapis.com/auth/userinfo.profile
    # scope=openid%20profile%20email

    url = Config.GOOGLE_LOGIN_CODE
    url = url + "response_type=code" + "&access_type=offline&" + "&scope=openid%20profile%20email"
    url = url + "&client_id=" + client_id + "&redirect_uri=" + redirect_uri

    print("url      :")
    print(url)

    return redirect(url)



logging.getLogger('flask_cors').level = logging.DEBUG


@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Authtype')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE, OPTIONS')
  response.headers.add('Vary', 'Origin')
  return response


if __name__ == "__main__" :
    app.run()


