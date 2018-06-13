import os
import sys
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor

# 在指定文件时，不能使用列表指定多个。
host_path = '/etc/ansible/hosts'
if not os.path.exists(host_path):
  print ('[INFO] The [%s] inventory does not exist' %(host_path))
  sys.exit()

loader = DataLoader()
variable_manager = VariableManager(loader=loader)
# 指定扩展的变量，相当于 执行 playbook 时的 -e 参数
variable_manager.extra_vars = {"host":"29"}
inventory = InventoryManager(loader=loader,sources=['/etc/ansible/hosts'])
variable_manager.set_inventory(inventory)
passwords=dict()

Options = namedtuple('Options',
                     ['connection',
                      'remote_user',
                      'ask_sudo_pass',
                      'verbosity',
                      'ack_pass',
                      'module_path',
                      'forks',
                      'become',
                      'become_method',
                      'become_user',
                      'check',
                      'listhosts',
                      'listtasks',
                      'listtags',
                      'syntax',
                      'sudo_user',
                      'sudo',
                      'diff'])

options = Options(connection='smart',
                       remote_user='root',
                       ack_pass=None,
                       sudo_user='root',
                       forks=5,
                       sudo='yes',
                       ask_sudo_pass=False,
                       verbosity=5,
                       module_path=None,
                       become=True,
                       become_method='sudo',
                       become_user='root',
                       check=None,
                       listhosts=None,
                       listtasks=None,
                       listtags=None,
                       syntax=None,
                       diff=False)

# 多个yaml文件则以列表形式
playbook_path=['/etc/ansible/h5-test.yml']
for i in playbook_path:
  if not os.path.exists(i):
    print ('[INFO] The [%s] playbook does not exist'%(i))
    sys.exit()

playbook = PlaybookExecutor(playbooks=playbook_path,inventory=inventory,
              variable_manager=variable_manager,
              loader=loader,options=options,passwords=passwords)

# 执行playbook
result = playbook.run()

# 返回执行结果
print ('执行结果: %s' %(result))