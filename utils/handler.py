import redis,configparser
import traceback
import socket,datetime,logging
import json,os,collections


def cache(*args,**kwargs):
    r = redis.Redis(**kwargs)
    return r


def formatStr2Int(obj):
    if isinstance(obj,dict) and obj.get("port"):
        try:
            obj["port"] = int(obj.get("port"))
        except Exception as e:
            traceback.print_exc()
        finally:
            return obj


def getConfigInfo(configfile):
    config = configparser.ConfigParser()
    config.read(configfile)
    return config


def list2dict(listobj):
    dictobj = {}
    if isinstance(listobj,list):
        for i in listobj:
            try:
                key,value = i
                dictobj[key] = value
            except Exception as e:
                traceback.print_exc()
        else:
            return dictobj


def getIpAddr():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception as e:
        traceback.print_exc()
        print(e)
    finally:
        s.close()
    return ip


def schemaZabbixData(dataobj,itemName):
    """

    :param dataobj: process list
    :param itemName: PROCESS
    :return:
    {
    "data": [

        {
            "{#PROCESS}": "2672 Neo.Cutt.App.LogParser.Runtime"
        },
        {
            "{#PROCESS}": "2597 Neo.Cutt.Zhiyue.DataServer.Runtime"
        },
        {
            "{#PROCESS}": "mysql"
        }
        ]
    }
    """
    data = []
    ret = {}
    if isinstance(dataobj,collections.Iterable):
        for line in dataobj:
            line = line.strip()
            data.append({itemName:line})
        ret["data"] = data
        return json.dumps(ret,sort_keys=True, indent=4)
    else:
        exit()


def _getProcCmdLine(pid):
    cmdline_filename = os.path.join("/proc",pid,"cmdline")
    if os.path.exists(cmdline_filename):
        with open(cmdline_filename) as fd:
            ret = fd.read().split("\x00")
            ret.reverse()
        for item in ret:
            if item.startswith("org.apache."):
                return item
        else:
            return None
    else:
        return None


def logger(loggername,level,msg):
    # get current datetime
    today = datetime.datetime.now().strftime("%Y-%d-%m")

    # create logger
    logger = logging.getLogger(loggername)
    logger.setLevel(logging.DEBUG)

    # create file handler and set level to warn
    fh = logging.FileHandler("logs/open-falcon.{0}.log".format(today))
    fh.setLevel(logging.INFO)

    # create formatter
    fmt = "%(asctime)-15s %(levelname)s %(filename)s %(lineno)d %(process)d %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # add formatter to fh and add fh to logger
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    """
    logger.debug("debug message")
    logger.info("info message")
    logger.warn("warn message")
    logger.error("error message")
    logger.critical("critical message")
    """

    if level == "debug":
        logger.debug(msg)
    elif level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    elif level == "critical":
        logger.critical(msg)
