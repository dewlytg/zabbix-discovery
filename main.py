#!/usr/bin/env python
#coding:utf-8

import os,sys
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from src.DiscoveryHandler import getProcessList,getPortList,purgeProcessList,purgePortList

def print_help():
    print("Function only support one parameter [process|purgeprocess|port]")

main_dict = {
    "process":getProcessList,
    "port":getPortList,
    "purgeprocess":purgeProcessList,
    "purgeport":purgePortList
}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_help()
        exit()
    else:
        if sys.argv[1] in main_dict:
            main_dict[sys.argv[1]]()