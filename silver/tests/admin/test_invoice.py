# Copyright (c) 2015 Presslabs SRL
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
from itertools import cycle

from django.contrib.admin.models import CHANGE
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django_fsm import TransitionNotAllowed
from mock import MagicMock, patch

from silver.tests.factories import InvoiceFactory


class InvoiceAdminTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('user', 'myemail@test.com', 'password')

        self.admin = Client()

        self.admin.login(username='user', password='password')

    def test_actions_log_entries(self):
        invoice = InvoiceFactory.create()

        url = reverse('admin:silver_invoice_changelist')

        mock_log_entry = MagicMock()
        mock_log_action = MagicMock()
        mock_log_entry.objects.log_action = mock_log_action

        mock_action = MagicMock(return_value=MagicMock(series_number='aaa'))

        mock_invoice = MagicMock()
        mock_invoice.issue = mock_action
        mock_invoice.cancel = mock_action
        mock_invoice.pay = mock_action
        mock_invoice.clone_into_draft = mock_action

        with patch.multiple('silver.admin',
                            LogEntry=mock_log_entry,
                            Invoice=mock_invoice):
            actions = ['issue', 'pay', 'cancel', 'clone']

            for action in actions:
                self.admin.post(url, {
                    'action': action,
                    '_selected_action': [str(invoice.pk)]
                })

                assert mock_action.call_count

                mock_action.reset_mock()

                if action == 'clone':
                    action = 'clone_into_draft'

                mock_log_action.assert_called_with(
                    user_id=self.user.pk,
                    content_type_id=ContentType.objects.get_for_model(invoice).pk,
                    object_id=invoice.pk,
                    object_repr=unicode(invoice),
                    action_flag=CHANGE,
                    change_message='{action} action initiated by user.'.format(
                        action=action.capitalize().replace('_', ' ')
                    )
                )

    def test_actions_failed_no_log_entries(self):
        invoice = InvoiceFactory.create()

        url = reverse('admin:silver_invoice_changelist')

        mock_log_entry = MagicMock()
        mock_log_action = MagicMock()
        mock_log_entry.objects.log_action = mock_log_action

        exceptions = cycle([ValueError, TransitionNotAllowed])

        def _exception_thrower(*args):
            raise exceptions.next()

        mock_action = MagicMock(side_effect=_exception_thrower)

        mock_invoice = MagicMock()
        mock_invoice.issue = mock_action
        mock_invoice.cancel = mock_action
        mock_invoice.pay = mock_action
        mock_invoice.clone_into_draft = mock_action
        mock_invoice.create_invoice = mock_action

        with patch.multiple('silver.admin',
                            LogEntry=mock_log_entry,
                            Invoice=mock_invoice):
            actions = ['issue', 'pay', 'cancel', 'clone']

            for action in actions:
                self.admin.post(url, {
                    'action': action,
                    '_selected_action': [str(invoice.pk)]
                })

                assert not mock_log_action.call_count
