import logging

import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(root_dir, "logs")

if not os.path.exists(log_dir):
    os.mkdir(log_dir)


# 创建一个日志器
logger = logging.getLogger("logger")

# 设置日志输出的最低等级,低于当前等级则会被忽略
logger.setLevel(logging.INFO)

# 创建处理器：sh为控制台处理器，fh为文件处理器
sh = logging.StreamHandler()

# 创建处理器：sh为控制台处理器，fh为文件处理器,log_file为日志存放的文件夹
# log_file = os.path.join(log_dir,"{}_log".format(time.strftime("%Y/%m/%d",time.localtime())))
log_file = os.path.join(log_dir, "telegram.log")
fh = logging.FileHandler(log_file, encoding="UTF-8")

# 创建格式器,并将sh，fh设置对应的格式
formator = logging.Formatter(fmt="%(asctime)s.%(msecs)03d - %(message)s",
                             datefmt="%Y/%m/%d %X")
sh.setFormatter(formator)
fh.setFormatter(formator)

# 将处理器，添加至日志器中
logger.addHandler(sh)
logger.addHandler(fh)

