from django.views.generic import View,TemplateView,ListView
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from resources.models import ServerModel,IDC,CmdbModel
from resources.forms import ServerAliyunAddForm,ServerAliyunUpdateForm,ServerIdcAddForm,ServerIdcUpdateForm
from api.thirdapi.ansible_adhoc import ansible_adhoc
from api.thirdapi.aliyun_describe_instance import AliyunDescribeInstances,AliyunDescribeInstanceAutoRenewAttribute
from django.forms.models import model_to_dict
import json
from datetime import *
from dashboard.utils.utc_to_local import utc_to_local
from dashboard.utils.wslog import wslog_error,wslog_info
from django.db.models import Q


def GetServerInfoFromApi(private_ip,server_aliyun_obj):
    
    ret = {"result":0,"msg":None}
    
    try:
        server_info_aliyun = AliyunDescribeInstances(PrivateIpAddresses=[private_ip])[0]
    except Exception as e:
        ret["result"] = 1
        ret["msg"] = "aliyun api 调用失败，请查看日志"
        wslog_error().error(e.args)
        return ret

    try:
        server_aliyun_obj.public_ip = server_info_aliyun["PublicIpAddress"].get("IpAddress")[0] if server_info_aliyun["PublicIpAddress"].get("IpAddress") else server_info_aliyun["EipAddress"]["IpAddress"]
        server_aliyun_obj.instance_id = server_info_aliyun["InstanceId"]
        server_aliyun_obj.instance_name = server_info_aliyun["InstanceName"]
        server_aliyun_obj.region = server_info_aliyun["RegionId"]
        server_aliyun_obj.zone = server_info_aliyun["ZoneId"]
        server_aliyun_obj.instance_type = server_info_aliyun["InstanceType"]
        server_aliyun_obj.os_version = server_info_aliyun["OSName"]
        server_aliyun_obj.cpu_count = '%s 核' %(server_info_aliyun["Cpu"])
        server_aliyun_obj.mem = '%.2f GB' %(server_info_aliyun["Memory"]/1024.0)
        server_aliyun_obj.charge_type = server_info_aliyun["InstanceChargeType"]
        server_aliyun_obj.status = server_info_aliyun["Status"]
        server_aliyun_obj.online_time = server_info_aliyun["CreationTime"]
        server_aliyun_obj.expired_time = server_info_aliyun["ExpiredTime"]
    except Exception as e:
        ret["result"] = 1
        ret["msg"] = "aliyun api 某个属性失败，请查看日志"
        wslog_error().error(e.args)
        return ret

    server_renewal_status = AliyunDescribeInstanceAutoRenewAttribute(server_info_aliyun["InstanceId"])
    if server_info_aliyun["InstanceChargeType"] == 'PostPaid':
        server_aliyun_obj.renewal_type = 'RenewalByUsed'
    elif server_renewal_status["result"] == 1:
        ret["result"] = 1
        ret["msg"] = "aliyun api 获取续费状态失败，请查看日志"
        return ret
    else:
        server_aliyun_obj.renewal_type = server_renewal_status["data"]

    if server_aliyun_obj.status == 'Running': 
        try:
            if private_ip == '172.17.134.23':
                server_info_ansible = ansible_adhoc('setup','gather_subset=hardware',"127.0.0.1")["localhost"]['ansible_facts']
            else:
                server_info_ansible = ansible_adhoc('setup','gather_subset=hardware,!facter',private_ip)[private_ip]['ansible_facts']
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "ansible api 调用失败，请查看日志"
            print (e)
            wslog_error().error(e.args)
            return ret

        try:
            server_aliyun_obj.hostname = server_info_ansible['ansible_hostname']
            server_aliyun_obj.server_brand = server_info_ansible['ansible_system_vendor']
            server_aliyun_obj.swap = '%.2f GB' %(server_info_ansible['ansible_swaptotal_mb']/1024.0)
            server_aliyun_obj.disk = '</br>'.join(['['+i+'] '+': '+server_info_ansible['ansible_devices'][i]['size'] for i in server_info_ansible['ansible_devices'] if 'ss' in i or 'sd' in i or 'vd' in i])
            server_aliyun_obj.disk_mount = '\n'.join(['['+i['mount']+'] '+' - '+i['device']+' : %.2f GB' %(i['size_total']/1024.0/1024.0/1024.0) for i in server_info_ansible['ansible_mounts'] if i['device'].startswith('/dev')])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "ansible api 某个属性获取值失败，请查看日志"
            wslog_error().error(e.args)
            return ret

    try:
        server_aliyun_obj.save()
    except Exception as e:
        ret["result"] = 1
        ret["msg"] = "服务器信息刷新后保存数据库失败，请查看日志"
        wslog_error().error(e.args)
    else:
        ret["msg"] = "服务器信息刷新成功"

    return ret

class ServerAliyunListView(LoginRequiredMixin,ListView):
    template_name = "server/server_list.html"
    model = ServerModel
    paginate_by = 10
    ordering = 'id'
    page_total = 11

    def get_context_data(self,**kwargs):
        context = super(ServerAliyunListView,self).get_context_data(**kwargs)
        context['page_range'] = self.get_page_range(context['page_obj'])
        # request.GET 是获取QueryDict对象,也即是前端传过来的所有参数,由于QueryDict对象是只读的,所有要使用copy方法,赋值一份出来,才能进行修改
        search_data = self.request.GET.copy()
        try:
            search_data.pop('page')
        except:
            pass

        if search_data:
            context['search_uri'] = '&' + search_data.urlencode()
        else:
            context['search_uri'] = '' 
        # context.update(字典A) 是合并字典 context 和 A
        context.update(search_data.dict())
        return context

    # 过滤模型中的数据
    def get_queryset(self):
        queryset = super(ServerAliyunListView,self).get_queryset()
        queryset = queryset.exclude(private_ip__startswith="10.")

        search_name = self.request.GET.get('search',None)
        if search_name:
            queryset = queryset.filter(Q(private_ip__icontains=search_name)|Q(public_ip__icontains=search_name)|Q(hostname__icontains=search_name))
        return queryset
    
    # 获取要展示的页数范围,这里是固定显示多少页
    def get_page_range(self,page_obj):
        page_now = page_obj.number
        if page_obj.paginator.num_pages > self.page_total:
            page_start = page_now - self.page_total//2
            page_end = page_now + self.page_total//2 + 1

            if page_start <= 0:
                page_start = 1
                page_end = page_start + self.page_total
            if page_end > page_obj.paginator.num_pages:
                page_end = page_obj.paginator.num_pages + 1
                page_start = page_end - self.page_total
        else:
            page_start = 1
            page_end = page_obj.paginator.num_pages + 1

        page_range = range(page_start,page_end)
        return page_range

class ServerAliyunAddView(LoginRequiredMixin,View):

    def post(self,request):
        ret = {"result":0,"msg":None}
        server_aliyun_add_form = ServerAliyunAddForm(request.POST)
        if not server_aliyun_add_form.is_valid():
            ret["result"] = 1
            ret["msg"] = json.dumps(json.loads(server_aliyun_add_form.errors.as_json(escape_html=False)),ensure_ascii=False)
            return JsonResponse(ret)

        try:
            server_aliyun_obj = ServerModel(**server_aliyun_add_form.cleaned_data)
            server_aliyun_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
            return JsonResponse(ret)

        try:
            with open("/etc/ansible/hosts",'a+') as f:
                f.seek(0)
                if "%s\n" %(server_aliyun_obj.private_ip) not in f.readlines():
                    f.write("%s:%s\n" %(server_aliyun_obj.private_ip,server_aliyun_obj.ssh_port))
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
        else:
            ret["msg"] = "服务器 %s 添加成功" %(server_aliyun_add_form.cleaned_data.get("private_ip"))
        return JsonResponse(ret)

class ServerAliyunRefreshView(LoginRequiredMixin,View):
    
    def post(self,request):
        ret = {"result":0,"msg":None}
        server_id = request.POST.get("id",0)

        try:
            server_aliyun_obj = ServerModel.objects.get(id__exact=server_id)
        except ServerModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "该服务器ID %s 不存在，请刷新重试" %(server_id)
            return JsonResponse(ret)
        else:
            private_ip = server_aliyun_obj.private_ip
        
        ret = GetServerInfoFromApi(private_ip,server_aliyun_obj)

        return JsonResponse(ret)

class ServerAliyunInfoView(LoginRequiredMixin,View):

    def get(self,request):
        ret = {"result":0,"msg":None}
        sid = request.GET.get("id",0)
        try:
            server_aliyun_obj = ServerModel.objects.get(id__exact=sid)
        except ServerModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "Aliyun 上不存在 ID 为 %s 的服务器" %(sid)
            return JsonResponse(ret)

        try:
            #server_aliyun_info = model_to_dict(server_aliyun_obj)  // 使用这个方法,读不到 DateTimeField 设置为 auto_now = True 的字段,因此读不到 last_update_time 字段
            server_aliyun_info = ServerModel.objects.filter(id__exact=sid).values()[0]
            server_aliyun_info["env"] = {"id": server_aliyun_obj.env,"name": server_aliyun_obj.get_env_display()}
            server_aliyun_info["charge_type"] = server_aliyun_obj.get_charge_type_display()
            server_aliyun_info["status"] = server_aliyun_obj.get_status_display()
            server_aliyun_info["renewal_type"] = server_aliyun_obj.get_renewal_type_display()
            server_aliyun_info["disk"] = server_aliyun_info["disk"].replace("</br>","\n")
            if server_aliyun_info.get("expired_time"):
                server_aliyun_info["expired_time"] = utc_to_local(server_aliyun_info["expired_time"]).strftime("%Y-%m-%d %X")
            if server_aliyun_info.get("offline_time"):
                server_aliyun_info["offline_time"] = utc_to_local(server_aliyun_info["offline_time"]).strftime("%Y-%m-%d %X")
            if server_aliyun_info.get("online_time"):
                server_aliyun_info["online_time"] = utc_to_local(server_aliyun_info["online_time"]).strftime("%Y-%m-%d %X")
            if server_aliyun_info.get("last_update_time"):
                server_aliyun_info["last_update_time"] = utc_to_local(server_aliyun_info["last_update_time"]).strftime("%Y-%m-%d %X")
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "模型对象转dict失败" 
            wslog_error().error(e.args)
        else:
            ret["server_info"] = server_aliyun_info

        return JsonResponse(ret)

class ServerDeleteView(LoginRequiredMixin,View):
    
    def post(self,request):
        ret = {"result":0,"msg":None}
        sid = request.POST.get('id',0)

        try:
            server_obj = ServerModel.objects.get(id__exact=sid)
        except ServerModel.DoesNotExist:
            ret["result"] = 1
            ret["mag"] = "该服务器ID %s 不存在,请刷新重试" %(sid)
            return JsonResponse(ret)
        
        try:
            server_obj.delete()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
        else:
            ret["msg"] = "服务器 %s 删除成功" %(server_obj.private_ip)

        return JsonResponse(ret)

class ServerAliyunUpdateView(LoginRequiredMixin,View):

    def get(self,request):

        ret = {"result":0,"msg":None}
        server_info = {}
        sid = request.GET.get("id",0)

        try:
            server_aliyun_obj = ServerModel.objects.get(id__exact=sid)
        except ServerModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "Aliyun 上不存在 ID 为 %s 的服务器" %(sid)
            return JsonResponse(ret)

        try:
            server_info["id"] = sid
            server_info["private_ip"] = server_aliyun_obj.private_ip
            server_info["ssh_port"] = server_aliyun_obj.ssh_port   
            server_info["env"] = {"id": server_aliyun_obj.env,"name": server_aliyun_obj.get_env_display()}
            server_info["idc"] = {"id": server_aliyun_obj.idc.id,"name": server_aliyun_obj.idc.cn_name}
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "从模型 ServerAliyun 中获取 id 为 %s 的数据失败" %(sid)
        else:
            ret["server_info"] = server_info

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0,"msg":None}
        sid = request.POST.get('id',0)
        server_aliyun_update_form = ServerAliyunUpdateForm(request.POST)

        if not server_aliyun_update_form.is_valid():
            ret["result"] = 1
            ret["msg"] = json.dumps(json.loads(server_aliyun_update_form.errors.as_json(escape_html=False)),ensure_ascii=False)
            return JsonResponse(ret)

        try:
            server_aliyun_obj = ServerModel.objects.get(id__exact=sid)
        except ServerModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "服务器ID %s 不存在,请刷新重试" %(sid)
            return JsonResponse(ret)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
            return JsonResponse(ret)
        
        try:
            server_aliyun_obj.hostname = server_aliyun_update_form.cleaned_data.get("hostname")
            server_aliyun_obj.ssh_port = server_aliyun_update_form.cleaned_data.get("ssh_port")
            server_aliyun_obj.env = server_aliyun_update_form.cleaned_data.get("env")
            server_aliyun_obj.idc = server_aliyun_update_form.cleaned_data.get("idc")
            server_aliyun_obj.save(update_fields=["hostname","ssh_port","env","idc_id","last_update_time"])

        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
        else:
            ret["msg"] = "服务器 %s 更新成功" %(server_aliyun_obj.private_ip)

        return JsonResponse(ret)


def ServerAliyunAutoAdd():
    
    local_result = ServerModel.objects.exclude(private_ip__startswith="10.").values("private_ip")
    local_server_list = [i['private_ip'] for i in local_result]
    local_server_add = []
    local_server_delete = []

    try:
        aliyun_result = AliyunDescribeInstances()
    except Exception as e:
        wslog_error().error("服务器自动添加失败,错误信息: %s" %(e.args))
    else:
        aliyun_ecs_list = [i["NetworkInterfaces"]["NetworkInterface"][0]["PrimaryIpAddress"] for i in aliyun_result]
        local_server_add = list(set(aliyun_ecs_list).difference(set(local_server_list)))
        local_server_delete = list(set(local_server_list).difference(set(aliyun_ecs_list)))

    idc_obj = IDC.objects.get(pk=1)


    #添加服务器到本地 ServerModel 模型
    if local_server_add:
        for s in local_server_add:
            server = ServerModel()
            server.private_ip = s
            server.idc = idc_obj
            try:
                server.save()
            except Exception as e:
                wslog_error().error("自动添加服务器: %s,错误信息: %s" %(s,e.args))
                continue

            try:
                with open("/etc/ansible/hosts",'a+') as f:
                    f.seek(0)
                    if "%s\n" %(s) not in f.readlines():
                        f.write("%s\n" %(s))
            except Exception as e:
                wslog_error().error("自动添加服务器: %s,错误信息: %s" %(s,e.args))
                continue
            else:
                wslog_info().info("服务器: %s 自动添加成功" %(s))
                continue

    #将在阿里云上不存在的服务器,从本地的 ServerModel 模型中删除
    if local_server_delete:
        for s in local_server_delete:
            try:
                server_obj = ServerModel.objects.get(private_ip__exact=s)
            except ServerModel.DoesNostExist:
                wslog_error().error("自动删除服务器: %s ,已经不存在,所以不用删除" %(s))
                continue
            except Exception as e:
                wslog_error().error("自动删除服务器: %s,错误信息:%s" %(s,e.args))
                continue
            try:
                server_obj.delete()
            except Exception as e:
                wslog_error().error("自动删除服务器: %s,错误信息: %s" %(s,e.args))
                continue
            else:
                wslog_info().info("服务器: %s 自动删除成功" %(s))
                continue

class ServerIdcListView(LoginRequiredMixin,View):
    def get(self,resuest):
        server_idc_list = list(ServerModel.objects.filter(private_ip__startswith="10.").values('id','hostname','ssh_port','private_ip','env','os_version','cpu_count','mem','disk','idc_id','status','last_update_time'))
        for server in server_idc_list:
            server_obj = ServerModel.objects.get(id__exact=server["id"])
            server["env"] = server_obj.get_env_display()
            server["status"] = server_obj.get_status_display()
            server["idc_id"] = server_obj.idc.cn_name
            server["last_update_time"] = utc_to_local(server["last_update_time"]).strftime("%Y-%m-%d %X")

        return JsonResponse(server_idc_list,safe=False)

class ServerIdcAddView(LoginRequiredMixin,View):
    def post(self,request):
        ret = {"result":0,"msg":None}
        server_idc_add_form = ServerIdcAddForm(request.POST)

        if not server_idc_add_form.is_valid():
            ret["result"] = 1
            ret["msg"] = json.dumps(json.loads(server_idc_add_form.errors.as_json(escape_html=False)),ensure_ascii=False)
            return JsonResponse(ret)
        
        try:
            server_idc_obj = ServerModel(**server_idc_add_form.cleaned_data)
            server_idc_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
            return JsonResponse(ret)

        try:
            with open("/etc/ansible/hosts",'a+') as f:
                f.seek(0)
                if "%s\n" %(server_idc_obj.private_ip) not in f.readlines():
                    f.write("%s:%s\n" %(server_idc_obj.private_ip,server_idc_obj.ssh_port))
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
        else:
            ret["msg"] = "服务器 %s 添加成功" %(server_idc_add_form.cleaned_data.get("private_ip"))
        return JsonResponse(ret)

class ServerIdcUpdateView(LoginRequiredMixin,View):
    def get(self,request):
        ret = {"result":0,"msg":None}
        server_info = {}
        sid = request.GET.get("id",0)

        try:
            server_idc_obj = ServerModel.objects.get(id__exact=sid)
        except ServerModel.DoesNotExist:
            ret["msg"] = "模型 ServerModel 不存在 ID 为 %s 的对象,请刷新重试..." %(sid)
            return JsonResponse(ret)

        try:
            server_info["id"] = sid
            server_info["private_ip"] = server_idc_obj.private_ip
            server_info["ssh_port"] = server_idc_obj.ssh_port
            server_info["env"] = {"id": server_idc_obj.env,"name": server_idc_obj.get_env_display()}
            server_info["idc"] = {"id": server_idc_obj.idc.id,"name": server_idc_obj.idc.cn_name}
            server_info["sn_code"] = server_idc_obj.sn_code
            server_info["cabinet_num"] = server_idc_obj.cabinet_num
            server_info["idrac_ip"] = server_idc_obj.idrac_ip
            server_info["status"] = server_idc_obj.status
             
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "从模型 ServerModel 中获取 id 为 %s 的数据失败" %(sid)
        else:
            ret["server_info"] = server_info

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0,"msg":None}
        sid = request.POST.get('id',0)
        server_idc_update_form = ServerIdcUpdateForm(request.POST)

        if not server_idc_update_form.is_valid():
            ret["result"] = 1
            ret["msg"] = json.dumps(json.loads(server_idc_update_form.errors.as_json(escape_html=False)),ensure_ascii=False)
            return JsonResponse(ret)

        try:
            server_idc_obj = ServerModel.objects.get(id__exact=sid)
        except ServerModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "服务器ID %s 不存在,请刷新重试" %(sid)
            return JsonResponse(ret)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
            return JsonResponse(ret)
        
        try:
            server_idc_obj.ssh_port = server_idc_update_form.cleaned_data.get("ssh_port")
            server_idc_obj.env = server_idc_update_form.cleaned_data.get("env")
            server_idc_obj.idc = server_idc_update_form.cleaned_data.get("idc")
            server_idc_obj.status = server_idc_update_form.cleaned_data.get("status")
            server_idc_obj.sn_code = server_idc_update_form.cleaned_data.get("sn_code")
            server_idc_obj.cabinet_num = server_idc_update_form.cleaned_data.get("cabinet_num") 
            server_idc_obj.idrac_ip = server_idc_update_form.cleaned_data.get("idrac_ip") 
            server_idc_obj.save(update_fields=["sn_code","ssh_port","env","idc_id","status","cabinet_num","idrac_ip","last_update_time"])

        except Exception as e:
            ret["result"] = 1
            ret["msg"] = e.args
        else:
            ret["msg"] = "服务器 %s 更新成功" %(server_idc_obj.private_ip)

        return JsonResponse(ret)

