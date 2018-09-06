from utils import handler
import traceback,json,time,requests,sys

try:
    if sys.version_info  > (3, 0):
        import subprocess as sbprocess
    else:
        import commands as sbprocess
except Exception:
    traceback.print_exc()


_local_ip = handler.getIpAddr()
_hostname = sbprocess.getoutput("echo $HOSTNAME")
discovery_process_key = "".join(["cutt.vnode.process.", _local_ip])
discovery_port_key = "".join(["cutt.vnode.port.", _local_ip])
cutt_monitor_process_key = "cutt.process"


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
            else: # anther process
                command_status, command_output = sbprocess.getstatusoutput(
                    "ps axu|grep %s|egrep -v 'grep|rotatelogs|py'" % line)
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
        if new_set.difference(old_set):
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
                             "tags": "vnode_id:%s, srv=vnode" % str(vnode_id)}
            else:
                dict_info = {"endpoint": _hostname,
                             "metric": line,
                             "timestamp": ts,
                             "step": 60,
                             "value": value,
                             "counterType": "GAUGE",
                             "tags": "srv=common-service"}
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

