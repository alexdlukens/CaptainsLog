import gi
import json

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import docker
import sys
import os
from typing import Dict, List

from docker.models.containers import Container
from gi.repository import Adw, Gdk, GLib, Gtk, Gio

from .threads import StoppableThread, join_threads
from .container_updates import (prepare_container_log_elements,
                                update_container_status_css,
                                container_log_tailer)
from .docker_utils import list_containers
from pathlib import Path

cl_path = os.path.dirname(sys.modules['CaptainsLog'].__file__)
css_path = Path(cl_path).joinpath('style.css')
icon_path = Path(cl_path).joinpath('./icons')

css_provider = Gtk.CssProvider()
css_provider.load_from_path(str(css_path))
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(
), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

thread_dict: Dict[str, StoppableThread] = {}


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_search_path(str(icon_path))
        theme.add_search_path(str(icon_path.joinpath('./icon_development')))
        # print(theme.get_icon_sizes("com.alexdlukens.CaptainsLog"))
        # with open('dump.json', 'w') as f:
        #     json.dump(theme.get_icon_names(), f)
        # pixbuf = Gtk.Image.new_from_file(str(icon_path))

        # self.set_icon_name(pixbuf)
        self.set_icon_name("com.alexdlukens.CaptainsLog")
        # self.set_default_icon_name("com.alexdlukens.CaptainsLog")
        # Header Setup
        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)
        # self.stack_child_dict: Dict[str, Gtk.StackPage] = {}

        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.set_icon_name("view-refresh-symbolic")
        self.refresh_button.connect('clicked', self.refresh_toggled)

        # setup Menu
        self.menu = Gio.Menu()
        self.menu.append_item(Gio.MenuItem().new("About", "app.about"))

        quit_action = Gio.SimpleAction(name="quit")
        quit_action.connect("activate", self.quit_activated)
        app.add_action(quit_action)

        app.set_accels_for_action("app.quit", ["<Ctrl>q"])

        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_menu_model(self.menu)

        self.about_dialog = Gtk.AboutDialog(authors=["Alexander Lukens"],
                                            website="https://alukens.com",
                                            website_label="My Website",
                                            version="v2023.08.26",
                                            license_type=Gtk.License.GPL_3_0,
                                            program_name="CaptainsLog",
                                            wrap_license=True,
                                            comments="Thank you for using my app. This is a first for me",
                                            icon_name="com.alexdlukens.CaptainsLog",
                                            logo_icon_name="com.alexdlukens.CaptainsLog")

        about_action = Gio.SimpleAction(name="about")
        about_action.connect("activate", self.about_activated)
        app.add_action(about_action)

        # add buttons to top bar
        self.header.pack_start(self.refresh_button)
        self.header.pack_end(self.menu_button)

        # Main Content area boxes
        self.window_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.window_box.set_vexpand(True)
        self.set_child(self.window_box)

        self.sidebar_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.sidebar_box.set_size_request(200, 100)

        self.sidebar_button_list = Gtk.ListBox(
            vexpand=True, css_classes=['border-right'])

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)

        self.sidebar_box.append(self.sidebar_button_list)
        self.window_box.append(self.sidebar_box)
        self.window_box.append(self.content_box)

        # Create a stack to hold multiple pages

        self.sidebar_button_dict: Dict[str, Gtk.Button] = {}
        self.stack = Gtk.Stack()

        overview_box = Gtk.Box(vexpand=True,
                               hexpand=True,
                               orientation=Gtk.Orientation.VERTICAL,
                               name="overview-page")
        welcome_label = Gtk.Label(name="welcome-label",
                                  label="Welcome to CaptainsLog",
                                  css_classes=["title", "overview-title"])

        dc = docker.from_env()
        dc.configs.client
        # docker overview metrics
        welcome_content = """Docker socket location: {}
        \n\nYou currently have {} docker containers tracked by the docker daemon.
        \n\nSelect a container from the left to view its logs""".format(dc.api.base_url, len(docker.from_env().containers.list()))
        welcome_text = Gtk.Label(name="welcome-text",
                                 label=welcome_content,
                                 wrap=True,
                                 wrap_mode=Gtk.WrapMode.WORD,
                                 justify=Gtk.Justification.CENTER,
                                 css_classes=["welcome-text"],
                                 )

        overview_box.append(welcome_label)
        overview_box.append(welcome_text)

        self.add_sidebar_item(item_name="overview-page", item_label="Overview")
        self.stack.add_titled(
            overview_box, name="overview-page", title="Overview")

        self.stack.set_visible_child_name("overview-page")

        # initial stack updating
        self.update_container_stack()
        self.content_box.append(self.stack)

        # update stack every .25 seconds
        # TODO: Make this on event from docker daemon
        GLib.timeout_add(250, self.update_container_stack)
        self.match_iter = None
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

        # update list of docker containers
        self.containers: List[Container] = list_containers()

        # get current stack pages
        # TODO: Support having pages that are not associated
        # with a docker container (e.g. welcome page)
        page: Gtk.StackPage
        current_pages: List[Gtk.StackPage] = [
            page for page in self.stack.get_pages()]
        current_page_names = [page.get_name() for page in current_pages]
        # filter pages depending on if it belongs to a container or not
        current_page_names = [
            name for name in current_page_names if name != 'overview-page']

        current_container_names = [
            container.name for container in self.containers]

        # if the container is gone and thread is still alive, we should join the thread
        join_threads(thread_dict=thread_dict,
                     current_page_names=current_page_names,
                     current_container_names=current_container_names)

        # update sidebar button colors, add new stack elements
        # for new docker containers
        for container in self.containers:
            try:
                container.reload()
            except:
                continue
            if container.name in self.sidebar_button_dict:
                update_container_status_css(
                    button=self.sidebar_button_dict[container.name], status=container.status)
            # restart thread if container has been seen previously
            if container.name in current_page_names:
                if not thread_dict[container.name].is_alive():
                    thread_dict[container.name].start()
                continue

            container_box, container_info, container_log_save_button, container_log_search = prepare_container_log_elements()
            container_box.set_name(container.name)
            # setup signal functionality
            container_log_save_button.connect("clicked", self.on_container_save_click, container_info)
            container_log_search.connect("activate", self.next_match, container_info)
            container_log_search.connect("next-match", self.next_match, container_info)
            container_log_search.connect("previous-match", self.prev_match, container_info)
            
            # tail docker logs in separate threads, calling back to main Gtk thread to update TextView
            thread_dict[container.name] = StoppableThread(
                target=container_log_tailer, args=[container_info, container.name])
            thread_dict[container.name].daemon = True
            thread_dict[container.name].start()

            self.add_sidebar_item(item_name=container.name)

            self.stack.add_titled(child=container_box,
                                  name=container.name,
                                  title=container.name)

        return True

    def add_sidebar_item(self, item_name: str, item_label: str = None):
        if item_label is None:
            item_label = item_name
        sidebar_row = Gtk.ListBoxRow(name=item_name)
        new_button = Gtk.Button(name=item_name, label=item_label)
        new_button.connect('clicked', self.on_sidebar_button_clicked)
        self.sidebar_button_dict[item_name] = new_button
        sidebar_row.set_child(new_button)
        self.sidebar_button_list.append(sidebar_row)

    def on_sidebar_button_clicked(self, button: Gtk.Button):

        # update main view content based on clicked button
        # and set selected row on sidebar
        # print(f"old selected button = {self.sidebar_button_list.get_selected_row().get_name()}")
        # print(f"new selected button = {button.get_name()}")
        self.stack.get_child_by_name(self.sidebar_button_list.get_selected_row().get_name()).set_visible(False)
        self.sidebar_button_list.select_row(button.get_parent())
        self.stack.get_child_by_name(self.sidebar_button_list.get_selected_row().get_name()).set_visible(True)
        # disable visibility of current stack child, turn on visibility of new child
        self.stack.set_visible_child_name(button.get_name())
        # print(f"new visible child name = {self.stack.get_visible_child().get_name()}")

    def quit_activated(self, action, parameter):
        # print("quit")<Ctrl>
        app.quit()
        pass

    def about_activated(self, action, parameter):
        self.about_dialog.show()
    

    def on_container_save_click(self, button: Gtk.Button, container_info: Gtk.TextView):
        # container_info: Gtk.TextView = button.get_child()
        
        save_file_dialog = Gtk.FileChooserDialog(title="Save File As",
                                                 transient_for=self,
                                                 action=Gtk.FileChooserAction.SAVE)
        save_button = save_file_dialog.add_button("Save", response_id=Gtk.ResponseType.ACCEPT)
        save_button.add_css_class("success")
        save_file_dialog.connect("response", self.on_save_response, container_info.get_buffer())
        save_file_dialog.show()

    def on_save_response(self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType, buffer: Gtk.TextBuffer):
        
        if response == Gtk.ResponseType.ACCEPT:
            self.save_text_buffer(file=dialog.get_file(), buffer=buffer)
        dialog.close()

    def save_text_buffer(self, file: Gio.File, buffer: Gtk.TextBuffer):

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()

        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        # If there is nothing to save, return early
        if not text:
            return

        bytes = GLib.Bytes.new(text.encode('utf-8'))

        # Start the asynchronous operation to save the data into the file
        file.replace_contents_bytes_async(bytes,
                                        None,
                                        False,
                                        Gio.FileCreateFlags.NONE,
                                        None,
                                        self.save_file_complete)

    def save_file_complete(self, file: Gio.File, result):
        res = file.replace_contents_finish(result)
        info = file.query_info("standard::display-name",
                            Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()
        if not res:
            print(f"Unable to save {display_name}")

    def search_text(self, widget: Gtk.SearchEntry, text_view: Gtk.TextView):
        search_text = widget.get_text()
        start_iter = text_view.get_buffer().get_start_iter()
        self.match_iter = start_iter.forward_search(
            search_text, Gtk.TextSearchFlags.CASE_INSENSITIVE, None
        )

        if self.match_iter:
            self.select_match(text_view)

    def select_match(self, text_view: Gtk.TextView):
        match_start, match_end = self.match_iter
        text_view.scroll_to_iter(match_start, 0.0, True, 0.5, 0.5)
        textbuffer = text_view.get_buffer()
        textbuffer.select_range(match_start, match_end)

    def next_match(self, widget: Gtk.SearchEntry, text_view: Gtk.TextView):
        if self.match_iter:
            next_iter = self.match_iter[1].forward_search(
                widget.get_text(),
                Gtk.TextSearchFlags.CASE_INSENSITIVE,
                None,
            )
            if next_iter:
                self.match_iter = next_iter
                self.select_match(text_view)
            else:
                self.search_text(widget=widget, text_view=text_view)
        else:
            self.search_text(widget=widget, text_view=text_view)

    def prev_match(self, widget: Gtk.SearchEntry, text_view: Gtk.TextView):
        if self.match_iter:
            prev_iter = self.match_iter[0].backward_search(
                widget.get_text(),
                Gtk.TextSearchFlags.CASE_INSENSITIVE,
                None,
            )
            if prev_iter:
                self.match_iter = prev_iter
                self.select_match(text_view=text_view)
            else:
                self.search_text(widget=widget, text_view=text_view)

class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = MyApp(application_id="com.alexdlukens.CaptainsLog")
