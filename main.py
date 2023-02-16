import json

from flask import request
from flask_cors import CORS

from result.json_flask import JsonFlask
from result.json_response import JsonResponse
from telegram import api_service
from telegram.api_service import LOOP


app = JsonFlask(__name__)  # 初始化app
CORS(app, supports_credentials=True)


@app.route("/")  # 建立路由
def hello():
    return 'Hello World'


# 发送验证码
@app.route("/send_code")
def send_code():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    api_hash = request.args.get('apiHash')
    sign_task = LOOP.create_task(api_service.send_code(phone, api_id, api_hash))
    LOOP.run_until_complete(sign_task)
    return JsonResponse.success(sign_task.result())


# 客户端登录
@app.route('/login')  # 登录
def login():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    code = request.args.get('code')
    password = request.args.get('password')
    sign_task = LOOP.create_task(api_service.sign(phone, api_id, code, password))
    LOOP.run_until_complete(sign_task)
    return JsonResponse.success(sign_task.result())


# 获取登录用户信息
@app.route("/me")
def info():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    get_me_task = LOOP.create_task(api_service.get_me(phone, api_id))
    LOOP.run_until_complete(get_me_task)
    return JsonResponse.success(get_me_task.result())


# 三方登录获取手机号
@app.route("/third/phone")
def third_phone():
    platform = request.args.get('platform')
    user = request.args.get('user')
    password = request.args.get('password')
    appid = request.args.get('appid')
    result = api_service.get_third_phone(platform, user, password, appid)
    return JsonResponse.success(result)


# 三方登录获取验证码
@app.route("/third/code")
def third_code():
    platform = request.args.get('platform')
    user = request.args.get('user')
    password = request.args.get('password')
    appid = request.args.get('appid')
    phone = request.args.get('phone')
    result = api_service.get_third_code(platform, user, password, appid, phone)
    return JsonResponse.success(result)


# 判断手机号是否注册TG账号
@app.route("/check/register")
def check_register():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    target = request.args.get('target')
    check_register_task = LOOP.create_task(api_service.check_register_tg(phone, api_id, target))
    LOOP.run_until_complete(check_register_task)
    return JsonResponse.success(check_register_task.result())


# 修改TG账号 username
@app.route("/update/username")
def update_username():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    username = request.args.get('username')
    update_username_task = LOOP.create_task(api_service.update_username_tg(phone, api_id, username))
    LOOP.run_until_complete(update_username_task)
    return JsonResponse.success()


# 修改TG账号 profile
@app.route("/update/profile")
def update_profile():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    firstname = request.args.get('firstname')   # 名
    lastname = request.args.get('lastname')     # 性
    update_profile_task = LOOP.create_task(api_service.update_profile_tg(phone, api_id, firstname, lastname))
    LOOP.run_until_complete(update_profile_task)
    return JsonResponse.success()


# 修改TG账号 password
@app.route("/update/password")
def update_password():
    phone = request.args.get('phone')
    api_id = request.args.get('apiId')
    old_psw = request.args.get('oldPsw')
    new_psw = request.args.get('newPsw')
    update_password_task = LOOP.create_task(api_service.update_password_tg(phone, api_id, old_psw, new_psw))
    LOOP.run_until_complete(update_password_task)
    if update_password_task.result():
        return JsonResponse.success()
    return JsonResponse.error()


# 查询联系人状态
@app.route("/users/info", methods=["POST"])
def users_info():
    data = json.loads(request.data)  # 将json字符串转为dict
    phone = data['phone']
    api_id = data['apiId']
    users = data['users']
    get_users_task = LOOP.create_task(api_service.get_users_tg(phone, api_id, users))
    LOOP.run_until_complete(get_users_task)
    return JsonResponse.success(get_users_task.result())


# 查询消息列表
@app.route("/message/code")
def message_code():
    phone = request.args.get('phone')
    message_list_task = LOOP.create_task(api_service.message_code_tg(phone))
    LOOP.run_until_complete(message_list_task)
    return JsonResponse.success(message_list_task.result())


@app.errorhandler(Exception)
def error_handler(e):
    """
    全局异常捕获，也相当于一个视图函数
    """
    return JsonResponse.error(msg=str(e))


if __name__ == '__main__':
    app.run(port=5001, host='0.0.0.0')  # 运行app
