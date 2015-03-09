from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

class TestInvoiceGenerationCommand(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command('generate_billing_documents', stdout=out)
        #self.assertIn('Text', out.getvalue())
        assert True
