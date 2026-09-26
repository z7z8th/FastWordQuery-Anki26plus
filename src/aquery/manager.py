#-*- coding:utf-8 -*-
#
# Copyright (C) 2018 sthoo <sth201807@gmail.com>
#
# Support: Report an issue at https://github.com/sth2018/FastWordQuery/issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version; http://www.gnu.org/copyleft/gpl.html.
import os
import sys
import multiprocessing as mp
import queue
import pickle
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
import time

import anki.notes
from aqt import mw, gui_hooks
from aqt.qt import QElapsedTimer, QThread
from anki.notes import Note
# from anki.collection import Collection

from .. import context
from ..context import config, ADDON_NAME, gui_processEvents
from ..lang import _

from .common import inspect_note, query_flds, QueryStat, update_note_fields
from ..service import Service, QueryResult

from ..service.query_worker import *

# mp.set_start_method("spawn", force=True)

__all__ = ['QueryWorkerManager']

def get_anki_spawn_context():
    ctx = mp.get_context("spawn")
    anki_dir = os.path.dirname(sys.executable)
    
    # Check for embedded python binaries inside Anki's install folder
    possible_pythons = [
        os.path.join(anki_dir, "python", "bin", "python3"),
        os.path.join(anki_dir, "python", "bin", "python"),
        os.path.join(anki_dir, "lib", "python3"),
    ]
    
    for py_bin in possible_pythons:
        if os.path.isfile(py_bin) and os.access(py_bin, os.X_OK):
            print(f"--- ctx.set_executable {py_bin}")
            ctx.set_executable(py_bin)
            break

    return ctx


class QueryWorkerManager(object):
    """
    Query Worker Process Manager using multiprocessing.Process and Queues
    """

    def __init__(self):
        from ..gui import ProgressWindow

        self.processes = []
        self.ctx = get_anki_spawn_context()

        self.task_queue = self.ctx.Queue()
        self.result_queue = self.ctx.Queue()
        self.stop_event = self.ctx.Event()
        
        self.progress = ProgressWindow(mw.app.activeWindow())
        self.total = 0

        self.qstat = QueryStat()
        self.missed_css_info_list = list()
        self.flush = True
        self.query_fields:list[int] = []
        self.note_map = {}  # Keep track of Note instances by ID on the main process

        self.mdx_backend_lock = self.ctx.Lock()
        self.llm_lock = self.ctx.Lock()
        gui_hooks.profile_will_close.append(self.terminate_processes)

    def add_note_task(self, note: Note):
        """Prepares note data for multiprocessing serialization."""
        self.note_map[note.id] = note
        # Send lightweight primitive data instead of SWIG/C++ dependent Note objects
        # note_id, note_fields, word_ord, word, cfg_qfields = payload
        note_fields_len_list = [ len(f) for f in note.fields ]
        word_ord, word, cfg_qfields = inspect_note(note)
        if not word:
            print(f"***Warning: Field `{word_ord}` of `{note.fields[0]}` note {note} is empty. Skip querying this note.")
            return
        payload = (note.id, note_fields_len_list, word_ord, word, cfg_qfields)

        self.task_queue.put(payload)


    def start(self):
        self.reset_result_time()

        self.total = self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else len(self.note_map)
        self.progress.start(min=0, max=self.total)
        self.update_progress()

        num_workers = min(config.thread_number, self.total) if self.total > 1 else 1

        main_mod = sys.modules.get('__main__')
        # Store original __name__ attribute
        orig_name = getattr(main_mod, '__name__', None)
        # print(f'--- worker process_worker_loop.__module__ {process_worker_loop.__module__}')
        # print(f"--- worker sys.modules['__main__'] {sys.modules['__main__']}")
        main_module = sys.modules['__main__']
        main_mod_name = getattr(main_module.__spec__, "name", None)
        main_path = getattr(main_module, '__file__', None)
        # print(f'main_module {main_module} {dir(main_module)}')
        # print(f'main_mod_name {main_mod_name}')
        # print(f'main_path {main_path}')
        #### if error, try debug in sys lib multiprocesisng: spawn_main, _main

        try:
            # Temporarily unset or override __name__ so get_preparation_data()
            # does not set init_main_from_name to 'anki.__main__'
            if main_mod:
                setattr(main_mod.__spec__, 'name', f'{ADDON_NAME}.service.__init__')
            # print(f'__name__ {__name__}')
            # print(f'getattr(main_module.__spec__, "name", None) {getattr(main_module.__spec__, "name", None)}')

            # Spawn worker processes
            for _ in range(num_workers):
                p = self.ctx.Process(
                    target=process_worker_loop,
                    args=(self.stop_event, self.task_queue, self.result_queue, self.query_fields, self.mdx_backend_lock, self.llm_lock),
                    # Pass the parent's full sys.path list to the initializer
                    # initializer=_init_worker,
                    # initargs=(list(sys.path),)
                )
                p.daemon = True
                p.start()
                self.processes.append(p)

                # time.sleep(1)

                # print(f"Is worker alive? {p.is_alive()}")
                # print(f"Worker exit code: {p.exitcode}")
        finally:
            # Restore __main__.__name__ for Anki's main thread
            if main_mod and orig_name is not None:
                setattr(main_mod.__spec__, 'name', orig_name)


    def update(self, note, results: defaultdict[int, QueryResult], qstat: QueryStat, missed_css_info_list: list):
        """Applies query results to notes on the main Qt thread."""
        self.qstat += qstat
        val = update_note_fields(note, results)
        self.qstat.field_updated_count += val
        self.missed_css_info_list += missed_css_info_list

        if self.total > 1:
            if val > 0:
                self.handle_flush(note)
        else:
            self.handle_flush(note)

    def update_progress(self, force=False):
        if not self.last_update_progress:
            self.last_update_progress = datetime.now()
        elif not force and datetime.now() - self.last_update_progress < timedelta(seconds=1):
            return
        self.last_update_progress = datetime.now()
        
        self.qstat.elapsed_time = (datetime.now() - self.start_time).total_seconds()
        # print(f'elapsed time {self.qstat.elapsed_time}  ETA {self.qstat.estimated_time_done}')
        self.progress.update_labels(self.qstat)
        gui_processEvents()

    def reset_result_time(self):
        self.start_time = datetime.now()
        self.last_update_progress = None
        self.qstat.elapsed_time = 0
        self.qstat.estimated_time_done = 0

    def update_result_time(self):
        self.qstat.elapsed_time = (datetime.now() - self.start_time).total_seconds()
        try:
            self.qstat.estimated_time_done = int(datetime.now().timestamp() + (self.total - self.qstat.note_count) * \
                                                  (self.qstat.elapsed_time/(self.qstat.note_count-self.qstat.note_skip_count)))
        except:
            self.qstat.estimated_time_done = 0

    def process_results(self):
        """Drains the IPC result queue without blocking the main event loop."""
        while not self.result_queue.empty():
            try:
                status, data = self.result_queue.get_nowait()
                self.update_result_time()
                if status == 'success':
                    note_id, results, qstat, missed_css_info_list = data
                    # for debug _ForkingPickler.loads: None is not callable.
                    # results = pickle.loads(results)
                    # qstat = pickle.loads(qstat)
                    note = self.note_map.get(note_id)
                    if note:
                        self.update(note, results, qstat, missed_css_info_list)
                # elif status == 'invalid_word':
                #     self.qstat.field_error_count += 1
                    # if self.total == 1:
                    #     showInfo(_("NO_QUERY_WORD"))
                elif status == 'error':
                    self.qstat.field_error_count += 1
                    note_id, err_str, tb = data
                    print(f"Error processing note {note_id}: {err_str}\n{tb}")
            except queue.Empty:
                break
            except ValueError: # queue is closed when canceling
                break

    def join(self):
        """Waits for processes to complete while maintaining UI responsiveness."""

        while any(p.is_alive() for p in self.processes) or not self.result_queue.empty():
            # Handle user cancellation
            if self.progress.is_aborted():
                self.terminate_processes()
                break

            # Drain IPC message queue
            self.process_results()
            self.update_progress()
            gui_processEvents()

            # Brief sleep to prevent high CPU loop on the main thread
            time.sleep(0.2)

        for p in self.processes:
            p.join()

        print(f'*** All active child processes Exited Normally.')

        # Final drain of any lingering queue messages
        self.process_results()
        self.progress.set_finished()
        self.update_progress(force=True)

    def terminate_processes(self):
        """Terminates active child processes immediately."""
        print(f'*** Try stop all active child processes.')
        self.stop_event.set()
        self.task_queue.close()
        self.result_queue.close()
        self.task_queue.cancel_join_thread()
        self.result_queue.cancel_join_thread()

        while any(p.is_alive() for p in self.processes):
            for p in self.processes:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout = 0.1)
                    gui_processEvents()
        print(f'*** All active child processes Terminated.')

    def handle_flush(self, note: anki.notes.Note):
        if self.flush and note:
            try:
                note.col.update_note(note)
            except Exception:
                # Fallback if col.update_note is not present in older Anki versions
                note.flush()