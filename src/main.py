import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import re
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


def remove_control_characters(s):
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', s)


def join_threads(current_page_names, current_container_names):
    # if the container is dead and thread is still alive, we should join the thread
    threads_to_join = []
    for page_name in current_page_names:
        if page_name in current_container_names:
            continue
        if not thread_dict[page_name].is_alive():
            continue
        threads_to_join.append(page_name)

    for name in threads_to_join:
        # print(f'removing page for container {name}')
        thread_dict[name].stop()
        thread_dict[name].join()


def prepare_container_log_elements():
    """Make GTK elements for individual container log
    """

    # otherwise create new stack object for new container
    container_scroll_window = Gtk.ScrolledWindow(
        vexpand=True, hexpand=True)

    container_info = Gtk.TextView()
    container_scroll_window.set_child(container_info)
    return container_scroll_window, container_info

def update_container_log(text_view: Gtk.TextView, new_text: str):
    """Perform the actual updating of the TextBuffer with additional text

    Args:
        container_textbuf (Gtk.TextBuffer): TextBuffer to append to
        new_text (str): text to append to buffer
    """
    container_textbuf = text_view.get_buffer()
    end_iter = container_textbuf.get_end_iter()
    container_textbuf.insert(end_iter, new_text)
    return

def update_container_status_css(button: Gtk.Button, status: str):
    css_classes = button.get_css_classes()
    container_classes = []
    for class_name in css_classes:
        if class_name.startswith('container-'):
            container_classes.append(class_name)
    
    for class_name in container_classes:
        button.remove_css_class(class_name)
    
    button.add_css_class(f'container-{status}')


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)
        self.sidebar_button_dict: Dict[str, Gtk.Button]= {}
        # self.stack_child_dict: Dict[str, Gtk.StackPage] = {}
        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.set_icon_name("view-refresh-symbolic")

        self.refresh_button.connect('clicked', self.refresh_toggled)
        self.header.pack_start(self.refresh_button)

        self.window_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.window_box.set_vexpand(True)
        self.set_child(self.window_box)

        self.sidebar_box = Gtk.ListBox()
        self.sidebar_box.set_vexpand(True)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_hexpand(True)
        self.content_box.set_vexpand(True)

        # Create a stack to hold multiple pages
        self.stack = Gtk.Stack()

        self.stack_sidebar = Gtk.StackSidebar()
        self.stack_sidebar.set_stack(self.stack)

        self.update_container_stack(stack=self.stack)

        # self.sidebar_box.append(self.stack_sidebar)

        self.stack_sidebar.set_size_request(100, 100)

        self.window_box.append(self.sidebar_box)
        self.content_box.append(self.stack)
        self.window_box.append(self.content_box)
        # Add the stack to the main box

        # shortcuts
        # self.shortcut_controller = Gtk.ShortcutController()
        GLib.timeout_add(250, self.update_container_stack, self.stack)
        self.set_default_size(600, 600)
        self.set_title("CaptainsLog")


    def refresh_toggled(self, button):
        """When refresh button pressed, update container stack"""
        self.containers = list_containers()
        self.update_container_stack(containers=self.containers,
                                    stack=self.stack)

    def clear_container_log(self, text_view: Gtk.TextView):
        buffer = text_view.get_buffer()
        buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())

    def container_log_tailer(self, text_view: Gtk.TextView, container_name: str):
        current_thread = threading.current_thread()
        dc = docker.from_env()
        container: Container = dc.containers.get(container_name)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)

        # erase container text view on thread start
        GLib.idle_add(self.clear_container_log, text_view)

        since_time = None
        while True:
            new_since_time = datetime.datetime.utcnow()
            container_logs = container.logs(
                since=since_time, until=new_since_time)
            since_time = new_since_time
            if container_logs:
                # only update UI when new logs generated
                new_text = container_logs.decode('utf-8')
                # strip control characters other than newline
                new_text = remove_control_characters(new_text)
                GLib.idle_add(update_container_log, text_view, new_text)
            if current_thread.stopped():
                # break from infinite loop when thread is stopped (e.g. on update)
                return
            time.sleep(0.5)



    def update_container_stack(self, stack: Gtk.Stack):
        """Maintain proper stack of containers, and threads to tail their logs correspondingly

        Args:
            containers (List[Container]): current list of containers
            stack (Gtk.Stack): _description_
        """
        self.containers: List[Container] = list_containers()
        page: Gtk.StackPage
        current_pages = [page for page in stack.get_pages()]
        current_page_names = [page.get_name() for page in current_pages]
        current_container_names = [container.name for container in self.containers]

        # if the container is dead and thread is still alive, we should join the thread
        join_threads(current_page_names=current_page_names,
                     current_container_names=current_container_names)

        for container in self.containers:
            container.reload()
            if container.name in self.sidebar_button_dict:
                update_container_status_css(button=self.sidebar_button_dict[container.name], status=container.status)
            # restart thread if container has been seen previously
            if container.name in current_page_names:
                if not thread_dict[container.name].is_alive():
                    thread_dict[container.name].start()
                continue

            container_scroll_window, container_info = prepare_container_log_elements()
            
            # tail docker logs in separate threads, calling back to main Gtk thread to update TextView
            thread_dict[container.name] = StoppableThread(
                target=self.container_log_tailer, args=[container_info, container.name])
            thread_dict[container.name].daemon = True
            thread_dict[container.name].start()

            sidebar_row = Gtk.ListBoxRow()
            new_button = Gtk.Button(label=container.name)
            new_button.connect('clicked', self.on_sidebar_button_clicked)
            self.sidebar_button_dict[container.name] = new_button
            sidebar_row.set_child(new_button)
            self.sidebar_box.append(sidebar_row)

            stack.add_titled(child=container_scroll_window,
                             name=container.name, title=container.name)
        
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
