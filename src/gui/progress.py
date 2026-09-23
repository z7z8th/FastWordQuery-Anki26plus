# -*- coding:utf-8 -*-
#
# Copyright (C) 2018 sthoo <sth201807@gmail.com>
#
# Support: Report an issue at https://github.com/sth2018/FastWordQuery/issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version; http://www.gnu.org/copyleft/gpl.html.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import time
from collections import defaultdict

from aqt.qt import *

from .base import APP_ICON
from ..lang import _
from ..utils import QueryStat
from ..context import gui_processEvents

__all__ = ['ProgressWindow']


def get_info_msg(qstat):
    msg = \
        f"""<strong>{_('QUERIED')}</strong>
        <p>{'-' * 45}</p>
        <p>{_('CARDS')} <b>{qstat.note_count}</b> {_('WORDS')}</p>
        <p>{_('SUCCESS')} <b>{qstat.field_success_count}</b> {_('FIELDS')}</p>
        <p>{_('SKIPED')} <b>{qstat.field_skip_count}</b> {_('FIELDS')}</p>
        <p>{_('UPDATE')} <b>{qstat.field_updated_count}</b> {_('FIELDS')}</p>
        <p>{_('FAILURE')} <b>{qstat.field_error_count}</b> {_('FIELDS')}</p>
    """
    return msg



class ProgressWindow(QProgressDialog):
    """
    Query progress window
    """

    def __init__(self, parent=None):
        # self.app = QApplication.instance()
        # self._win = None
        super().__init__(parent)
        self._msg_count = QueryStat()
        self._last_update = 0
        self._first_time = 0
        self._aborted = False

    def keyPressEvent(self, event):
        # print(f'---keyPressEvent {event.key()}')
        if event.key() == Qt.Key.Key_Escape:
            # Manually trigger cancel(), which emits canceled signal
            self.finish()
            event.accept()
        else:
            super().keyPressEvent(event)
                
    def update_labels(self, qstat:QueryStat):
        if self.is_aborted():
            return

        self._msg_count = qstat
        query_stat_info = get_info_msg(qstat)
        self._update(
            label=query_stat_info,
            value=qstat.note_count)
        self.adjustSize()
        gui_processEvents()

    def update_title(self, title):
        if self.is_aborted():
            return
        self.setWindowTitle(title)

    def start(self, max=0, min=0, label=None, parent=None):
        self._msg_count.reset()
        # setup window
        label = label or _("Processing...")
        # parent = parent or self.app.activeWindow() or self.mw
        # self._win = QProgressDialog(label, '', min, max, parent)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setCancelButton(None)
        self.canceled.connect(self.finish)
        self.setWindowTitle("FastWQ - Querying...")
        # TODO
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setWindowIcon(APP_ICON)
        self.setAutoReset(False)
        self.setAutoClose(False)
        self.setMinimum(0)
        self.setMaximum(max)
        # we need to manually manage minimum time to show, as qt gets confused
        # by the db handler
        # self.setMinimumDuration(100000)
        self._first_time = time.time()
        self._last_update = time.time()
        self.show()
        self.setValue(0)
        bar = self.findChild(QProgressBar)
        if bar:
            # Enable center-aligned text inside the progress bar
            bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Set custom text format (%p% = percentage, %v% = current value, %m% = total)
            bar.setFormat(r"Completed %v of %m files (%p%)")
        else:
            print(f"*** Error: can't find QProgressBar in QProgressDialog")
        gui_processEvents()

    def is_aborted(self):
        # self.aborted = True
        # if processEvents.processEvents() is not called, wasCanceled() NEVER returns True.
        # Calling progress.reset() or progress.setValue(progress.maximum()) will reset wasCanceled() back to False
        # self.wasCanceled() or 
        return self._aborted or sip.isdeleted(self)

    def set_finished(self):
        if self.is_aborted():
            return
        self.setWindowTitle('FastWQ - Finished')
        self.setValue(self.maximum())
        # self.setLabelText("Done")

    def finish(self):
        print(f'---progressbar.finish called')
        self._aborted = True
        self.hide()
        self.destroy()

    def _update(self, label, value, process=True):
        elapsed = time.time() - self._last_update
        if label:
            self.setLabelText(label)
        if value:
            self.setValue(value)
        if process and elapsed >= 0.2:
            gui_processEvents()
            self._last_update = time.time()
            self.update()
