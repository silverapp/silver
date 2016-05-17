# Copyright (c) 2016 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from django.core.cache import cache


def cached_method(unique_attribute=None):
    """
    A decorator for caching method results in the Django context
    :param unique_attribute: Name of attribute used in the cache key
    """
    def decorator(func):
        def func_wrapper(self, *args, **kwargs):
            """
            :param invalidate_cache: If True the cache is being invalidated
            :param set_cache: If True the cache will be set if there is no cache
                              If invalidate is True, the cache will be reset
            :param bypass_cache: If True the original method will be called
                                 It can interact with the other parameters
            :param return: Value of method (either cached or not)

            !!! Warning: the *args and **kwargs parameters are considered when
            creating the cache key
            """

            invalidate = kwargs.pop('invalidate_cache', False)
            set_cache = kwargs.pop('set_cache', True)
            bypass = kwargs.pop('bypass_cache', False)

            if not unique_attribute:
                unique_key = id(self)
            else:
                if not hasattr(self, unique_attribute):
                    raise AttributeError

                unique_key = getattr(self, unique_attribute)

            key = "{}-{}-{}".format(
                self.__class__.__name__, func.__name__, unique_key
            )

            cache_is_fresh = False

            if invalidate:
                if set_cache:
                    # reset cache
                    cache.set(key, func(self, *args, **kwargs), None)
                    cache_is_fresh = True
                else:
                    cache.delete(key)  # invalidate cache
            elif not cache.get(key) and set_cache:
                cache.set(key, func(self, *args, **kwargs), None)  # set cache
                cache_is_fresh = True

            # if the method wasn't already called
            if bypass and not cache_is_fresh:
                return func(self, *args, **kwargs)  # bypass cache

            return cache.get(key)

        return func_wrapper

    return decorator
