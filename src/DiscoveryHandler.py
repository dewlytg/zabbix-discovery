from utils import handler
import traceback,subprocess,json

_local_ip = handler.getIpAddr()
discovery_process_key = "".join(["cutt.vnode.process.", _local_ip])
discovery_port_key = "".join(["cutt.vnode.port.", _local_ip])
cutt_monitor_process_key = "cutt.process"


def getProcessList():
    try:
        command_output_all = ""
        r = cacheHandler()
        cuttprocess = r.lrange(cutt_monitor_process_key, 0, -1)
        for line in cuttprocess:
            line = line.strip().decode()
            if line == "vnode": #vnode process
                command_output = subprocess.getoutput(
                    "ps aux |grep %s|egrep -v 'grep|rotatelogs|py'|awk '{print $(NF-2),$(NF-1)}'" % line)
                command_output_all += command_output + "\n"
            else: # anther process
                command_status, command_output = subprocess.getstatusoutput(
                    "ps axu|grep %s|egrep -v 'grep|rotatelogs|py'" % line)
                if command_status == 0:
                    command_output = line + "\n"
                    command_output_all += command_output
        else:
            command_output_all = command_output_all.strip()
            command_output_all_list = command_output_all.split("\n")
        formated_data = handler.schemaZabbixData(command_output_all_list, "{#PROCESS}")
        _redisHandler(discovery_process_key, command_output_all_list, "{#PROCESS}", formated_data)
    except Exception as e:
        traceback.print_exc()
        print(e)


def getPortList():
    try:
        command_output_all = subprocess.getoutput(
            "ss -lnput|egrep -v '127.0.0.1|tcp6|snmp|ssh|10050'|awk '{print $5}'|awk -F '[ :]+' 'NR>1 {print $NF}'|sort |uniq").strip(
            "\n")
        command_output_all_list = command_output_all.split("\n")
        formated_data = handler.schemaZabbixData(command_output_all_list, "{#PORT}")
        _redisHandler(discovery_port_key,command_output_all_list,"{#PORT}",formated_data)
    except Exception as e:
        traceback.print_exc()
        print(e)


def _redisHandler(key,listobj,zabbix_macro,formated_data):
    r = cacheHandler()
    if r.get(key):
        port_data = json.loads(r.get(key))["data"]
        old_set = set()
        new_set = set(listobj)
        for i in port_data:
            old_set.add(list(i.values())[0])
        if new_set.difference(old_set):
            ret_list = list(old_set.union(new_set))
            new_formated_data = handler.schemaZabbixData(ret_list, zabbix_macro)
            r.set(key, new_formated_data)
        print(r.get(key).decode())
    else:
        r.set(key, formated_data)
        print(r.get(key).decode())


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


def cacheHandler():
    config = handler.getConfigInfo("./config/cutt.cfg")
    cache_info_list = config.items("cacheserver")
    cache_info_dict = handler.list2dict(cache_info_list)
    cache_connection = handler.formatStr2Int(cache_info_dict)
    r = handler.cache(**cache_connection)
    return r

