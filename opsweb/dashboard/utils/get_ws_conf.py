#!/usr/bin/env python
#coding=utf8

import os
import configparser,traceback

wsconf = configparser.ConfigParser()

def get_myconf(config_name='/root/.ws-ops.conf',section=''):

    ret = {"result":0,"msg":None}

    try:
        wsconf.read(config_name)
    except Exception as e:
        ret["result"] = 1
        ret["msg"] = e.args
        return ret

    try:
        mysec_conf = wsconf.items(section)
    except configparser.NoSectionError:
        ret["result"] = 1
        ret["msg"] = "本地配置文件中不存在这个section: %s" %(section)
    except Exception as e:
        ret["result"] = 1
        ret["msg"] = e.args
    else:
        ret["mysec_conf"] = dict(mysec_conf)
    return ret

if __name__ == '__main__':
    haha = get_myconf(section="ldap_config")
    print(haha["result"])
    print(haha)
