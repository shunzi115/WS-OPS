from django.contrib.auth.models import User,Group,Permission,ContentType
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,View,ListView
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from django.http import JsonResponse,HttpResponse
from accounts.forms import PermissionAddForm
import json

class PermissionListView(LoginRequiredMixin,PermissionRequiredMixin,ListView):
    permission_required = "auth.view_permission"
    permission_redirect_url = "index" 

    template_name = "permission/permission_list.html"
    model = Permission
    paginate_by = 10
    ordering = "id"
    page_total = 11

    def get_context_data(self,**kwargs):
        context = super(PermissionListView,self).get_context_data(**kwargs)
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
        queryset = super(PermissionListView,self).get_queryset()
        search_name = self.request.GET.get('search',None)
        if search_name:
            queryset = queryset.filter(codename__icontains=search_name)
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


class PermissionChangeNameView(LoginRequiredMixin,View):
    permission_required = "auth.change_permission"

    def get(self,request,*args,**kwargs):
        ret = {'result':0}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'修改 permission 模型'的权限,请联系运维!"
            return JsonResponse(ret)

        p_id = request.GET.get('id',None)
        try:
            perm = Permission.objects.get(id__exact=p_id)
        except Permission.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = "权限 ID 不存在"
        else:
            ret['name'] = perm.name
        return JsonResponse(ret)

    def post(self,request):
        ret = {'result':0}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'修改 permission 模型'的权限,请联系运维!"
            return JsonResponse(ret)

        p_id = request.POST.get('id',None)
        perm_name = request.POST.get('perms_name',None)

        try:
            perm = Permission.objects.get(id__exact=p_id)
        except Permission.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = "权限 ID 不存在"
            return JsonResponse(ret)

        if perm_name and perm_name.strip():
            try:
                Permission.objects.filter(id__exact=p_id).update(name=perm_name)
            except Exception as e:
                ret['result'] = 1
                ret['msg'] = e.args
            else:
                ret['msg'] = "name 修改为 '%s' 成功" %(perm_name)
        else:
            ret['result'] = 1
            ret['msg'] = "name 不能为空"

        return  JsonResponse(ret)


class PermissionAddView(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    permission_required = "auth.add_permission"
    permission_redirect_url = "permission_list"

    template_name = "permission/permission_add.html"

    def get_context_data(self,**kwargs):
        context = super(PermissionAddView,self).get_context_data(**kwargs)
        context['contenttype_obj_list'] = ContentType.objects.all()
        return context

    def post(self,request):
        ret = {'result':0,'msg':None}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'添加 permission 模型对象'的权限,请联系运维!"
            return JsonResponse(ret)        

        perms_form = PermissionAddForm(request.POST)
        
        if not perms_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(perms_form.errors.as_json(escape_html=False)) 
            ret["msg"] = '\n'.join([ i["message"] for v in error_msg.values() for i in v ])
            return JsonResponse(ret)

        try:
            perm = Permission(**perms_form.cleaned_data)
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = e.args
        else:
            perm.save()
            ret['msg'] = "权限创建成功"
        return JsonResponse(ret)


class PermissionDeleteView(LoginRequiredMixin,View):
    permission_required = "auth.delete_permission"

    def get(self,request):
        ret = {'result':0,'msg':None}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'删除 permission 模型对象'的权限,请联系运维!"
            return JsonResponse(ret)

        perm_id = request.GET.get("p_id",0)

        try:
            perm_obj = Permission.objects.get(id__exact=perm_id)
        except Permission.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = " permission ID:%s 不存在" %(perm_id)
            return JsonResponse(ret)
           
        try:
            perm_obj.delete()
            ret['msg'] = '权限 "%s" 删除成功' %(perm_obj.name)
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = e.args

        return JsonResponse(ret)

