from copy import deepcopy


class ActionConfig:
    def __init__(self, type_name: str, params: dict=None, parent=None): # noqa
        self.type_name = type_name
        self.params = params or {}
        self.parent = parent
        self.sub_actions: list[ActionConfig] = []

    def enabled(self):
        return self.params.get('enabled', True)

    def set_enabled(self, enabled):
        self.params['enabled'] = enabled

    def set_enabled_all(self, enabled):
        self.params['enabled'] = enabled
        for a in self.sub_actions:
            a.set_enabled_all(enabled)

    def add_sub_action(self, action):
        self.sub_actions.append(action)
        action.parent = self

    def pop_sub_action(self, index):
        if index < len(self.sub_actions):
            self.sub_actions.pop(index)
        else:
            raise Exception(f"can't pop sub-action {index}, lenght is {len(self.sub_actions)}")

    def clone(self, name_postfix=''):
        c = ActionConfig(self.type_name, deepcopy(self.params))
        c.sub_actions = [s.clone() for s in self.sub_actions]
        for s in c.sub_actions:
            s.parent = c
        if name_postfix != '':
            c.params['name'] = c.params.get('name', '') + name_postfix
        return c

    def to_dict(self):
        dict = {
            'type_name': self.type_name,
            'params': self.params,
        }
        if len(self.sub_actions) > 0:
            dict['sub_actions'] = [a.to_dict() for a in self.sub_actions]
        return dict

    @classmethod
    def from_dict(cls, data):
        a = ActionConfig(data['type_name'], data['params'])
        if 'sub_actions' in data.keys():
            a.sub_actions = [ActionConfig.from_dict(s) for s in data['sub_actions']]
            for s in a.sub_actions:
                s.parent = a
        return a


class Project:
    def __init__(self):
        self.jobs: list[ActionConfig] = []

    def run_all(self):
        for job in self.jobs:
            stack_job = job.to_stack_job()
            stack_job.run()

    def clone(self):
        c = Project()
        c.jobs = [j.clone() for j in self.jobs]
        return c

    def to_dict(self):
        return [j.to_dict() for j in self.jobs]

    @classmethod
    def from_dict(cls, data):
        p = Project()
        p.jobs = [ActionConfig.from_dict(j) for j in data]
        for j in p.jobs:
            for s in j.sub_actions:
                s.parent = j
        return p
