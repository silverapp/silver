from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        self.stdout.write('Text')

