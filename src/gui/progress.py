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

__all__ = ['ProgressWindow']

_INFO_TEMPLATE = u''.join([
    u'<strong>' + _('QUERIED') + u'</strong>',
    u'<p>' + 45 * u'-' + u'</p>',
    u'<p>' + _('CARDS') + u' <b>{}</b> ' + _('WORDS') + u'</p>',
    u'<p>' + _('SUCCESS') + u' <b>{}</b> ' + _('FIELDS') + u'</p>',
    u'<p>' + _('SKIPED') + u' <b>{}</b> ' + _('FIELDS') + u'</p>',
    u'<p>' + _('UPDATE') + u' <b>{}</b> ' + _('FIELDS') + u'</p>',
    u'<p>' + _('FAILURE') + u' <b>{}</b> ' + _('FIELDS') + u'</p>',
])


class ProgressWindow(object):
    """
    Query progress window
    """

    def __init__(self, mw):
        self.mw = mw
        self.app = QApplication.instance()
        self._win = None
        self._msg_count = QueryStat()
        self._last_update = 0
        self._first_time = 0
        self._disabled = False
        self._aborted = False

    def update_labels(self, qstat:QueryStat):
        if self.is_aborted():
            return

        # if data.type == 'count':
        #     self._msg_count.update(data)
        # else:
        #     return
        self._msg_count = qstat

        # words_number, fields_number, fails_number, skips_number = (
        #     self._msg_count.get('words_number', 0),
        #     self._msg_count.get('fields_number', 0),
        #     self._msg_count.get('fails_number', 0),
        #     self._msg_count.get('skips_number', 0))
        query_stat_info = _INFO_TEMPLATE.format(qstat.note_count, 
                                            qstat.field_success_count, qstat.field_skip_count,
                                            qstat.field_updated_count, qstat.field_error_count)
        self._update(
            label=query_stat_info,
            value=qstat.note_count)
        self._win.adjustSize()
        self.app.processEvents()

    def update_title(self, title):
        if self.is_aborted():
            return
        self._win.setWindowTitle(title)

    def start(self, max=0, min=0, label=None, parent=None):
        self._msg_count.reset()
        # setup window
        label = label or _("Processing...")
        parent = parent or self.app.activeWindow() or self.mw
        self._win = QProgressDialog(label, '', min, max, parent)
        self._win.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._win.setCancelButton(None)
        self._win.canceled.connect(self.finish)
        self._win.setWindowTitle("FastWQ - Querying...")
        # TODO
        self._win.setModal(True)
        self._win.setWindowFlags(
            self._win.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._win.setWindowIcon(APP_ICON)
        self._win.setAutoReset(False)
        self._win.setAutoClose(False)
        self._win.setMinimum(0)
        self._win.setMaximum(max)
        # we need to manually manage minimum time to show, as qt gets confused
        # by the db handler
        # self._win.setMinimumDuration(100000)
        self._first_time = time.time()
        self._last_update = time.time()
        self._disabled = False
        self._win.show()
        self._win.setValue(0)
        bar = self._win.findChild(QProgressBar)
        if bar:
            # Enable center-aligned text inside the progress bar
            bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Set custom text format (%p% = percentage, %v% = current value, %m% = total)
            bar.setFormat(r"Completed %v of %m files (%p%)")
            # self._bar = bar
        else:
            print(f"*** Error: can't find QProgressBar in QProgressDialog")
        self.app.processEvents()

    def is_aborted(self):
        # self.aborted = True
        # if processEvents.processEvents() is not called, wasCanceled() NEVER returns True.
        # Calling progress.reset() or progress.setValue(progress.maximum()) will reset wasCanceled() back to False
        # self._win.wasCanceled() or 
        return self._aborted

    def set_finished(self):
        self._win.setWindowTitle('FastWQ - Finished')
        self._win.setValue(self._win.maximum())
        # self._win.setLabelText("Done")

    def finish(self):
        print(f'---progressbar.finish called')
        self._aborted = True
        self._win.hide()
        self._unset_busy()
        self._win.destroy()

    def _update(self, label, value, process=True):
        elapsed = time.time() - self._last_update
        if label:
            self._win.setLabelText(label)
        if value:
            self._win.setValue(value)
        if process and elapsed >= 0.2:
            self.app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
            self._last_update = time.time()
            self._win.update()

    def _set_busy(self):
        self._disabled = True
        self.mw.app.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

    def _unset_busy(self):
        self._disabled = False
        self.app.restoreOverrideCursor()
