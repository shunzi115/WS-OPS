#!/usr/bin/env python
#-*-coding: utf-8-*-


import MySQLdb

class InceptionApi(object):
    def __init__(self,user,password,host,sql_str,port=3306):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.sql_str = sql_str

    def inception_server(self,sql):
        try:
            conn=MySQLdb.connect(host='172.17.134.34',user='',passwd='',db='',port=6669,charset='utf8')
            cur=conn.cursor()
            ret=cur.execute(sql)
            result=cur.fetchall()
            num_fields = len(cur.description)
            field_names = [i[0] for i in cur.description]
            print(field_names)
            for row in result:
                print(row[0], "|",row[1],"|",row[2],"|",row[3],"|",row[4],"|",
                row[5],"|",row[6],"|",row[7],"|",row[8],"|",row[9],"|",row[10])
            cur.close()
            conn.close()
        except MySQLdb.Error as e:
             print("Mysql Error %d: %s" % (e.args[0], e.args[1]))

    def inception_check(self):
        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-check;--port=%s;--enable-ignore-warnings;*/
                inception_magic_start;
                %s 
                inception_magic_commit;''' %(self.user,self.password,self.host,self.port,self.sql_str)

        self.inception_server(sql)

    def inception_exec(self):
        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-execute;--port=%s;*/
                inception_magic_start;
                %s
                inception_magic_commit;''' % (self.user, self.password, self.host, self.port, self.sql_str)

        self.inception_server(sql)

if __name__ == '__main__':
    sql_str = '''
                    CREATE TABLE mytest.idc_test (
                        id int(11) NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                        status smallint(1) NOT NULL DEFAULT '0' COMMENT '商品价格数据状态（0-未同步；1-已同步）',
                        PRIMARY KEY (id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品价格信息表（价格信息为增量更新，当匹配不上商品或入库失败时，要做下数据临时保存，避免数据丢失）';
              '''

    ia = InceptionApi("root","123456","172.17.134.23",sql_str)
    ia.inception_exec()
