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

import io
import os
import re
import shutil
import unicodedata
from collections import defaultdict
import traceback

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

from ..constants import Template
from ..context import config
from ..service import Service, QueryResult, copy_static_file, service_pool
from ..service.base import LocalService, WordNotFoundError
from ..utils import wrap_css, QueryStat
from ..lang import _

from .base import *
from ..service.worker import *

__all__ = [
    'update_note_fields', 'update_note_field',
    'promot_choose_css', 'add_to_tmpl', 'query_flds', 'inspect_note'
]


def inspect_note(note):
    """
    inspect the note, and get necessary input parameters
    return word_ord: field index of the word in current note
    return word: the word
    return fields: dicts map of current note
    """

    mconf = config.get_query_configs(note.note_type()['id'])
    idx = mconf['default']
    if idx<0 or idx >= len(mconf['query_configs']):
        return -1, '',[]
    
    cfg = mconf['query_configs'][idx]
    fields = cfg['fields']
    for i, fld in enumerate(fields):
        if fld.get('word_checked', False):
            word_ord = i
            break
    else:
        # if no field is checked to be the word field, default the first one.
        word_ord = 0

    def purify_word(word):
        return word.strip() if word else ''

    word = purify_word(note.fields[word_ord])
    return word_ord, word, fields


def update_note_fields(note, results: defaultdict[int, QueryResult]):
    """
    Update query result to note fields, return updated fields count.
    """

    if not results or not note or len(results) == 0:
        return 0
    count = 0
    for ord, fld in results.items():
        # print(f"--- update_note_fields `{ord}` `{fld}`")
        if isinstance(fld, QueryResult) and ord < len(note.fields):
            count += update_note_field(note, ord, fld)
        else:
            print(f"*** Error: update_note_fields note `{note}` fld type {fld} or ord {ord} max_ord {len(note.fields)}")

    return count


def update_note_field(note, fld_ord: int, fld_result: QueryResult):
    """
    Update single field, if result is valid then return 1, else return 0
    """

    # js process: add to template of the note model
    mw.taskman.run_on_main(lambda: add_to_tmpl(note, js_list=fld_result.js_list, js_files=fld_result.js_files, 
                    css_list=fld_result.css_list, css_files=fld_result.css_files))

    result = fld_result.result

    if not config.force_update and not result:
        return 0

    value = result if result else ''
    if note.fields[fld_ord] != value:
        note.fields[fld_ord] = value
        return 1

    return 0


def promot_choose_css(missed_css_info_list):
    """
    Choose missed css file and copy to user folder
    """
    checked = set()
    for css in missed_css_info_list:
        css_file = css['file']
        if not os.path.exists(css_file) and not css['file'] in checked:
            checked.add(css['file'])
            msg = Template.miss_css.format(dict=css['title'], css=css['file'])
            print(msg)
            showInfo(msg)
            try:
                dir = os.path.dirname(css['dict_path'])
                filepath, filter = QFileDialog.getOpenFileName(
                                            directory=dir,
                                            caption=u'Choose css file',
                                            filter=u'CSS (*.css)')
                # print(f"---promot_choose_css {filepath} {css_file}")
                if filepath:
                    shutil.copyfile(filepath, css_file)
                    wrap_css(css_file)
                else:
                    print(f'*** No css file for {css_file} choosed.')
            except KeyError:
                traceback.print_exc()
                pass


class ReschedulableTimer:

    def __init__(self):
        self.timer = QTimer()
        self.timer.setSingleShot(True)

    def schedule(self, delay_ms, func, *args, **kwargs):
        # Stop existing run if it hasn't fired yet
        if self.timer.isActive():
            self.timer.stop()

        # Disconnect any old target function
        try:
            self.timer.timeout.disconnect()
        except (TypeError, RuntimeError):
            pass

        # Bind parameters and connect
        def _wrapper():
            func(*args, **kwargs)

        self.timer.timeout.connect(_wrapper)

        # Start or restart timer
        self.timer.start(delay_ms)

save_timer = ReschedulableTimer()

def add_to_tmpl(note, js_list=[], js_files=[], css_list=[], css_files=[]):
    # templates
    """
    [{ 
        'name': 'Card 1',
        'qfmt': '{{Front}}\n\n',
        'did': None,
        'bafmt': '',
        'afmt': '{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}\n\n{{12}}\n\n{{44}}\n\n',
        'ord': 0,
        'bqfmt': '',
        'css': '',
    }]
    """

    # print(f"--- add_to_tmpl js_list {js_list} js_files {js_files} css_list {css_list} css_files {css_files}")
    model = note.note_type()


    note_afmt = model['tmpls'][0]['afmt']

    if js_list:
        for js in js_list:
            js = js.strip()
            if js in note_afmt:
                continue
            if not js.startswith(u'<script') and not js.endswith(u'/script>'):
                js = f'\n<script type="text/javascript">\n{js}\n</script>'
            note_afmt += js

    if js_files:
        for file in js_files:
            # print(f"### warning {file} not copied yet")
            src = f'''\n<script src="{file}" type="text/javascript"></script>'''
            if src not in note_afmt:
                note_afmt += src

    model['tmpls'][0]['afmt'] = note_afmt

    note_css = model['css']
    text_align = '.card { text-align: left; }'
    if text_align not in note_css:
        note_css += f'\n{text_align}\n'

    if css_list:
        for css in css_list:
            css = css.strip()
            if css in note_css:
                continue
            if not css.startswith('<style'):
                css = f"<style>\n{css}\n</style>"
            note_css = f"{note_css}\n{css}"

    if css_files:
        if '@import' not in note_css:
            note_css = f'\n{note_css}'

        for file in css_files:
            src = f'@import url("{file}");'
            if src not in note_css:
                print(f'Inject css file `{src}`')
                note_css = f"{src}\n{note_css}"

    model['css'] = note_css

    def _save_model():
        print(f'--- Saving model {model['name']}')
        mw.col.models.save(model)
    # QTimer.singleShot(1000*10, lambda: mw.col.models.save(model))
    save_timer.schedule(1000*5, _save_model)


def query_flds_by_note(note, qfields:list[int]) -> tuple[defaultdict[int, QueryResult], QueryStat, list]:
    word_ord, word, cfg_qfields = inspect_note(note)
    return query_flds(note.fields, word_ord, word, cfg_qfields, qfields=qfields)


