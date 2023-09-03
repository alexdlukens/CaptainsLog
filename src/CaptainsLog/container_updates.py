import gi
import datetime
import re
import threading
import time
from typing import List

import docker
from docker.models.containers import Container
from gi.repository import GLib, Gtk, Gio


def remove_control_characters(s):
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', s)


def update_container_status_css(button: Gtk.Button, status: str):
    """Update button with css class based on docker container status

    Args:
        button (Gtk.Button): button corresponding to docker container in sidebar
        status (str): current status of the docker container
    """

    try:
        css_classes = button.get_css_classes()

        # name of new css class
        new_container_class = f'docker-container-{status}'

        # get all the css classes we have added
        container_classes: List[str] = []
        for class_name in css_classes:
            if class_name.startswith('docker-container-'):
                container_classes.append(class_name)

        # already has the right class
        if new_container_class in container_classes and len(container_classes) == 1:
            return True

        for class_name in container_classes:
            button.remove_css_class(class_name)
        button.add_css_class(new_container_class)

    except Exception:
        return False

    return True


def prepare_container_log_elements():
    """Make GTK elements for individual container log
    """

    container_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                            hexpand=True,
                            vexpand=True,
                            visible=False)

    # otherwise create new stack object for new container
    container_scroll_window = Gtk.ScrolledWindow(
        vexpand=True, hexpand=True)

    container_info = Gtk.TextView()
    container_info.add_css_class('container-text')
    container_scroll_window.set_child(container_info)

    container_action_bar = Gtk.ActionBar(hexpand=True,
                                         css_classes=['container-action-bar'])
    container_log_save_button = Gtk.Button(label="Save as")
    container_action_bar.pack_start(container_log_save_button)
    container_log_search = Gtk.SearchEntry(placeholder_text="Search Log")
    container_action_bar.pack_end(container_log_search)

    container_box.append(container_action_bar)
    container_box.append(container_scroll_window)

    return container_box, container_info, container_log_save_button, container_log_search


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


def clear_container_log(text_view: Gtk.TextView):
    """Erase all content from passed text view
    """
    buffer = text_view.get_buffer()
    buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())


def container_log_tailer(text_view: Gtk.TextView, container_name: str):
    current_thread = threading.current_thread()
    dc = docker.from_env()
    container: Container = dc.containers.get(container_name)
    text_view.set_wrap_mode(Gtk.WrapMode.WORD)

    # erase container text view on thread start
    if 'since_time' not in locals():
        GLib.idle_add(clear_container_log, text_view)
        since_time = None

    text_to_append = ""
    while True:
        if current_thread.stopped():
            # add text needing to be appended before stopping
            if text_to_append:
                GLib.idle_add(update_container_log, text_view, text_to_append)
            # break from infinite loop when thread is stopped (e.g. on update)
            return
        new_since_time = datetime.datetime.utcnow()
        try:
            container_logs: bytes = container.logs(
                since=since_time, until=new_since_time)
            since_time = new_since_time
            if container_logs:
                # only update UI when new logs generated
                new_text = container_logs.decode('utf-8')
                # strip control characters other than newline
                new_text = remove_control_characters(new_text)
                text_to_append += new_text

            if text_to_append:
                # if we have text to add to log, and the container box is visible
                # e.g. (stack page is currently selected)
                if text_view.get_parent().get_parent().is_visible():
                    GLib.idle_add(update_container_log,
                                  text_view,
                                  text_to_append,
                                  priority=GLib.PRIORITY_HIGH)
                    text_to_append = ""

        except:
            return

        time.sleep(0.5)  # TODO: make this a setting in the application
