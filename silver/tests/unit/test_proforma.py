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


from decimal import Decimal

from django.test import TestCase

from silver.models import DocumentEntry, Invoice, Proforma
from silver.tests.factories import ProformaFactory, DocumentEntryFactory, \
    CustomerFactory, ProviderFactory


class TestProforma(TestCase):
    def test_pay_proforma_related_invoice_state_change_to_paid(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.create_invoice()

        proforma.pay()
        proforma.save()

        assert proforma.invoice.state == Invoice.STATES.PAID
        assert proforma.state == Invoice.STATES.PAID

    def test_clone_proforma_into_draft(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()
        proforma.save()

        entries = DocumentEntryFactory.create_batch(3)
        proforma.proforma_entries.add(*entries)

        clone = proforma.clone_into_draft()

        assert clone.state == Proforma.STATES.DRAFT
        assert clone.paid_date is None
        assert clone.issue_date is None
        assert clone.invoice is None
        assert (clone.series != proforma.series or
                clone.number != proforma.number)
        assert clone.sales_tax_percent == proforma.sales_tax_percent
        assert clone.sales_tax_name == proforma.sales_tax_name

        assert not clone.archived_customer
        assert not clone.archived_provider
        assert clone.customer == proforma.customer
        assert clone.provider == proforma.provider

        assert clone.currency == proforma.currency
        assert clone._last_state == clone.state
        assert clone.pk != proforma.pk
        assert clone.id != proforma.id
        assert not clone.pdf

        assert clone.proforma_entries.count() == 3
        assert proforma.proforma_entries.count() == 3

        entry_fields = [entry.name for entry in DocumentEntry._meta.get_fields()]
        for clone_entry, original_entry in zip(clone.proforma_entries.all(),
                                               proforma.proforma_entries.all()):
            for entry in entry_fields:
                if entry not in ('id', 'proforma', 'invoice'):
                    assert getattr(clone_entry, entry) == \
                        getattr(original_entry, entry)

        assert proforma.state == Proforma.STATES.PAID

    def test_cancel_issued_proforma_with_related_invoice(self):
        proforma = ProformaFactory.create()
        proforma.issue()

        if not proforma.invoice:
            proforma.create_invoice()

        proforma.cancel()
        proforma.save()

        assert proforma.state == proforma.invoice.state == Proforma.STATES.CANCELED

    def _get_decimal_places(self, number):
        return max(0, -number.as_tuple().exponent)

    def test_proforma_total_decimal_points(self):
        proforma_entries = DocumentEntryFactory.create_batch(3)
        proforma = ProformaFactory.create(proforma_entries=proforma_entries)

        assert self._get_decimal_places(proforma.total) == 2

    def test_proforma_total_before_tax_decimal_places(self):
        proforma_entries = DocumentEntryFactory.create_batch(3)
        proforma = ProformaFactory.create(proforma_entries=proforma_entries)

        proforma.sales_tax_percent = Decimal('20.00')

        assert self._get_decimal_places(proforma.total_before_tax) == 2

    def test_proforma_tax_value_decimal_places(self):
        proforma_entries = DocumentEntryFactory.create_batch(3)
        proforma = ProformaFactory.create(proforma_entries=proforma_entries)

        proforma.sales_tax_percent = Decimal('20.00')

        assert self._get_decimal_places(proforma.tax_value) == 2

    def test_proforma_total_with_tax_integrity(self):
        proforma_entries = DocumentEntryFactory.create_batch(5)
        proforma = ProformaFactory.create(proforma_entries=proforma_entries)

        proforma.sales_tax_percent = Decimal('20.00')

        assert proforma.total == proforma.total_before_tax + proforma.tax_value

    def test_draft_proforma_series_number(self):
        proforma = ProformaFactory.create()
        proforma.number = None

        assert proforma.series_number == '%s-draft-id:%d' % (proforma.series,
                                                             proforma.pk)

        proforma.series = None

        assert proforma.series_number == 'draft-id:%d' % proforma.pk

    def test_issues_proforma_series_number(self):
        proforma = ProformaFactory.create()

        assert proforma.series_number == '%s-%s' % (proforma.series,
                                                    proforma.number)

    def test_proforma_name_cache(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        proforma.series += 'alternate'  # no save, doesn't invalidate cache

        assert cached_name == proforma.__unicode__()

    def test_proforma_name_cache_invalidation_on_invoice_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        proforma.series += 'alternate'
        proforma.save()

        assert cached_name != proforma.__unicode__()

    def test_proforma_name_cache_invalidation_on_related_entries_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        entry = DocumentEntryFactory.create()
        proforma.proforma_entries.add(entry)

        entry.save()

        assert cached_name != proforma.__unicode__()

    def test_proforma_name_cache_invalidation_on_related_customer_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        proforma.customer.company = "change"
        proforma.customer.save()

        assert cached_name != proforma.__unicode__()

    def test_proforma_name_cache_invalidation_on_related_provider_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        proforma.provider.company = "change"
        proforma.provider.save()

        assert cached_name != proforma.__unicode__()

    def test_proforma_name_cache_on_unrelated_entries_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        entry = DocumentEntryFactory.create()

        entry.save()

        assert cached_name == proforma.__unicode__()

    def test_proforma_name_cache_on_unrelated_customer_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        customer = CustomerFactory.create()
        customer.save()

        assert cached_name == proforma.__unicode__()

    def test_proforma_name_cache_on_unrelated_provider_save(self):
        proforma = ProformaFactory.create()

        cached_name = proforma.__unicode__()

        provider = ProviderFactory.create()
        provider.save()

        assert cached_name == proforma.__unicode__()
