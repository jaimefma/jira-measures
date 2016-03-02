class Issue(object):
    def __init__(self, **kargs):
        [setattr(self, field, value)for field, value in kargs.items()]
