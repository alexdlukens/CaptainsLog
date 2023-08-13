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

        self.window_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.window_box.set_vexpand(True)
        self.set_child(self.window_box)
        
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.sidebar_box.set_vexpand(True)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_hexpand(True)
        self.content_box.set_vexpand(True)

        # Create a stack to hold multiple pages
        self.stack = Gtk.Stack()

        self.stack_sidebar = Gtk.StackSidebar()
        self.stack_sidebar.set_stack(self.stack)

        self.update_container_stack(containers=self.containers, stack=self.stack, stack_sidebar=self.stack_sidebar)
        
        self.sidebar_box.append(self.stack_sidebar)
        
        self.stack_sidebar.set_size_request(100, 100)

        self.window_box.append(self.sidebar_box)
        self.content_box.append(self.stack)
        self.window_box.append(self.content_box)
        # Add the stack to the main box
        
        # shortcuts
        # self.shortcut_controller = Gtk.ShortcutController()
        
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
        
        since_time = 0.001
        while True:
            new_since_time = datetime.datetime.utcnow()
            container_logs = container.logs(since=since_time, until=new_since_time)
            since_time = new_since_time
            if container_logs:
                # only update UI when new logs generated
                new_text = container_logs.decode('iso-8859-1') 
                new_text = remove_control_characters(new_text) # strip control characters other than newline
                GLib.idle_add(self.update_container_log, text_view, new_text)
            if current_thread.stopped():
                # break from infinite loop when thread is stopped (e.g. on update)
                return
            time.sleep(0.5)


    def update_container_log(self, text_view: Gtk.TextView, new_text: str):
        """Perform the actual updating of the TextBuffer with additional text

        Args:
            container_textbuf (Gtk.TextBuffer): TextBuffer to append to
            new_text (str): _description_
        """
        container_textbuf = text_view.get_buffer()
        end_iter = container_textbuf.get_end_iter()
        container_textbuf.insert(end_iter, new_text)
        return  

    def update_container_stack(self, containers: List[Container], stack: Gtk.Stack, stack_sidebar: Gtk.StackSidebar):
        # remove all previous elements
        page : Gtk.StackPage
        num_pages = len(stack.get_pages())
        print(f'stack has {num_pages} pages')
        old_pages = [page for page in stack.get_pages()]
        
        # if the container still exists, do not re-create stackpage
        current_container_names = [container.name for container in containers]
        current_page_names = [page.get_name() for page in old_pages]
        
        
        pages_to_remove = [page for page in old_pages if page.get_name() not in current_container_names]
        for page in pages_to_remove:
            name = page.get_name()
            print(f'removing page for container {name}')
            if name in thread_dict:
                thread_dict[name].stop()
            thread_dict[name].join()
            stack.remove(page.get_child())
        
        containers_to_add = [container for container in containers if container.name not in current_page_names] 
        for container in containers_to_add:
            container_scroll_window = Gtk.ScrolledWindow(vexpand=True, hexpand=True)

            container_info = Gtk.TextView()
            container_scroll_window.set_child(container_info)

            # tail docker logs in separate thread, calling back to main Gtk thread to update TextView
            thread_dict[container.name] = StoppableThread(target=self.container_log_tailer, args=[container_info, container.name])
            thread_dict[container.name].daemon = True
            thread_dict[container.name].start()
            
            stack.add_titled(child=container_scroll_window, name=container.name, title=container.name)
            


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
