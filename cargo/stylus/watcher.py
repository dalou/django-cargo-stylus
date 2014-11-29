'''
    Low level inotify wrapper
'''

from os import read, close
from struct import unpack
from fcntl import ioctl
from termios import FIONREAD
from time import sleep
from ctypes import cdll, c_int, POINTER
from errno import errorcode


from os import listdir
from os.path import join as opj, normpath, isdir
from threading import Thread, RLock
from Queue import Queue
from time import sleep

import os
import sys
import time
import logging
import signal
# from watchdog.observers import Observer
# from watchdog.events import LoggingEventHandler, PatternMatchingEventHandler, FileSystemEventHandler, FileMovedEvent
import tempfile

import pyinotify
from django.conf import settings
from django.utils.module_loading import import_module
from django.db.models import get_models, get_app

import subprocess

pyinotify.max_queued_events.value = 100000
pyinotify.max_user_watches.value = 100000


pyinotify.SysCtlINotify.inotify_attrs['max_user_watches'] = 100000


mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO | pyinotify.IN_MODIFY  # watched events

class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, manager, *args, **kwargs):
        self.manager = manager

    # def process_IN_CREATE(self, event):
    #     print "Create: %s" %  os.path.join(event.path, event.name)

    # def process_IN_DELETE(self, event):
    #     print "Remove: %s" %  os.path.join(event.path, event.name)

    # def process_IN_MODIFY(self, event):
    #     print "Modify: %s" %  os.path.join(event.path, event.name)

    # Atomic save
    def process_IN_MOVED_TO(self, event):
        print "Moved: %s" %  os.path.join(event.path, event.name)
        self.manager.process_changes(event)

class Watcher(object):
    handler = None
    command = None
    blocked = False
    stout_prefix = 'cargo-stylus'
    configs = []

    def __init__(self, command=None, *args, **kwargs):
        #self.handler = WatcherHandler(self)
        self.command = command
        self.manager = pyinotify.WatchManager()
        self.notifier = pyinotify.Notifier(self.manager, EventHandler(self))

        self.process_settings()

        self.notifier.max_user_watches=16384
        self.process_settings()

        paths = self.get_watched_paths()
        for appname, path in paths:

            #try:
            #self.schedule(self.handler, path, recursive=True)
            self.schedule(path, self.process_changes, 'MODIFY')
            self.print_head('Watching \033[94m%s\033[0m' % (appname))
            # except Exception, e:
            #     self.print_error('Watching %s error : %s' % (appname, str(e)))


    def process_settings(self):

        reload(conf)
        self.configs = []
        settings = conf.settings

        if not hasattr(settings, 'CARGO_STYLUS') and 'watcher' in settings.CARGO_STYLUS:
            self.print_error('Improprely config for cargo stylus watcher : missing settings.CARGO_STYLUS["watcher"]')
        else:
            configs = settings.CARGO_STYLUS['watcher']

            try
                from cargo import admin
                configs.append(
                    (
                        os.path.join(os.path.dirname(admin.__file__), 'styl/admin.styl'),
                        os.path.join(os.path.dirname(admin.__file__), 'static/cargo/admin/css/cargo.css'),
                    )
                )
            except:
                pass

            for config in configs:
                try:

                    source = config[0]
                    css_output = config[1]
                    content = None

                    if not os.path.isfile(source):
                        source = os.path.join(settings.SITE_ROOT, config[0])
                        if not os.path.isfile(source):
                            self.print_error('Source is missing "%s"' % source)
                            source = None


                    css_output_dir = os.path.dirname(css_output)
                    if not os.path.isdir(css_output_dir):
                        css_output_dir = os.path.join(settings.SITE_ROOT, css_output_dir)
                        css_output =    os.path.join(settings.SITE_ROOT, css_output)
                        if not os.path.isdir(css_output_dir):
                            self.print_error('CSS output folder is missing "%s"' % css_output)
                            css_output = None

                    if os.path.isfile(css_output):
                        f = open(css_output, 'r')
                        content = f.read()
                        f.close()

                    if source and css_output:
                        self.configs.append((source, css_output, content))
                except:
                    self.print_error('Invalid config for cargo stylus watcher "%s"' % config)

    def process_changes(self, event):

        if event.pathname.endswith('.styl'):

            self.process_settings()
            diff_cmd_stream = os.popen("git diff --name-only")
            diffs = diff_cmd_stream.read()

            if ".styl" in diffs:
                self.print_head('Changes detected')
                self.generate_css()

            else:
                self.print_head("No changes")

    def generate_css(self, compress=True):

        for config in self.configs:
            #try:
            source = config[0]
            css_output = config[1]


            self.print_process('Compiling css from %s to %s' % (source, css_output))

            f = open(source, 'r')
            initial = f.read()
            f.close()
            shortcuts_path = os.path.join(os.path.dirname(__file__), 'libs', 'shortcuts', 'shortcuts.styl')

            styl = """
SOURCE_ROOT = '%s/'
DJANGO_ROOT = '%s/'
@import '%s'

import_app(appname)
    if !appname
        return
""" % (os.path.abspath(os.path.dirname(source)), settings.DJANGO_ROOT, shortcuts_path)
            for appname, path in self.get_watched_paths():
                styl += """
    else if appname == '%s'
        @import '%s'
""" % (appname, os.path.join(path, '*'))
            styl += """
    else
        @import SOURCE_ROOT+appname
"""
            styl += initial

            tmp =  tempfile.NamedTemporaryFile(mode='w+b', delete=False)
            tmp.write(styl)
            tmp.close()
            cmd = "stylus%s < %s" % (' --compress' if compress else '', tmp.name)#, css_output)
            # self.print_process('Executing %s' % cmd)
            pipe = subprocess.Popen(cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell = True)

            css = "".join([ line for line in pipe.stdout ])
            errors = "".join([ line for line in pipe.stderr ])
            self.print_error(errors)
            os.unlink(tmp.name)

            csslen = len(css)
            if csslen == 0 or errors:
                self.print_error("^ Error in stylus compilation")
            else:
                # self.print_success("Done (%s chars)." % csslen)
                f = open(css_output, 'w')
                #self.print_process('Pushing css into %s' % css_output)
                f.write(css)
                f.close()
                self.print_success("Done (git commit to stop watching those changes)")
            #except Exception, e:
                #self.print_error('Error during css generation for "%s" : %s' % (config, str(e)))



    def get_watched_paths(self):
        app_paths = []
        for config in self.configs:
            source_dir = os.path.abspath(os.path.dirname(config[0]))
            app_paths.append(
                (config[0], source_dir)
            )

        #styl_path = os.path.join(settings.DJANGO_ROOT, 'styl')
        styl_path = settings.DJANGO_ROOT
        if os.path.exists(styl_path):
            app_paths.append((styl_path, styl_path))

        for path in settings.STATICFILES_DIRS:
            #styl_path = os.path.join(path, 'styl')
            styl_path = path
            if os.path.exists(styl_path):
                app_paths.append((styl_path, styl_path))

        for appname in settings.INSTALLED_APPS:
            app = import_module(appname)
            #styl_path = os.path.join(os.path.dirname(app.__file__), 'styl')
            styl_path = os.path.dirname(app.__file__)
            if os.path.exists(styl_path):
                app_paths.append((appname, styl_path))

        return app_paths

    def sigterm(self, signum, frame):
        print 'Cargo watchers : SIGTERM'
        self.close()
        #self.join()
        exit(0)

    def watch(self, paths=[]):


        signal.signal(signal.SIGTERM, self.sigterm)
        signal.signal(signal.SIGINT , self.sigterm)
        logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

        while True:  # loop forever
            try:
                # process the queue of events as explained above
                self.notifier.loop()
                # you can do some tasks here...
            except KeyboardInterrupt:
                # destroy the inotify's instance on this interrupt (stop monitoring)
                self.notifier.stop()
                break



    def schedule(self, path, event_handle, event_type="MODIFY"):
        if event_type == "MODIFY":
            self.manager.add_watch(path, mask, rec=True)
        pass

    def print_r(self, pattern, str):
        output = pattern % (self.stout_prefix, str)
        if self.command:
            self.command.stdout.write(output)
            self.command.stdout.flush()
        else:
            print output

    def print_head(self, str):
        self.print_r("\033[95m[%s]\033[0m %s", str)

    def print_process(self, str):
        self.print_r("\033[95m[%s]\033[0m \033[93m%s\033[0m", str)

    def print_success(self, str):
        self.print_r("\033[95m[%s]\033[0m \033[92m%s\033[0m", str)

    def print_error(self, str):
        self.print_r("\033[95m[%s]\033[0m \033[91m%s\033[0m", str)

    def getext(filename):
        "Get the file extension."

        return os.path.splitext(filename)[-1].lower()