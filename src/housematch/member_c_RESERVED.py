"""Member C: accounts, application workflow and full acceptance transaction."""


def manage_accounts(*args, **kwargs):
    raise NotImplementedError('Member C: account/session implementation.')


def manage_applications(*args, **kwargs):
    raise NotImplementedError('Member C: apply, withdraw and review applications.')


def accept_application(*args, **kwargs):
    raise NotImplementedError('Member C: call A state helper inside the acceptance transaction.')
