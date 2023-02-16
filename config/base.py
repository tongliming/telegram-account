headers = {
    "Content-Type": "application/json;charset=UTF-8"
}
third_platform = {
    "qisms": {
        "get_phone_url": "https://api.qisms.com/api?name={}&pwd={}&act=getphone&appid={}",
        "get_code_url": "https://api.qisms.com/api?name={}&pwd={}&act=code&appid={}&number={}"
    }
}
db_config_dev = {
    "host": "192.168.1.34",
    "port": 3306,
    "db_name": "tg",
    "user": "root",
    "password": "root"
}
db_config_test = {
    "host": "",
    "port": 3306,
    "db_name": "tg",
    "user": "tg",
    "password": ""
}
db_config_prod = {
    "host": "154.91.227.174",
    "port": 3306,
    "db_name": "tg",
    "user": "tg",
    "password": ""
}
