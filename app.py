from flask import Flask, request
from flask.json import jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_jwt_extended.exceptions import RevokedTokenError
from jwt.exceptions import ExpiredSignatureError

from http import HTTPStatus

from config import Config



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
# api.add_resource(UserLoginResource, '/v1/user/login')
# api.add_resource(LogoutResource, '/v1/user/logout')



# 연결확인용 
@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


if __name__ == "__main__" :
    app.run()


