## ws-ops
    WS运维管理平台

### 功能说明
    - 用户管理
    - 资产管理
    - CMDB
    - 运维工单(需要优化)
    - LDAP认证(待完善)
    - 发布系统(还没写)

### 运行环境   
    * Python 3.6.3
    * Django 1.11.7

### 启动方式
    ```
    scripts/gunicorn.sh start
    ```
### 功能详细说明
    - 用户管理
        1. 用户的增删改查
        2. 用户组的增删改查
        3. 权限的增删改查
        4. 用户组的权限管理
        5. ldap 认证

    - 资产管理
        1. 服务器的增删改查
        2. cmdb 的增删改查
        3. 阿里云服务器的自动增删改查、阿里云服务器信息的自动更新
        4. 阿里云服务器信息的手动一键更新
        5. 阿里云服务器上部署的应用自动增删改到 cmdb
        6. IDC 服务器信息实现手动批量更新(由于公司网络及防火墙的原因,需从IDC中的跳板机执行脚本批量post信息到平台的接口，实现更新)
        7. IDC 机房信息的增删改查

    - 运维工单
        见 workform/莴笋运维平台工单设计思路.txt

### 部署方式
    暂时先略
