import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import re

def remove_control_characters(s):
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', s)

from typing import List, Dict
import docker
from gi.repository import Gtk, Gdk, Adw, GLib
from docker_utils import list_containers
from docker.models.containers import Container
from threads import StoppableThread
import threading
import datetime
import time
css_provider = Gtk.CssProvider()
css_provider.load_from_path('src/style.css')
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(
), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

thread_dict: Dict[str, StoppableThread] = {}


        
        
class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header = Gtk.HeaderBar()
        self.containers: List[Container] = list_containers()
        self.set_titlebar(self.header)
        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.set_icon_name("view-refresh-symbolic")

        self.refresh_button.connect('clicked', self.refresh_toggled)
        self.header.pack_start(self.refresh_button)

        self.box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.box1.set_vexpand(True)
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)
        self.set_child(self.box1)

        # Create a stack to hold multiple pages
        self.stack = Gtk.Stack()
        # self.stack.set_transition_type(
        #     Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        # self.stack.set_transition_duration(500)

        self.stack_sidebar = Gtk.StackSidebar()
        self.stack_sidebar.set_stack(self.stack)

        self.update_container_stack(containers=self.containers, stack=self.stack, stack_sidebar=self.stack_sidebar)
        
        self.sidebar_box.append(self.stack_sidebar)
        self.sidebar_box.set_vexpand(True)
        self.stack_sidebar.set_size_request(100, 100)

        self.box1.append(self.sidebar_box)
        self.main_box.append(self.stack)
        self.box1.append(self.main_box)
        # Add the stack to the main box

        self.set_default_size(600, 600)
        self.set_title("CaptainsLog")

    def hello(self, button):
        print(f'Hello world')
        if self.check.get_active():
            print('and goodbye')

    def refresh_toggled(self, button):
        self.containers = list_containers()
        print(f'refresh toggled: {self.containers=}')
        self.update_container_stack(containers=self.containers, stack=self.stack, stack_sidebar=self.stack_sidebar)

    def container_log_tailer(self, text_view: Gtk.TextView, container_name: str):
        current_thread = threading.current_thread()
        dc = docker.from_env()
        container: Container = dc.containers.get(container_name)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        container_textbuf = text_view.get_buffer()
        since_time = 0.001
        while True:
            new_since_time = datetime.datetime.utcnow()
            container_logs = container.logs(since=since_time, until=new_since_time)
            since_time = new_since_time
            if container_logs:
                new_text = container_logs.decode('utf-8')
                new_text = remove_control_characters(new_text)
                GLib.idle_add(self.update_container_log, container_textbuf, new_text)
                if current_thread.stopped():
                    return
                time.sleep(0.5)


    def update_container_log(self, container_textbuf: Gtk.TextBuffer, new_text: str):
        
        end_iter = container_textbuf.get_end_iter()
        container_textbuf.insert(end_iter, new_text)
        return  

    def update_container_stack(self, containers: List[Container], stack: Gtk.Stack, stack_sidebar: Gtk.StackSidebar):
        # remove all previous elements
        page : Gtk.StackPage
        num_pages = len(stack.get_pages())
        print(f'stack has {num_pages} pages')
        old_pages = [page for page in stack.get_pages()]
        for page in old_pages:
            name = page.get_name()
            print(f'{page=}, name={name}')
            if name in thread_dict:
                thread_dict[name].stop()
            thread_dict[name].join()
            stack.remove(page.get_child())
        
        for container in containers:
            container_info = Gtk.TextView()
            # container_info.set_wrap_mode(Gtk.WrapMode.WORD)
            # container_textbuf = container_info.get_buffer()
            # container_logs = container.logs(since=0.1).decode('iso-8859-1')
            # container_logs = remove_control_characters(container_logs)
            # container_textbuf.set_text(f'Hello: {container_logs}')
            thread_dict[container.name] = StoppableThread(target=self.container_log_tailer, args=[container_info, container.name])
            thread_dict[container.name].daemon = True
            thread_dict[container.name].start()
            
            stack.add_titled(child=container_info, name=container.name, title=container.name)
            


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
