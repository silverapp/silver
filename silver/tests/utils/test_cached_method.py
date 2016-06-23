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
from django.test import TestCase

from silver.utils.decorators import cached_method


class Incrementer(object):
    def __init__(self, count=None):
        self.count = count if count else 0

    def _increment(self, amount=None):
        self.count += amount if amount else 1

    @cached_method()
    def increment(self, *args, **kwargs):
        if args:
            amount = args[0]
        elif kwargs:
            amount = kwargs.get('amount', 1)
        else:
            amount = 1

        self._increment(amount)

        return self.count


class UniqueIncrementer(Incrementer):
    _unique_id = 0

    def __init__(self, count=None):
        super(UniqueIncrementer, self).__init__(count=count)

        self.unique_id = UniqueIncrementer._unique_id
        UniqueIncrementer._unique_id += 1

    @cached_method(unique_attribute='unique_id')
    def increment(self, amount=None):
        super(UniqueIncrementer, self).increment(amount=amount, bypass=True)


class TestInvoice(TestCase):
    def setUp(self):
        self.incrementer = Incrementer()

    def tearDown(self):
        cache.clear()

    def test_cached_method_result(self):
        cached_count = self.incrementer.increment()

        assert cached_count == 1

        self.incrementer._increment()
        cached_count == self.incrementer.increment()  # cached result

        assert cached_count == 1
        assert self.incrementer.count == 2

    def test_cached_method_invalidate_cache(self):
        self.incrementer.increment()

        # invalidates cache, next call will be an actual call
        self.incrementer.increment(invalidate_cache=True, set_cache=False)

        # doesn't call actual method, even if cache is empty
        cached_count = self.incrementer.increment(set_cache=False)

        assert cached_count is None

        # actual call
        cached_count = self.incrementer.increment()

        assert cached_count == 2

    def test_cached_method_reset_cache(self):
        self.incrementer.increment()

        cached_count = self.incrementer.increment(invalidate_cache=True,
                                                  set_cache=True)

        assert cached_count == 2

    def test_cached_method_bypass(self):
        self.incrementer.increment()

        self.incrementer.increment(bypass_cache=True)

        assert self.incrementer.count == 2

        cached_count = self.incrementer.increment()

        assert cached_count == 1

    def test_cached_method_bypass_with_invalidation(self):
        self.incrementer.increment()

        bypass_count = self.incrementer.increment(invalidate_cache=True,
                                                  bypass_cache=True)

        assert bypass_count == 2

        cached_count = self.incrementer.increment()

        assert cached_count == 2

    def test_cached_method_with_args_and_kwargs(self):
        self.incrementer.increment(5)

        assert self.incrementer.count == 5

        self.incrementer.increment(5, invalidate_cache=True)

        assert self.incrementer.count == 10

        self.incrementer.increment(
            amount=5, invalidate_cache=True, set_cache=True
        )

        assert self.incrementer.count == 15

        self.incrementer.increment(5, bypass_cache=True)

        assert self.incrementer.count == 20

    def test_cached_method_default_unique_keys(self):
        other_incrementer = Incrementer(5)

        cached_count = self.incrementer.increment()
        other_cached_count = other_incrementer.increment()

        assert cached_count != other_cached_count

    def test_cached_method_unique_attribute_key(self):
        incrementer = UniqueIncrementer()

        other_incrementer = UniqueIncrementer()

        assert incrementer.unique_id != other_incrementer.unique_id

        incrementer.increment(5)
        other_incrementer.increment(55)

        assert incrementer.count != other_incrementer.count
