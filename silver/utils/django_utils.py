from django.shortcuts import _get_queryset


def get_object_or_None(model, *args, **kwargs):
    queryset = _get_queryset(model)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None
