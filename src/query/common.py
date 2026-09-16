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

from aqt.qt import *
from aqt.utils import showInfo

from ..constants import Template
from ..context import config
from ..libs.snowballstemmer import stemmer
from ..service import Service, QueryResult, copy_static_file, service_pool
from ..service.base import LocalService
from ..utils import wrap_css
from ..lang import _

__all__ = [
    'InvalidWordException', 'update_note_fields', 'update_note_field',
    'promot_choose_css', 'add_to_tmpl', 'query_flds', 'inspect_note'
]


class InvalidWordException(Exception):
    """Invalid word exception"""


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


def strip_combining(txt):
    """Return txt with all combining characters removed."""
    norm = unicodedata.normalize('NFKD', txt)
    return u"".join([c for c in norm if not unicodedata.combining(c)])


def update_note_fields(note, results: defaultdict[int, QueryResult]):
    """
    Update query result to note fields, return updated fields count.
    """

    if not results or not note or len(results) == 0:
        return 0
    count = 0
    for ord, fld in results.items():
        if isinstance(fld, QueryResult) and ord < len(note.fields):
            count += update_note_field(note, ord, fld)

    return count


def update_note_field(note, fld_ord:int, fld_result: QueryResult):
    """
    Update single field, if result is valid then return 1, else return 0
    """

    # js process: add to template of the note model
    add_to_tmpl(note, js_list=fld_result.js, js_files=fld_result.js_files, 
                css_list=fld_result.css, css_files=fld_result.css_file)

    result = fld_result.result

    if not config.force_update and not result:
        return 0

    value = result if result else ''
    if note.fields[fld_ord] != value:
        note.fields[fld_ord] = value
        return 1

    return 0


def promot_choose_css(missed_css):
    """
    Choose missed css file and copy to user folder
    """
    checked = set()
    for css in missed_css:
        dest_name = u'_' + css['file']
        if not os.path.exists(dest_name) and not css['file'] in checked:
            checked.add(css['file'])
            showInfo(
                Template.miss_css.format(dict=css['title'], css=css['file']))
            try:
                filepath = css['dict_path'][:css['dict_path'].rindex(os.path.
                                                                     sep) + 1]
                filepath = QFileDialog.getOpenFileName(
                    directory=filepath,
                    caption=u'Choose css file',
                    filter=u'CSS (*.css)')
                if filepath:
                    shutil.copy(filepath, dest_name)
                    wrap_css(dest_name)

            except KeyError:
                pass


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

    note_afmt = note.note_type()['tmpls'][0]['afmt']

    if js_list:
        for js in js_list:
            js = js.strip()
            if js in note_afmt:
                continue
            if not js.startswith(u'<script') and not js.endswith(u'/script>'):
                js = f'\n<script type="text/javascript">\n{js}\n</script>'
            note_afmt += js

    if js_files:
        js_files = js_files if isinstance(js_files, list) else [js_files]
        for file in js_files:
            print(f"### warning {file} not copied yet")
            src = f'''\n<script src="{file}" type="text/javascript"></script>'''
            if src not in note_afmt:
                note_afmt += src

    note.note_type()['tmpls'][0]['afmt'] = note_afmt

    note_css = note.note_type()['css']

    if css_list:
        for css in css_list:
            css = css.strip()
            if css in note_css:
                continue
            if not css.startswith('<style'):
                css = f"<style>\n{css}\n</style>"
            
            note_css = f"{note_css}\n{css}"

    if css_files:
        css_files = css_files if isinstance(css_files, list) else [css_files]
        for file in css_files:
            src = f'@import url("{file}")'
            if src not in note_css:
                note_css = f"{src}\n{note_css}"

    note.note_type()['css'] = note_css

def query_flds(note, qfields=None) -> tuple[defaultdict[int, QueryResult], int, list]:
    """
    Query fields of single note
    """
    # traceback.print_stack()

    word_ord, word, fields = inspect_note(note)
    # print(f"qfields {qfields}")
    # print(f'query_flds {word_ord}, {word}, {fields}')
    if not word:
        raise InvalidWordException

    if config.ignore_accents:
        word = strip_combining(word)

    # progress.update_title(u'Querying [[ %s ]]' % word)

    services: dict[str, Service] = {}
    tasks = []

    for i, field in enumerate(fields):
        if i == word_ord:
            continue
        if i == len(note.fields):
            break
        # ignore field
        ignore = field.get('ignore', False)
        if ignore:
            continue
        # skip valued
        skip = field.get('skip_valued', False)
        if skip and len(note.fields[i]) != 0:
            continue
        # cloze
        cloze = field.get('cloze_word', False)
        # normal
        dict_unique = field.get('dict_unique', '').strip()
        dict_fld_ord = field.get('dict_fld_ord', -1)
        fld_ord = field.get('fld_ord', -1)
        # print(f"dict_unique {dict_unique} dict_fld_ord {dict_fld_ord} fld_ord {fld_ord}")
        if dict_unique and dict_fld_ord != -1 and fld_ord != -1:
            if qfields is None or \
                fld_ord in qfields:
                
                svc = services.get(dict_unique, None)
                if svc is None:
                    svc = service_pool.get(dict_unique)
                    if svc and svc.support:
                        services[dict_unique] = svc

                # print(f"---service {svc} for {dict_unique}")
                if svc and svc.support:
                    tasks.append({
                        'dict_uniq': dict_unique,
                        'word': word,
                        'dict_fld_ord': dict_fld_ord,
                        'fld_ord': fld_ord,
                        'cloze': cloze,
                    })
    # print(f'---iter tasks {tasks}')
    if not tasks:
        print(f"*** Error: No tasks generated for word `{word}`")

    success_num = 0
    result = defaultdict(int)
    for task in tasks:
        try:
            service = services.get(task['dict_uniq'], None)
            qr = service.active(task['dict_fld_ord'], task['word'])
            # print(f"--- qr {str(qr)[:100]}")
            if qr:
                if task['cloze']:
                    qr['result'] = cloze_deletion(qr['result'], word)
                result.update({task['fld_ord']: qr})
                success_num += 1
        except Exception as e:
            print(traceback.format_exc())
            print(_("NO_QUERY_WORD"), e)
            pass

    missed_css = list()
    for service in services.values():
        if isinstance(service, LocalService):
            for css in service.missed_css:
                missed_css.append({
                    'dict_path': service.dict_path,
                    'title': service.title,
                    'file': css
                })
        service_pool.put(service)

    return result, -1 if len(tasks) == 0 else success_num, missed_css


def cloze_deletion(text, cloze):
    """create cloze deletion text"""
    text = text.replace('’', '\'')
    result = text
    offset = 0
    term = _stemmer.stemWord(cloze).lower()

    terms = re.finditer(r"\b[\w'-]*\b", text)
    tags = re.finditer(r"<[^>]+>", text)
    for m in terms:
        s = m.start()
        e = m.end()
        f = False
        for tag in tags:
            if s >= tag.start() and e <= tag.end():
                f = True
                break
        if f:
            continue
        word = text[s:e]
        if _stemmer.stemWord(word).lower() == term:
            ln = len(cloze)
            w = word
            if w[:ln].lower() == cloze.lower():
                e = s + ln
                w = word[:ln]
            result = result[:s + offset] + (
                config.cloze_str % w) + result[e + offset:]
            offset += len(config.cloze_str) - 2
    return result


_stemmer = stemmer('english')
