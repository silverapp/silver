from copy import deepcopy

from rest_framework import serializers
from rest_framework.settings import api_settings

from django.core.exceptions import ValidationError as DjangoValidationError, NON_FIELD_ERRORS


def django_to_drf_validation_error(django_validation_error,
                                   default_errors_key=None):
    try:
        errors = django_validation_error.message_dict
    except AttributeError:
        errors = django_validation_error.messages
        if default_errors_key:
            errors = {default_errors_key: errors}
    else:
        non_field_errors = errors.pop(NON_FIELD_ERRORS, None)
        if non_field_errors:
            errors[default_errors_key or api_settings.NON_FIELD_ERRORS_KEY] = non_field_errors

    raise serializers.ValidationError(errors)


class AutoCleanSerializerMixin:
    # Run model clean and handle ValidationErrors
    def validate(self, attrs):
        try:
            # Use the existing instance to avoid unique field errors
            if self.instance:
                instance = deepcopy(self.instance)
                for field, value in attrs.items():
                    setattr(instance, field, value)
            else:
                instance = self.instantiate_object(attrs)

            instance.full_clean()
        except DjangoValidationError as django_validation_error:
            django_to_drf_validation_error(django_validation_error)

        return attrs

    def instantiate_object(self, data):
        model = self.Meta.model
        # filter reverse relations out and m2m relations
        reverse_relation = [
            field.name for field in model._meta.get_fields()
            if field.auto_created and not field.concrete
        ]
        return model(
            **{field: value for field, value in data.items()
               if field not in reverse_relation}
        )
