import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import sys
from typing import Dict, List

import docker
from docker.models.containers import Container
from gi.repository import Adw, Gdk, GLib, Gtk

from threads import StoppableThread, join_threads
from container_updates import (prepare_container_log_elements,
                               update_container_status_css,
                               container_log_tailer)
from docker_utils import list_containers

css_provider = Gtk.CssProvider()
css_provider.load_from_path('src/style.css')
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(
), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

thread_dict: Dict[str, StoppableThread] = {}


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Header Setup
        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)
        # self.stack_child_dict: Dict[str, Gtk.StackPage] = {}

        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.set_icon_name("view-refresh-symbolic")
        self.refresh_button.connect('clicked', self.refresh_toggled)

        self.header.pack_start(self.refresh_button)

        # Main Content area boxes
        self.window_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.window_box.set_vexpand(True)
        self.set_child(self.window_box)

        self.sidebar_box = Gtk.ListBox()
        self.sidebar_box.set_vexpand(True)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_hexpand(True)
        self.content_box.set_vexpand(True)

        self.window_box.append(self.sidebar_box)
        self.window_box.append(self.content_box)

        # Create a stack to hold multiple pages

        self.sidebar_button_dict: Dict[str, Gtk.Button] = {}
        self.stack = Gtk.Stack()
        self.stack_sidebar = Gtk.StackSidebar()
        self.stack_sidebar.set_stack(self.stack)
        self.stack_sidebar.set_size_request(100, 100)

        # initial stack updating
        self.update_container_stack()
        self.content_box.append(self.stack)

        # update stack every .25 seconds
        # TODO: Make this on event from docker daemon
        GLib.timeout_add(250, self.update_container_stack)

        # set default size, title
        self.set_default_size(600, 600)
        self.set_title("CaptainsLog")

    def refresh_toggled(self, button):
        """When refresh button pressed, update container stack"""
        self.update_container_stack()

    def update_container_stack(self):
        """Maintain proper stack of containers, and threads to tail their logs correspondingly

        Args:
            containers (List[Container]): current list of containers
            stack (Gtk.Stack): _description_
        """
        self.containers: List[Container] = list_containers()
        page: Gtk.StackPage
        current_pages = [page for page in self.stack.get_pages()]
        current_page_names = [page.get_name() for page in current_pages]
        current_container_names = [
            container.name for container in self.containers]

        # if the container is dead and thread is still alive, we should join the thread
        join_threads(thread_dict=thread_dict,
                     current_page_names=current_page_names,
                     current_container_names=current_container_names)

        for container in self.containers:
            container.reload()
            if container.name in self.sidebar_button_dict:
                update_container_status_css(
                    button=self.sidebar_button_dict[container.name], status=container.status)
            # restart thread if container has been seen previously
            if container.name in current_page_names:
                if not thread_dict[container.name].is_alive():
                    thread_dict[container.name].start()
                continue

            container_scroll_window, container_info = prepare_container_log_elements()

            # tail docker logs in separate threads, calling back to main Gtk thread to update TextView
            thread_dict[container.name] = StoppableThread(
                target=container_log_tailer, args=[container_info, container.name])
            thread_dict[container.name].daemon = True
            thread_dict[container.name].start()

            sidebar_row = Gtk.ListBoxRow()
            new_button = Gtk.Button(label=container.name)
            new_button.connect('clicked', self.on_sidebar_button_clicked)
            self.sidebar_button_dict[container.name] = new_button
            sidebar_row.set_child(new_button)
            self.sidebar_box.append(sidebar_row)

            self.stack.add_titled(child=container_scroll_window,
                                  name=container.name,
                                  title=container.name)

        return True

    def on_sidebar_button_clicked(self, button: Gtk.Button):
        self.stack.set_visible_child_name(button.get_label())


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
