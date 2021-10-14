from functools import wraps

from django.db import transaction
from django_fsm import transition


def transactional_transition(
    field, source='*', target=None, on_error=None, conditions=[], permission=None, custom={}
):
    def func_wrapper(transition_method):
        original_wrapped_transition_method = transition(
            field, source, target, on_error, conditions, permission, custom
        )(transition_method)

        @wraps(transition_method)
        def transition_wrapper(instance, *args, **kwargs):
            with transaction.atomic():
                # post transition signal receivers are also executed inside this atomic transaction
                return original_wrapped_transition_method(instance, *args, **kwargs)

        return transition_wrapper

    return func_wrapper
