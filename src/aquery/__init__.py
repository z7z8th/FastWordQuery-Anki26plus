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
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# from collections import defaultdict
# import os
# import shutil
# import unicodedata
import re

# from aqt import mw

from .manager import QueryWorkerManager
from .common import promot_choose_css, inspect_note, QueryStat

# from ..constants import Endpoint, Template
from ..context import config
from ..lang import _
from ..service import service_manager, QueryResult, copy_static_file
# from ..service.base import LocalService
# from ..utils import Empty, MapDict, Queue, wrap_css
from aqt.utils import showInfo, showText, tooltip


__all__ = ['query_from_browser', 'query_from_editor_fields', 'QueryStat']

def natural_sort_key(s: str):
    """Splits string into a list of strings and integers for natural sorting."""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", s)
    ]

def get_note_deck_name(browser, note) -> str:
    """Helper to get the deck name of a note's first card."""
    cards = note.cards()
    if not cards:
        return ""
    # Get the deck object using the card's deck ID (did)
    deck = browser.mw.col.decks.get(cards[0].did)
    return deck["name"] if deck else ""

def query_from_browser(browser):
    """
    Query word from Browser
    """

    if not browser:
        return

    notes = [browser.mw.col.get_note(note_id) for note_id in browser.selectedNotes()]
    # Sort the notes list in-place by deck name using natural sorting
    notes.sort(key=lambda note: natural_sort_key(get_note_deck_name(browser, note)))

    if len(notes) == 1:
        query_from_editor_fields(browser.editor)
    else:
        query_all(notes)
        # browser.model.reset()


def query_from_editor_fields(editor, fields:list[int] = []):
    """
    Query word fileds from Editor
    """

    if not editor or not editor.note:
        return

    word_ord, word, fields_map = inspect_note(editor.note)
    flush = not editor.addMode
    nomaps = True
    for each in fields_map:
        dict_unique = each.get('dict_unique', '').strip()
        ignore = each.get('ignore', True)
        if dict_unique and not ignore:
            nomaps = False
            break
    if nomaps:
        from ..gui import show_options
        tooltip(_('PLS_SET_DICTIONARY_FIELDS'))
        show_options(
            editor.parentWindow,
            editor.note.note_type()['id'],
            query_from_editor_fields,
            editor,
            fields
        )
    else:
        editor.setNote(editor.note)
        query_all([editor.note], flush, fields)
        editor.setNote(editor.note, focusTo=0)
        editor.saveNow(lambda: print("Saved"))


def query_all(notes, flush=True, fields:list[int]=[]):
    """
    Query maps word fileds
    """

    if len(notes) == 0:
        return

    work_manager = QueryWorkerManager()
    #work_manager.reset()
    #progress.start(max=len(notes), min=0, immediate=True)
    work_manager.flush = flush
    work_manager.query_fields = fields
    # queue = work_manager.queue

    for note in notes:
        # queue.put(note)
        work_manager.add_note_task(note)

    work_manager.start()
    work_manager.join()
    
    qstat = work_manager.qstat
    #progress.finish()
    promot_choose_css(work_manager.missed_css_info_list)
    tooltip(f'{_('UPDATED')} {qstat.note_count} {_('CARDS')}, {qstat.field_updated_count} {_('FIELDS')}',
            period=3000)
    #work_manager.clean()
    service_manager.clean()
