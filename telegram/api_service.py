import asyncio

import pymysql
import requests
import socks
import nest_asyncio
from telethon import TelegramClient
from telethon.errors import ApiIdInvalidError, AuthRestartError, ApiIdPublishedFloodError, InputRequestTooLongError, \
    PhoneNumberAppSignupForbiddenError, PhoneNumberBannedError, PhoneNumberFloodError, PhoneNumberInvalidError, \
    SessionPasswordNeededError, PhoneCodeEmptyError, PhoneCodeExpiredError, PhoneCodeInvalidError, \
    PhoneNumberUnoccupiedError, PhonePasswordProtectedError, AboutTooLongError, FirstNameInvalidError, \
    UsernameInvalidError, UsernameOccupiedError, UsernameNotModifiedError, RegIdGenerateFailedError, \
    PhoneNumberOccupiedError, MemberOccupyPrimaryLocFailedError
from telethon.tl.functions.account import UpdateUsernameRequest, UpdateProfileRequest
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.functions.users import GetUsersRequest
from telethon.tl.types import InputUser, InputPhoneContact, User

from config.base import third_platform, headers, db_config_test, db_config_prod, db_config_dev
from config.log import logger
from telegram.client_model import ClientModel
from utils import deal_user

# 异步
nest_asyncio.apply()

TG_CLIENTS = {}
"""Telegram 客户端集合"""

TG_PARAMS = {}
"""Telegram 客户端参数"""

LOOP = asyncio.get_event_loop()


def __init():
    """初始化客户端"""
    logger.info(f'Connect mysql, host={db_config_prod["host"]}, port={db_config_prod["port"]}, db_name={db_config_prod["db_name"]}')
    conn = pymysql.connect(host=db_config_prod["host"],  # host属性
                           port=db_config_prod["port"],  # 端口号
                           user=db_config_prod["user"],  # 用户名
                           password=db_config_prod["password"],  # 此处填登录数据库的密码
                           db=db_config_prod["db_name"],  # 数据库名
                           charset='utf8'
                           )
    # 得到一个可以执行SQL语句的光标对象
    cursor = conn.cursor()
    sql = "SELECT BTA.phone, BTA.pwd, BD.api_id, BD.api_hash FROM `biz_tg_account` BTA, `biz_device` BD " \
          "WHERE BTA.api_id = BD.api_id AND BD.del_flag = 0 AND BD.`status` = '1' AND BTA.del_flag = 0"
    # 执行SQL语句
    cursor.execute(sql)
    # 获取所有记录列表
    results = cursor.fetchall()
    for row in results:
        phone = row[0]
        password = row[1]
        api_id = row[2]
        api_hash = row[3]
        client_model = ClientModel()
        client_model.api_id = api_id
        client_model.api_hash = api_hash
        client_model.phone_number = phone
        client_model.password = password
        key = "{}_{}".format(str(api_id), phone)
        TG_PARAMS[key] = client_model
        if key not in TG_CLIENTS:
            logger.info(f'Init telegram client, api_id={api_id}, api_hash={api_hash}, phone={phone}')
            TG_CLIENTS[key] = TelegramClient(key, api_id, api_hash) #, proxy=(socks.HTTP, '127.0.0.1', 4780))
    # 关闭光标对象
    cursor.close()
    # 关闭数据库连接
    conn.close()


def __delete_tg(key: str):
    if key in TG_CLIENTS:
        del TG_CLIENTS[key]
    if key in TG_PARAMS:
        del TG_PARAMS[key]


async def __connect_server():
    __init()
    for key in TG_CLIENTS:
        await TG_CLIENTS[key].connect()
        if TG_CLIENTS[key].is_connected():
            phone = TG_PARAMS[key].phone_number
            api_id = TG_PARAMS[key].api_id
            if not await TG_CLIENTS[key].is_user_authorized():
                logger.info(f'Init telegram client failed, need to login, api_id={api_id}, phone={phone}')
            else:
                logger.info(f'Init telegram client successful, api_id={api_id}, phone={phone}')
        else:
            logger.info(f'Init telegram client failed, delete client, api_id={api_id}, phone={phone}')
            __delete_tg(key)

# 执行coroutine
LOOP.run_until_complete(__connect_server())


async def send_code(phone: str, api_id: int, api_hash: str):
    logger.info(f'Send code: phone={phone}, api_id={api_id}, api_hash={api_hash}')
    """登陆前发送验证码"""
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        TG_CLIENTS[key] = TelegramClient(key, api_id, api_hash) #, proxy=(socks.HTTP, '127.0.0.1', 4780))

    try:
        await TG_CLIENTS[key].connect()
    except Exception as e:
        logger.info(f'Connect error, {e}')
        __delete_tg(key)
        raise Exception('客户端请求异常，请重试')

    if TG_CLIENTS[key].is_connected():
        try:
            result = await TG_CLIENTS[key].send_code_request(phone=phone)
            logger.info(result)
            """保存客户端信息"""
            client_model = ClientModel()
            client_model.api_id = api_id
            client_model.api_hash = api_hash
            client_model.phone_number = phone
            client_model.phone_code_hash = result.phone_code_hash
            TG_PARAMS[key] = client_model
        except ApiIdInvalidError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('当前 api_id/api_hash 组合无效')
        except ApiIdPublishedFloodError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('此 api_id 已在某处发布，您现在不能使用它')
        except AuthRestartError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('验证码发送失败，请重试')
        except InputRequestTooLongError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('验证码发送失败，请重试')
        except PhoneNumberAppSignupForbiddenError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('您无法使用此应用进行注册')
        except PhoneNumberBannedError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('该电话号码已被 Telegram 禁止。可查询 https://www.telegram.org/faq_spam')
        except PhoneNumberFloodError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('当日验证码发送次数已达上限，请24h之后再试')
        except PhoneNumberInvalidError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('该电话号码无效，请更换')
        except PhonePasswordProtectedError as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('该账号受密码保护，无法直接接收验证码')
        except Exception as e:
            logger.info(e)
            __delete_tg(key)
            raise Exception('验证码发送失败，请重试')

    else:
        """客户端连接失败，删除客户端实例"""
        logger.info(f'Connect server error')
        __delete_tg(key)
        raise Exception('系统请求异常，请重试')


# FirstNameInvalidError	The first name is invalid.
# MemberOccupyPrimaryLocFailedError	Occupation of primary member location failed.
# PhoneCodeEmptyError	The phone code is missing.
# PhoneCodeExpiredError	The confirmation code has expired.
# PhoneCodeInvalidError	The phone code entered was invalid.
# PhoneNumberFloodError	You asked for the code too many times..
# PhoneNumberInvalidError	The phone number is invalid.
# PhoneNumberOccupiedError	The phone number is already in use.
# RegIdGenerateFailedError	Failure while generating registration ID.
async def signup(phone: str, api_id: int, code: str, firstname: str, lastname: str):
    key = "{}_{}".format(str(api_id), phone)
    pch = TG_PARAMS[key].phone_code_hash
    logger.info(f'Sign up: phone={phone}, api_id={api_id}, code={code}, firstname={firstname}, lastname={lastname}, phone_code_hash={pch}')
    if key not in TG_CLIENTS:
        raise Exception("请先获取验证码")
    client = TG_CLIENTS[key]
    try:
        me = await client.sign_up(phone=phone, code=code, first_name=firstname, last_name=lastname, phone_code_hash=pch)
        logger.info(me)
    except FirstNameInvalidError as e:
        logger.info(e)
        raise Exception("名字非法，请替换")
    except MemberOccupyPrimaryLocFailedError as e:
        logger.info(e)
        raise Exception("主成员位置占用失败")
    except PhoneCodeExpiredError as e:
        logger.info(e)
        raise Exception("验证码已过期")
    except PhoneCodeInvalidError as e:
        logger.info(e)
        raise Exception("验证码无效")
    except PhoneCodeEmptyError as e:
        logger.info(e)
        raise Exception("验证码不能为空")
    except PhoneNumberFloodError as e:
        logger.info(e)
        raise Exception("验证码请求频繁")
    except PhoneNumberInvalidError as e:
        logger.info(e)
        raise Exception("电话号码无效")
    except PhoneNumberOccupiedError as e:
        logger.info(e)
        raise Exception("电话号码已注册")
    except RegIdGenerateFailedError as e:
        logger.info(e)
        raise Exception("生成注册 ID 失败")
    return deal_user.format(me)


async def sign(phone: str, api_id: int, code: str, password: str):
    key = "{}_{}".format(str(api_id), phone)
    pch = TG_PARAMS[key].phone_code_hash
    logger.info(f'Sign in: phone={phone}, api_id={api_id}, code={code}, password={password}, phone_code_hash={pch}')
    if key not in TG_CLIENTS:
        raise Exception("请先获取验证码")
    client = TG_CLIENTS[key]
    TG_PARAMS[key].password = password
    try:
        me = await client.sign_in(phone=phone, code=code, phone_code_hash=pch)
        logger.info(me)
    except SessionPasswordNeededError:
        if password is None:
            raise Exception('密码不能为空')
        me = await client.sign_in(password=password)
        logger.info(me)
        return deal_user.format(me)
    except PhoneCodeEmptyError as e:
        logger.info(e)
        raise Exception('验证码不能为空')
    except PhoneCodeExpiredError as e:
        logger.info(e)
        __delete_tg(key)
        raise Exception('验证码已过期，请重新获取验证码')
    except PhoneCodeInvalidError as e:
        logger.info(e)
        raise Exception('验证码错误，请重新输入')
    except PhoneNumberInvalidError as e:
        logger.info(e)
        __delete_tg(key)
        raise Exception('当前电话号码无效，请更换')
    except PhoneNumberUnoccupiedError as e:
        logger.info(e)
        # 注册
        return await signup(phone, api_id, code, str(api_id), phone)
    except Exception as e:
        logger.info(e)
        __delete_tg(key)
        raise Exception('系统请求异常，请重新获取验证码登录')
    return deal_user.format(me)


async def get_me(phone: str, api_id: int):
    logger.info(f'Get me: phone={phone}, api_id={api_id}')
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        raise Exception("该手机号不存在")
    client = TG_CLIENTS[key]
    me = await client.get_me()
    logger.info(me)
    return deal_user.format(me)


def get_third_phone(platform: str, user: str, password: str, appid: str):
    logger.info(f'Get third phone: platform={platform}, user={user}, password={password}, appid={appid}')
    if platform in third_platform:
        plat = third_platform[platform]
        try:
            res = requests.get(plat["get_phone_url"].format(user, password, appid),
                               headers=headers)
        except Exception as e:
            logger.info(e)
            raise Exception("三方解码平台接口调用失败")
        result = res.text
        if result:
            logger.info(result)
            arr_num = result.split("|")
            code = arr_num[0]  # 状态码：状态:0：成功，2：余额不足，3：申请不存在，4：项目可用号码不足,5:号码已被占用
            if code == '0':
                phone = '1' + arr_num[1]
            elif code == '2':
                raise Exception("三方解码平台余额不足")
            elif code == '3':
                raise Exception("三方解码平台项目不存在")
            elif code == '4':
                raise Exception("三方解码平台项目可用号码不足")
            elif code == '5':
                raise Exception("三方解码平台号码已被占用")
            else:
                raise Exception("三方解码平台接口调用失败")
            return phone
        else:
            raise Exception("三方解码平台接口调用失败")

    else:
        raise Exception("三方解码平台不存在")


def get_third_code(platform: str, user: str, password: str, appid: str, phone: str):
    logger.info(f'Get third code: platform={platform}, user={user}, password={password}, appid={appid}, phone={phone}')
    if platform in third_platform:
        plat = third_platform[platform]
        try:
            phone = phone[1:]
            res = requests.get(plat["get_code_url"].format(user, password, appid, phone),
                               headers=headers)
        except Exception as e:
            logger.info(e)
            raise Exception("三方解码平台接口调用失败")
        result = res.text
        logger.info(result)
        if result:
            arr_num = result.split("|")
            code = arr_num[0]
            # 状态码：状态0：成功收到验证码 1：未收到验证码 2：验证码获取超时或已释放，请重新获取 3：输入数据不正确。
            if code == '0':
                verification_code = arr_num[1]
            elif code == '1':
                raise Exception("三方解码平台未收到验证码")
            elif code == '2':
                raise Exception("三方解码平台验证码获取超时或已释放，请重新获取")
            elif code == '3':
                raise Exception("三方解码平台输入数据不正确")
            return verification_code
        else:
            return None
    else:
        raise Exception("三方解码平台不存在")


async def check_register_tg(phone: str, api_id: int, target: str) -> int:
    logger.info(f'Check register: phone={phone}, api_id={api_id}, target={target}')
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        raise Exception(f'{phone} 未登录，请登录客户端')
    contact = InputPhoneContact(client_id=0, phone=target, first_name=target, last_name=target)
    result = await TG_CLIENTS[key](ImportContactsRequest([contact]))
    logger.info(f'ImportContactsRequest: {result}')
    # if len(result.users) > 0:
    #     user_id = result.users[0].id
    #     access_hash = result.users[0].access_hash
    #     delete_result = await TG_CLIENTS[key](DeleteContactsRequest(
    #         id=[InputUser(user_id=user_id, access_hash=access_hash)]
    #     ))
    #     logger.info(f'DeleteContactsRequest: {delete_result}')
    if len(result.users) > 0:
        return deal_user.format(result.users[0])
    return None


async def update_username_tg(phone: str, api_id: int, username: str):
    logger.info(f'Update username: phone={phone}, api_id={api_id}, username={username}')
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        raise Exception(f'{phone} 未登录，请登录客户端')
    try:
        result = await TG_CLIENTS[key](UpdateUsernameRequest(
            username=username
        ))
        logger.info(result)
    except UsernameInvalidError as e:
        logger.info(e)
        raise Exception(f'用户名非法：{username}，只能是子母开头且只包含数字子母或下户线')
    except UsernameNotModifiedError as e:
        logger.info(e)
        raise Exception(f'用户名未修改：{username}')
    except UsernameOccupiedError as e:
        logger.info(e)
        raise Exception(f'已存在用户名：{username}')


async def update_profile_tg(phone: str, api_id: int, firstname: str, lastname: str):
    logger.info(f'Update profile: phone={phone}, api_id={api_id}, firstname={firstname}, lastname={lastname}')
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        raise Exception(f'{phone} 未登录，请登录客户端')
    try:
        result = await TG_CLIENTS[key](UpdateProfileRequest(
            first_name=firstname,
            last_name=lastname
        ))
        logger.info(result)
    except AboutTooLongError as e:
        logger.info(e)
        raise Exception("姓氏或名字超长")
    except FirstNameInvalidError as e:
        logger.info(e)
        raise Exception(f'名字无效，{firstname}')


async def update_password_tg(phone: str, api_id: int, old_psw: str, new_psw: str):
    logger.info(f'Update password: phone={phone}, api_id={api_id}, old_psw={old_psw}, new_psw={new_psw}')
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        raise Exception(f'{phone} 未登录，请登录客户端')
    client = TG_CLIENTS[key]
    result = await client.edit_2fa(current_password=old_psw, new_password=new_psw)
    logger.info(result)
    return result


async def get_users_tg(phone: str, api_id: int, users: dict):
    logger.info(f'Get users: phone={phone}, api_id={api_id}, users={users}')
    user_list = []
    for user in users:
        user_list.append(InputUser(user_id=int(user["userId"]), access_hash=int(user["accessHash"])))
    key = "{}_{}".format(str(api_id), phone)
    if key not in TG_CLIENTS:
        raise Exception(f'{phone} 未登录，请登录客户端')
    client = TG_CLIENTS[key]
    result = await client(GetUsersRequest(
        id=user_list
    ))
    user_result = []
    for u in result:
        logger.info(u)
        user_result.append(deal_user.format(u))
    return user_result


async def message_code_tg(phone):
    logger.info(f'Message code: phone={phone}')
    for key in TG_CLIENTS:
        if phone in key:
            if await TG_CLIENTS[key].is_user_authorized():
                client = TG_CLIENTS[key]
                # dialogs = await client.get_dialogs()
                # for dialog in dialogs:
                #     entity = dialog.entity
                #     message = dialog.message
                #     if entity is not None and message is not None:
                #         if entity.id == 777000:
                #             code_message = "{} {}".format(message.date.strftime("%Y-%m-%d %H:%M:%S"), message.message)
                #             logger.info(code_message)
                #             return code_message
                messages = client.iter_messages(777000, min_id=0, reverse=False, limit=10)
                messages_list = []
                async for message in messages:
                    logger.info(message)
                    code_message = "{} {}".format(message.date.strftime("%Y-%m-%d %H:%M:%S"), message.message)
                    messages_list.append(code_message)
                return messages_list
    return None
