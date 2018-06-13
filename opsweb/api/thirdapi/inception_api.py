
import pymysql
import time
from sqlmanager.models import SQLCheckTmpModel,SQLExecDetailModel
from dashboard.utils.wslog import wslog_error,wslog_info

class InceptionApi(object):
    def __init__(self,user,password,host,db_name,sql_str='',port=3306):
        self.user = user
        self.password = password
        self.host = host
        self.db_name = db_name
        self.port = port
        self.sql_str = sql_str

    ''' 连接 inception 服务端 '''
    def inception_server(self,sql):
        ret = {"result":0,"sql_err":0}
        try:
            ''' 连接 inception 服务端 '''
            conn = pymysql.connect(host='172.17.134.34',user='',passwd='',db='',port=6669,charset='utf8')
            cur = conn.cursor()
            cur.execute(sql)
            inc_result = cur.fetchall()
            # num_fields = len(cur.description)
            # field_names = [i[0] for i in cur.description]
            # print(field_names)
            # for row in inc_result:
            #     print(row)
            cur.close()
            conn.close()
        except pymysql.Error as e:
            ret["result"] = 1
            ret["msg"] = "连接 Inception 服务端执行SQL错误，错误信息 %d: %s" % (e.args[0], e.args[1])
            wslog_error().error("连接 Inception 服务端执行SQL错误，错误信息 %d: %s" % (e.args[0], e.args[1]))
        else:
            ret["inc_result"] = inc_result

        return ret

    ''' 连接 inception 备份服务器 '''
    def inception_backup_server(self,sql):
        ret = {"result":0}
        try:
            conn = pymysql.connect(host=self.host,user=self.user,passwd=self.password,db=self.db_name,port=self.port,charset='utf8')
            cur = conn.cursor()
            cur.execute(sql)
            backup_select_result = cur.fetchall()
            cur.close()
            conn.close()
        except pymysql.Error as e:
            ret["result"] = 1
            ret["msg"] = "连接 Inception 备份服务器执行SQL错误，错误信息 %d: %s" % (e.args[0], e.args[1])
            wslog_error().error("连接 Inception 备份服务器执行SQL错误，错误信息 %d: %s" % (e.args[0], e.args[1]))
        else:
            ret["backup_select_result"] = backup_select_result

        return ret

    ''' 仅用来检查 SQL的语法格式，并写入临时表 '''
    def inception_check(self):
        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-check;--port=%s;*/
                inception_magic_start;
                use %s;
                %s 
                inception_magic_commit;''' %(self.user,self.password,self.host,self.port,self.db_name,self.sql_str)

        ret = self.inception_server(sql)

        if ret["result"] == 1:
            wslog_error().error(ret["msg"])
            return ret
        inc_check_result = ret["inc_result"]
        sql_check_uuid = round(time.time() * 1000000)

        for s in inc_check_result[1:]:
            if s[4] == 'None':
                sql = s[5]
                try:
                    sct_obj = SQLCheckTmpModel(**{"sql_check_uuid":sql_check_uuid,"errmsg": s[4], "sql_detail": sql, "affected_rows": s[6]})
                    sct_obj.save()
                except Exception as e:
                    ret["result"] = 1
                    ret["msg"] = "SQLCheckTmpModel 保存对象失败,错误信息: %s" %(e.args)
                    wslog_error().error("SQLCheckTmpModel 保存对象失败,错误信息: %s" %(e.args))
                    break
            else:
                sql = s[5].split(";")[0]
                ret["sql_err"] = 1
                try:
                    sct_obj = SQLCheckTmpModel(**{"sql_check_uuid":sql_check_uuid,"errmsg": s[4], "sql_detail": sql, "affected_rows": s[6]})
                    sct_obj.save()
                except Exception as e:
                    ret["result"] = 1
                    ret["msg"] = "SQLCheckTmpModel 保存对象失败,错误信息: %s" %(e.args)
                    wslog_error().error("SQLCheckTmpModel 保存对象失败,错误信息: %s" %(e.args))
                break

        ret["sql_check_uuid"] = sql_check_uuid

        return ret

    ''' 用来拆分SQL(将一大段语句块拆成单条SQL),并写入相关表中，执行时使用；
        之所以要拆分SQL是因为如果中间某个SQL执行出错，那么这个错误SQL后面的SQL可以自定义"继续执行"或者"放弃执行"；
        如果不拆分 SQL 的话，那错误SQL及其后面的SQL就是一坨了，没办法去个性化定义如何执行 '''
    def inception_check_to_split(self,sql_obj):
        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-check;--port=%s;*/
                inception_magic_start;
                use %s;
                %s 
                inception_magic_commit;''' %(self.user,self.password,self.host,self.port,self.db_name,self.sql_str)

        ret = self.inception_server(sql)

        if ret["result"] == 1:
            wslog_error().error(ret["msg"])
            return ret
        inc_check_result = ret["inc_result"]
        del ret["inc_result"]

        for s in inc_check_result[1:]:
            try:
                se_obj = SQLExecDetailModel(**{"sql":s[5]+';',"sql_block":sql_obj,"check_affected_rows": s[6]})
                se_obj.save()
            except Exception as e:
                ret["result"] = 1
                wslog_error().error("SQL 拆分时 SQLExecDetailModel 保存对象失败,错误信息: %s" %(e.args))
                break
        return ret

    ''' 通过inception执行SQL(包含备份<回滚语句>)'''
    def inception_exec(self):

        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-execute;--port=%s;*/
                inception_magic_start;
                use %s;
                %s
                inception_magic_commit;''' % (self.user, self.password, self.host, self.port, self.db_name, self.sql_str)

        return self.inception_server(sql)

    '''打印SQL语法树，可以分析出语句的类型(insert/update/delete)和设计的库及表,仅仅支持DML(insert,update,delete)'''
    def inception_query_tree(self):
        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-query-print;--port=%s;*/
                inception_magic_start;
                use %s;
                %s
                inception_magic_commit;''' % (self.user, self.password, self.host, self.port, self.db_name, self.sql_str)

        return self.inception_server(sql)

    '''在一个语句块中包含对同一个表的 DDL 和 DML，会将这个语句块拆分成 DDL 和 DML 两种类型，但是并不检查语法错误，也不会执行，仅仅是拆分而已'''
    def inception_split(self):
        sql = '''/*--user=%s;--password=%s;--host=%s;--enable-split;--port=%s;*/
                   inception_magic_start;
                   use %s;
                   %s
                   inception_magic_commit;''' % (self.user, self.password, self.host, self.port,self.db_name,self.sql_str)

        return self.inception_server(sql)


if __name__ == '__main__':
    sql_str = '''
            insert into mytest.log123 (id,operator,operation_type,operation_result,delete_mark,gmt_create,gmt_modified,reference_id,content) VALUES (2,'bb',1,1,0,now(),now(),1234567,'hehehe');
            '''
    inc_obj = InceptionApi("root","123456","172.17.134.23","mytest",sql_str)

    inc_obj.inception_exec()