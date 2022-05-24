from functools import wraps

from django.db import transaction
from django_fsm import (transition, TransitionNotAllowed, ConcurrentTransitionMixin,
                        ConcurrentTransition)

from silver.utils.models import AutoCleanModelMixin


def locking_atomic_transition(
    field, source='*', target=None, on_error=None, conditions=None, permission=None, custom=None,
    save=True
):
    def func_wrapper(transition_method):
        original_wrapped_transition_method = transition(
            field, source, target, on_error, conditions or [], permission, custom or {}
        )(transition_method)

        @wraps(transition_method)
        def transition_wrapper(instance, *args, **kwargs):
            with transaction.atomic():
                locked_instance = instance.__class__.objects\
                    .filter(id=instance.id)\
                    .select_for_update()\
                    .first()

                field_name = field if isinstance(field, str) else field.name
                field_value = getattr(instance, field_name)
                saved_field_value = getattr(locked_instance, field_name)

                strict_fields = [
                    strict_field if isinstance(strict_field, str) else strict_field.name
                    for strict_field in getattr(instance, 'strict_fields', [])
                ]

                for strict_field in strict_fields:
                    if getattr(locked_instance, strict_field) != getattr(instance, strict_field):
                        raise TransitionNotAllowed(
                            f"{instance.__class__}'s {strict_field} value has concurrently changed."
                        )

                if source != '*':
                    if isinstance(source, (list, tuple, set)):
                        if saved_field_value not in source:
                            raise TransitionNotAllowed(
                                f"Saved object's {field} is not a valid source for this transition."
                            )
                    elif field_value != saved_field_value:
                        raise TransitionNotAllowed(
                            f"Object {field} is {field_value}, "
                            f"while the saved field is {saved_field_value}."
                        )

                # post transition signal receivers are also executed inside this atomic transaction
                result = original_wrapped_transition_method(instance, *args, **kwargs)

                setattr(instance, f'{field_name}_recently_transitioned_to', target)

                if save:
                    instance.save()

                return result

        return transition_wrapper

    return func_wrapper


class StrictModelMixin(ConcurrentTransitionMixin, AutoCleanModelMixin):
    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        # This is a modified version of FSM's ConcurrentTransitionMixin's _do_update

        # Select state fields to filter on
        filter_on = filter(lambda field: field.model == base_qs.model, self.state_fields)

        # state filter will be used to narrow down the standard filter checking only PK
        state_filter = dict(
            (field.attname, self._ConcurrentTransitionMixin__initial_states[field.attname])
            for field in filter_on
        )

        strict_fields = [field if isinstance(field, str) else field.name
                         for field in getattr(self, 'strict_fields', [])]

        if set(field.name for field in filter_on).intersection(set(self.get_unsaved_fields())):
            strict_fields_filter = {field: getattr(self, field) for field in strict_fields}
        else:
            strict_fields_filter = {}

        updated = super(ConcurrentTransitionMixin, self)._do_update(
            base_qs=base_qs.filter(**state_filter, **strict_fields_filter),
            using=using,
            pk_val=pk_val,
            values=values,
            update_fields=update_fields,
            forced_update=forced_update
        )

        if not updated and base_qs.filter(pk=pk_val).exists():
            raise ConcurrentTransition(
                "Cannot save object! The state has been changed since fetched from the database!"
            )

        return updated


def optimistic_atomic_transition(
    field, source='*', target=None, on_error=None, conditions=None, permission=None, custom=None,
    save=True
):
    def func_wrapper(transition_method):
        original_wrapped_transition_method = transition(
            field, source, target, on_error, conditions or [], permission, custom or {}
        )(transition_method)

        @wraps(transition_method)
        def transition_wrapper(instance, *args, **kwargs):
            with transaction.atomic():
                field_name = field if isinstance(field, str) else field.name

                # post transition signal receivers are also executed inside this atomic transaction
                result = original_wrapped_transition_method(instance, *args, **kwargs)

                setattr(instance, f'{field_name}_recently_transitioned_to', target)

                if save:
                    instance.save()

                return result

        return transition_wrapper

    return func_wrapper
