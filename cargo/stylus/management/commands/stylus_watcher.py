from django.conf import settings
from django.utils.module_loading import import_module
from django.core.management.base import BaseCommand
from cargo.watchers import StylusWatcher

class Command(BaseCommand):
	args = ''
	help = 'ex: ./manage.py stylus_watcher'
	
	def handle(self, *args, **options):	

		watcher = StylusWatcher(command=self)
		watcher.watch()