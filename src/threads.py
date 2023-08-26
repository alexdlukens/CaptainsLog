import threading
from threads import StoppableThread
from typing import Dict, List


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def join_threads(thread_dict: Dict[str, StoppableThread], current_page_names: List[str], current_container_names: List[str]):
    """Join threads for Docker containers that are no longer shown by the docker daemon (e.g. docker system prune performed, etc.)

    Args:
        thread_dict (Dict[str, StoppableThread]): dictionary keeping track of threads by docker container name
        current_page_names (List[str]): names of pages currently in Gtk stack
        current_container_names (List[str]): list of docker container names present in the docker daemon
    """
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

    return
