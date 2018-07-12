#!/usr/bin/env python

import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase

def ansible_adhoc(module,args,host):
    class ResultCallback(CallbackBase):
        def v2_runner_on_ok(self, result, **kwargs):
            host = result._host
            self.data = {host.name: result._result}
            return self.data

    Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'diff'])

    # initialize needed objects
    loader = DataLoader()
    options = Options(connection='smart', module_path='/ops-data/zp/haha/mysite-11/lib/python3.6/site-packages/ansible', forks=100, become=None, become_method=None, become_user=None, check=False, diff=False)
    passwords = dict(vault_pass='secret')

    # Instantiate our ResultCallback for handling results as they come in
    results_callback = ResultCallback()

    # create inventory and pass to var manager
    inventory = InventoryManager(loader=loader, sources=['/etc/ansible/hosts'])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    # create play with tasks
    play_source =  dict(
            name = "Ansible Play",
            hosts = host,
            gather_facts = 'no',
            tasks = [
                dict(action=dict(module=module, args=args), register='shell_out')
            ]
        )
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    # actually run it
    tqm = None
    try:
        tqm = TaskQueueManager(
                inventory=inventory,
                variable_manager=variable_manager,
                loader=loader,
                options=options,
                passwords=passwords,
                stdout_callback=results_callback,
                )
        result = tqm.run(play)
    finally:
        if tqm is not None:
            tqm.cleanup()
        return results_callback.data

