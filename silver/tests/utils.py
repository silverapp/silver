# Copyright (c) 2017 Presslabs SRL
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

from functools import wraps

from silver.models import PaymentProcessorManager


def register_processor(processor_class, **data):
    def decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            PaymentProcessorManager.register(processor_class, **data)
            result = func(*args, **kwargs)
            PaymentProcessorManager.unregister(processor_class)
            return result

        return func_wrapper
    return decorator
