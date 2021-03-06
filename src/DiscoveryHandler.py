from utils import handler
import traceback,json,time,requests,sys
from utils.handler import query_sql

try:
    if sys.version_info  > (3, 0):
        import subprocess as sbprocess
    else:
        import commands as sbprocess
except Exception:
    traceback.print_exc()


"""
本程序用于监控指定进程：
1.普通进程监控方式，ss -lnpt |grep PROCESSNAME 此命令一两个作用，一个是发现进程是否存在，第二个必须要listen TCP端口，才认为是存在
2.java进程监控方式，首先通过ps aux|grep PROCESSNAME 判断进程是存在并且获取进程ID，其次通过 jps 过滤出进程ID是否存在，如果存在才认识进程存在
3.自定义vnode进程监控方式如下：

因为这里监控java需要在agent上都安装jps，所以这里暂时不监控java进程
"""

_local_ip = handler.getIpAddr()
_hostname = sbprocess.getoutput("echo $HOSTNAME")
discovery_process_key = "".join(["cutt.vnode.process.", _local_ip])
discovery_mysql_name = "".join(["cutt.mysql.name.", _local_ip])
discovery_port_key = "".join(["cutt.vnode.port.", _local_ip])
cutt_monitor_process_key = "cutt.process"
java_process_list = ["kafka"] # java 进程监控方式有所不同


def getProcessList():
    """
    get current process which named vnode and judge is a active !
    :return:
    """
    try:
        command_output_all = ""
        r = cacheHandler()
        cuttprocess = r.lrange(cutt_monitor_process_key, 0, -1)
        for line in cuttprocess:
            line = line.strip().decode()
            if line == "vnode": #vnode process
                command_output = sbprocess.getoutput(
                    "ps aux |grep '/var/neo/vnode/vnode'|egrep -v 'grep|rotatelogs|py'|awk '{print $(NF-2),$(NF-1)}'")
                command_output_all += command_output + "\n"
            # elif line in java_process_list: #java process
            #     jps_status,jps_output = sbprocess.getstatusoutput("jps -q")
            #     if jps_status == 0:
            #         jps_list = jps_output.split("\n")
            #         command_status, command_output = sbprocess.getstatusoutput("ps axu|grep %s|egrep -v 'grep|rotatelogs|py'|awk '{print $2}'" % line)
            #         process_list = command_output.split("\n")
            #         if set(jps_list).intersection(set(process_list)):
            #             command_output = line + "\n"
            #             command_output_all += command_output
            else: # anther process
                command_status, command_output = sbprocess.getstatusoutput("ss -lnpt|grep %s" % line)
                if command_status == 0:
                    command_output = line + "\n"
                    command_output_all += command_output
        else:
            command_output_all = command_output_all.strip()
            command_output_all_list = command_output_all.split("\n")
        ret = _redisHandler(discovery_process_key, command_output_all_list, "{#PROCESS}") # thought redishandler to  union last vnode list and new vnode list
        if ret:push_metric_to_falcon(ret)
    except Exception as e:
        traceback.print_exc()
        print(e)


def getPortList():
    try:
        command_output_all = sbprocess.getoutput(
            "ss -lnput|egrep -v '127.0.0.1|tcp6|snmp|ssh|10050'|awk '{print $5}'|awk -F '[ :]+' 'NR>1 {print $NF}'|sort |uniq").strip(
            "\n")
        command_output_all_list = command_output_all.split("\n")
        _redisHandler(discovery_port_key,command_output_all_list,"{#TCP_PORT}")
    except Exception as e:
        traceback.print_exc()
        print(e)


def _redisHandler(key,listobj,zabbix_macro):
    """
    this function is order to add business data into redis and if it has exist in redis,to union last data and new data
    :param key:
    :param listobj:
    :param zabbix_macro:
    :return:
    """
    r = cacheHandler()
    if r.get(key):
        last_data = json.loads(r.get(key))["data"]
        old_set = set()
        new_set = set(listobj)
        for i in last_data:
            old_set.add(list(i.values())[0])
        listobj = list(old_set.union(new_set))
        new_formated_data = handler.schemaZabbixData(listobj, zabbix_macro)
        r.set(key, new_formated_data)
        print(r.get(key).decode())
    else:
        new_formated_data = handler.schemaZabbixData(listobj, zabbix_macro)
        r.set(key, new_formated_data)
        print(r.get(key).decode())
    return listobj


def purgeProcessList():
    try:
        discovery_key = "".join(["cutt.vnode.process.", _local_ip])
        r = cacheHandler()
        r.delete(discovery_key)
    except Exception as e:
        traceback.print_exc()
        exit(e)


def purgePortList():
    try:
        discovery_key = "".join(["cutt.vnode.port.", _local_ip])
        r = cacheHandler()
        r.delete(discovery_key)
    except Exception as e:
        traceback.print_exc()
        exit(e)


def push_metric_to_falcon(list_iter):
    try:
        ts = int(time.time())
        info_list = []
        for line in list_iter:
            command_status, command_output = sbprocess.getstatusoutput("ps axu|grep '%s'|egrep -v 'grep|rotatelogs|py'" % line)
            value = 0 if command_status else 1
            if "Neo" in line:
                vnode_id, vnode_name = line.split()
                dict_info = {"endpoint": _hostname,
                             "metric": vnode_name,
                             "timestamp": ts,
                             "step": 60,
                             "value": value,
                             "counterType": "GAUGE",
                             "tags": "vnode_id=%s, srv=vnode" % str(vnode_id)}
            else:
                dict_info = {"endpoint": _hostname,
                             "metric": line,
                             "timestamp": ts,
                             "step": 60,
                             "value": value,
                             "counterType": "GAUGE",
                             "tags": "name=%s, srv=common-service" % line}
            info_list.append(dict_info)
        requests.post("http://%s:1988/v1/push" % _local_ip, data=json.dumps(info_list))
        handler.logger("push","info","vnode process has push over...")
    except Exception:
        traceback.print_exc()


def cacheHandler():
    config = handler.getConfigInfo("./config/cutt.cfg")
    cache_info_list = config.items("cacheserver")
    cache_info_dict = handler.list2dict(cache_info_list)
    cache_connection = handler.formatStr2Int(cache_info_dict)
    r = handler.cache(**cache_connection)
    return r


def getDbNameInfoList():
    """
    get all db name which do you want to monitoring!
    :return:
    """
    try:
        command_output_all = ""
        config = handler.getConfigInfo("./config/db.cfg")
        db_name_list = config.sections()
        for line in db_name_list:
            command_output = line + "\n"
            command_output_all += command_output
        else:
            command_output_all = command_output_all.strip()
            command_output_all_list = command_output_all.split("\n")
            _redisHandler(discovery_mysql_name, command_output_all_list, "{#DBNAME}")
    except Exception as e:
        traceback.print_exc()
        print(e)


def get_metric_info(dbname,metric):
    config = handler.getConfigInfo("./config/db.cfg")
    connect_info = dict(config[dbname].items())

    if "port" in connect_info:
        connect_info["port"] = int(connect_info["port"])
    sql = "show status like '%s';" % metric
    query_result = query_sql(sql, **connect_info)
    metric_info = query_result[0][1]
    print(metric_info)
    return