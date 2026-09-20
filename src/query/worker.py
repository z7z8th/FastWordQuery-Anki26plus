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

import multiprocessing as mp
import queue
import pickle
import traceback
from collections import defaultdict

import anki.notes
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo
from anki.notes import Note
from anki.collection import Collection

from ..context import config
from ..lang import _
from ..gui import ProgressWindow

from .common import InvalidWordException, inspect_note, query_flds, QueryStat, update_note_fields
from ..service import Service, QueryResult

__all__ = ['QueryWorkerManager']


def _process_worker_loop(task_queue: mp.Queue, result_queue: mp.Queue, query_fields):
    """
    Top-level worker function executed in isolated child processes.
    Pulls lightweight note payload data, performs queries, and sends back results.
    """
    # col = Collection(col_path)
    # print(f'---_process_worker_loop col_path {col_path}')
    while True:
        try:
            # Poll task queue
            payload = task_queue.get(block=True, timeout=0.1)
        except queue.Empty:
            break

        if payload is None:  # Poison pill to gracefully shut down worker
            break

        note_id, note_fields_len_list, word_ord, word, cfg_qfields = payload
        # note = col.get_note(note_id)
        print(f'--- note_id {note_id} payload {payload}')

        try:
            # Reconstruction or dummy encapsulation if query_flds needs field data
            # Adjust query_flds call depending on whether it works with dict or Note
            results, qstat, missed_css_info_list = query_flds(note_fields_len_list, word_ord, word, cfg_qfields, query_fields)
            # result_queue.put(('success', (note_id, results, qstat, missed_css_info_list)))
            result_queue.put(('success', (note_id, pickle.dumps(results), pickle.dumps(qstat), missed_css_info_list)))
        except InvalidWordException:
            traceback.print_exc()
            result_queue.put(('invalid_word', (note_id,)))
        except Exception as e:
            traceback.print_exc()
            result_queue.put(('error', (note_id, str(e), traceback.format_exc())))

    print(f'--- worker {mp.current_process()} exit')
    # col.close()


class QueryWorkerManager(object):
    """
    Query Worker Process Manager using multiprocessing.Process and Queues
    """

    def __init__(self):
        self.processes = []
        self.task_queue = mp.Queue()
        self.result_queue = mp.Queue()
        
        self.progress = ProgressWindow(mw)
        self.total = 0

        self.qstat = QueryStat()
        self.missed_css_info_list = list()
        self.flush = True
        self.query_fields:list[int] = []
        self.note_map = {}  # Keep track of Note instances by ID on the main process
        self.fails = 0

    def add_note_task(self, note: Note):
        """Prepares note data for multiprocessing serialization."""
        self.note_map[note.id] = note
        # Send lightweight primitive data instead of SWIG/C++ dependent Note objects
        # note_id, note_fields, word_ord, word, cfg_qfields = payload
        note_fields_len_list = [ len(f) for f in note.fields ]
        word_ord, word, cfg_qfields = inspect_note(note)
        payload = (note.id, note_fields_len_list, word_ord, word, cfg_qfields)

        self.task_queue.put(payload)

    def start(self):
        self.total = self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else len(self.note_map)
        self.progress.start(min=0, max=self.total)
        self.update_progress()

        num_workers = min(config.thread_number, self.total) if self.total > 1 else 1

        # Spawn worker processes
        for _ in range(num_workers):
            p = mp.Process(
                target=_process_worker_loop,
                args=(self.task_queue, self.result_queue, self.query_fields)
            )
            p.daemon = True
            p.start()
            self.processes.append(p)

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

    def update_progress(self):
        self.progress.update_labels(self.qstat)
        mw.app.processEvents()

    def process_results(self):
        """Drains the IPC result queue without blocking the main event loop."""
        while not self.result_queue.empty():
            try:
                status, data = self.result_queue.get_nowait()
                if status == 'success':
                    note_id, results, qstat, missed_css_info_list = data
                    results = pickle.loads(results)
                    qstat = pickle.loads(qstat)
                    note = self.note_map.get(note_id)
                    if note:
                        self.update(note, results, qstat, missed_css_info_list)
                elif status == 'invalid_word':
                    self.fails += 1
                    if self.total == 1:
                        showInfo(_("NO_QUERY_WORD"))
                elif status == 'error':
                    note_id, err_str, tb = data
                    print(f"Error processing note {note_id}: {err_str}\n{tb}")
            except queue.Empty:
                break

    def join(self):
        """Waits for processes to complete while maintaining UI responsiveness."""
        timer = QElapsedTimer()
        timer.start()

        while any(p.is_alive() for p in self.processes) or not self.result_queue.empty():
            # Handle user cancellation
            if self.progress.is_aborted():
                self.terminate_processes()
                break

            # Drain IPC message queue
            self.process_results()
            self.update_progress()
            mw.app.processEvents()

            # Brief sleep to prevent high CPU loop on the main thread
            QThread.msleep(50)

        # Final drain of any lingering queue messages
        self.process_results()
        self.progress.set_finished()

    def terminate_processes(self):
        """Terminates active child processes immediately."""
        for p in self.processes:
            if p.is_alive():
                p.terminate()
                p.join()

    def handle_flush(self, note: anki.notes.Note):
        if self.flush and note:
            try:
                note.col.update_note(note)
            except Exception:
                # Fallback if col.update_note is not present in older Anki versions
                note.flush()