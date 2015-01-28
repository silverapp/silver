from django.core.management.base import BaseCommand, CommandError

from silver.models import Invoice, Plan, Subscription

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        self.stdout.write('Asd')

