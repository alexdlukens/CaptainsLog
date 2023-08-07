import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import re
import unicodedata
def remove_control_characters(s):
    # return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)

from typing import List
from gi.repository import Gtk, Gdk, Adw
from docker_utils import list_containers
from docker.models.containers import Container

css_provider = Gtk.CssProvider()
css_provider.load_from_path('src/style.css')
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(
), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


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
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(500)

        self.stack_sidebar = Gtk.StackSidebar()
        self.stack_sidebar.set_stack(self.stack)
        
        for idx, container in enumerate(self.containers):
            container_info = Gtk.TextView()
            container_info.set_wrap_mode(Gtk.WrapMode.WORD)
            container_textbuf = container_info.get_buffer()
            container_logs = container.logs().decode('iso-8859-1')
            container_logs = remove_control_characters(container_logs)
            container_textbuf.set_text(container_logs)
            self.stack.add_titled(container_info, f'container_{idx}', container.name)

        
        self.sidebar_box.append(self.stack_sidebar)
        self.sidebar_box.set_vexpand(True)
        
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


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
