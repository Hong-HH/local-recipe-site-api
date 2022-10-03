from flask import Flask, request, redirect
from flask.json import jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_jwt_extended.exceptions import RevokedTokenError
from jwt.exceptions import ExpiredSignatureError

from http import HTTPStatus
from urllib import parse

from config import Config
from resource.login import UserLoginResource


app = Flask(__name__)

# 환경 변수 세팅
app.config.from_object(Config)

# JWT 토큰 만들기
jwt = JWTManager(app)

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

# api.add_resource(UserRegisterResource, '/v1/user/register')
api.add_resource(UserLoginResource, '/v1/user/login')
# api.add_resource(LogoutResource, '/v1/user/logout')



# 연결확인용 
@app.route("/" , methods=['POST','GET'])
def hello_world():
    if request.method =='GET':
        return "<p>Hello, World!</p>"
    else : 

        return "<p>Hello, World! Do Not Post Here!!!</p>"



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









if __name__ == "__main__" :
    app.run()


