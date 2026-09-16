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

import inspect
import os
import random
import traceback
# use ntpath module to ensure the windows-style (e.g. '\\LDOCE.css')
# path can be processed on Unix platform.
# However, anki version on mac platforms doesn't including this package?
# import ntpath
import re
import shutil
import sqlite3
import urllib
import zlib
import threading
from collections import defaultdict
from functools import wraps
from hashlib import md5, sha1
from typing import Callable, Optional
from copy import deepcopy

import requests
from bs4 import BeautifulSoup

from aqt import mw
from aqt.qt import QMutex, QThread

from ..context import config
from ..lang import _cl
from ..libs import MdxBuilder, StardictBuilder
from ..utils import MapDict, wrap_css
from ..libs.snowballstemmer import stemmer

try:
    import urllib2
except Exception:
    import urllib.request as urllib2

try:
    from cookielib import CookieJar
except Exception:
    from http.cookiejar import CookieJar

try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

__all__ = [
    'register', 'export', 'auto_bind_exports', 'copy_static_file', 'with_styles', 'with_scripts', 'parse_html', 'object_builder', 'get_hex_name', 'get_canonical_name',
    'Service', 'WebService', 'LocalService', 'MdxService', 'StardictService', 'QueryResult'
]

_default_ua = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 ' \
              '(KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36'


def get_hex_name(prefix, val, suffix):
    ''' get sha1 hax name '''
    hex_digest = sha1(val.encode('utf-8')).hexdigest().lower()
    name = '.'.join(
        ['-'.join([prefix, hex_digest[:8], hex_digest[8:16], hex_digest[16:24], hex_digest[24:32], hex_digest[32:], ]),
         suffix, ])
    return name


def get_canonical_name(prefix, val, suffix=''):
    '''meaning full canonical name with special chars repalced'''
    val = val.replace('://', '-')
    val = re.sub(r'''[^\w\d_'.-]+''', '_', val)
    val = re.sub(r'''_*-+_*''', '-', val)
    val = re.sub(r'''_+''', '_', val)
    val = re.sub(r'''^_+''', '', val)

    return f"{prefix}{val}{suffix}"


def _is_method_or_func(object):
    return inspect.isfunction(object) or inspect.ismethod(object)


def register(labels, enabled = False):
    """
    register the dict service with a labels, which will be shown in the dicts list.
    """

    def _deco(cls):
        cls._register_label_ = _cl(labels)
        cls._enabled_ = enabled

        methods = inspect.getmembers(cls, predicate=_is_method_or_func)
        exports: list[tuple[int, Callable]] = []
        for name, method in methods:
            attrs = getattr(method, '_export_attrs_', None)
            if attrs and attrs[1] == -1:
                # [(global _def_index_, method), (,)]
                exports.append((
                    getattr(method, '_def_index_', 0),
                    method
                ))

        exports = sorted(exports)
        # local sorted index
        for index, (_, method) in enumerate(exports):
            attrs = getattr(method, '_export_attrs_', None)
            attrs[1] = index

        return cls

    return _deco


def export(labels):
    """
    export dict field function with a labels, which will be shown in the fields list.
    """
    def _with(fld_func):
        @wraps(fld_func)
        def _deco(self, *args, **kwargs):
            res = fld_func(self, *args, **kwargs)
            return QueryResult(result=res) if not isinstance(res, QueryResult) else res

        _deco._export_attrs_ = [_cl(labels), -1]
        _deco._def_index_ = export.EXPORT_INDEX
        export.EXPORT_INDEX += 1
        return _deco

    return _with


export.EXPORT_INDEX = 0



# 1. Define decorator helper first
def auto_bind_exports(cls):
    for field_name, labels, getter_fn in getattr(cls, '_EXPORTS', []):

        def make_handler(fn=getter_fn):
            def handler(self):
                return fn(self)

            return handler

        exported_fn = export(labels)(make_handler())
        exported_fn.__name__ = field_name

        # if field_name == 'fld_ee':
        #     exported_fn = with_styles(css_file='_oxford.css')(exported_fn)

        setattr(cls, field_name, exported_fn)
    return cls



def copy_static_file(filename, new_filename=None, static_dir='static'):
    """
    copy file in static directory to media folder
    """
    abspath = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           static_dir,
                           filename)
    shutil.copy(abspath, new_filename if new_filename else filename)


def with_styles(**styles):
    """
    css: css strings
    css_file: specify the css file in static folder
    """

    def _with(fld_func):
        @wraps(fld_func)
        def _deco(cls, *args, **kwargs):
            res = fld_func(cls, *args, **kwargs)
            css, css_file, do_wrap, class_wrapper = \
                styles.get('css', None), \
                styles.get('css_file', None), \
                styles.get('do_wrap', False), \
                styles.get('wrap_class', '')

            def _wrap(html, css_obj, is_file=True):
                # wrap css and html
                if do_wrap or class_wrapper:
                    html = f'<div class="{class_wrapper}">{html}</div>'
                    return html, wrap_css(css_obj, is_file=is_file, class_wrapper=class_wrapper, get_canional_name=lambda val: get_canonical_name(cls.media_prefix, val))[0]
                return html, css_obj

            new_res = res
            new_css_file = ''
            if css_file:
                new_css_file = css_file if css_file.startswith('_') \
                    else u'_' + css_file
                # copy the css file to media folder
                copy_static_file(css_file, new_css_file)
                # wrap the css file
                new_res, new_css_file = _wrap(res, new_css_file)
            if new_css_file:
                new_css_file = [new_css_file]
            if css:
                new_res, css = _wrap(res, css, is_file=False)

            if not isinstance(res, QueryResult):
                res = QueryResult(result=new_res, css=css, css_files=new_css_file)
            else:
                res.result = new_res
                res.css = css
                res.css_files = new_css_file

            return res

        return _deco

    return _with


def with_scripts(js='', js_files=[]):
    """
    js: js strings
    js_files: js files list
    """

    def _with(fld_func):
        @wraps(fld_func)
        def _deco(cls, *args, **kwargs):
            res = fld_func(cls, *args, **kwargs)
            
            if not isinstance(res, QueryResult):
                res = QueryResult(result=res, js=js, js_files=js_files)
            else:
                res.js = js
                res.js_files = js_files

            return res

        return _deco

    return _with


_BS_LOCKS = [_threading.Lock(), _threading.Lock()]  # bs4 threading lock, overload protection


def parse_html(html):
    '''
    use bs4 lib parse HTML, run only 2 BS at the same time
    '''
    lock = _BS_LOCKS[random.randrange(0, len(_BS_LOCKS) - 1, 1)]
    lock.acquire()
    soup = BeautifulSoup(html, 'html.parser')
    lock.release()
    return soup

class Service(object):
    '''
    Dictionary Service Abstract Class
    '''

    def __init__(self):
        self.cache = defaultdict(defaultdict)
        self._unique = self.__class__.__name__
        self._exporters = self._get_exporters()  # [(label1, method1), (label2, method2)]
        # (label1, label2), (method1, method2) = zip(("label1", "method1"), ("label2", "method2"))
        self._fields, self._actions = zip(*self._exporters) \
            if self._exporters else (None, None)
        self._word = ''
        # query interval: default 500ms
        self.query_interval = 0.5

    def cache_this(self, result):
        self.cache[self.word].update(result)
        return result

    def is_field_cached(self, key):
        return (self.word in self.cache) and (key in self.cache[self.word])

    def get_cache_by_field(self, key):
        return self.cache[self.word].get(key, u'')

    def _get_from_api(self):
        return {}

    def _get_field(self, key, default=u''):
        return self.get_cache_by_field(key) if self.is_field_cached(key) else self._get_from_api().get(key, default)

    @property
    def unique(self):
        return self._unique

    @unique.setter
    def unique(self, value):
        self._unique = value

    @property
    def word(self):
        return self._word

    @word.setter
    def word(self, value):
        value = re.sub(r'</?\w+[^>]*>', '', value)
        self._word = value

    @property
    def quote_word(self):
        return urllib2.quote(self.word)

    @property
    def support(self) -> bool:
        return True

    @property
    def fields(self):
        return self._fields

    @property
    def actions(self):
        return self._actions

    @property
    def exporters(self):
        return self._exporters

    def _get_exporters(self):
        flds = dict()
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        # print(f'_get_exporters methods {methods}')
        for name, method in methods:
            export_attrs = getattr(method, '_export_attrs_', None)
            # print(f'_get_exporters export_attrs {export_attrs}')
            
            if export_attrs:
                label, index = export_attrs[0], export_attrs[1]
                flds.update({int(index): (label, method)})
        sorted_flds = sorted(flds)
        # [(label, method), (label, method)]
        return [flds[key] for key in sorted_flds]

    def active(self, dict_fld_ord, word):
        self.word = word
        if dict_fld_ord >= 0 and dict_fld_ord < len(self.actions):
            return self.actions[dict_fld_ord]()
        return QueryResult.default()

    @staticmethod
    def get_anki_label(filename, type_):
        formats = {
            'audio': config.sound_str,
            'img': u'<img src="{0}">',
            'video': u'<video controls="controls" width="100%" height="auto" src="{0}"></video>'
        }
        return formats[type_].format(filename)


type ObjectBuilder = Callable[[], object]


from functools import partial
def object_builder(service, *args, **kwargs)-> ObjectBuilder:
    return partial(service, *args, **kwargs)

# def object_builder(service, *args, **kwargs)-> Callable[[], Service]:
#     """
#     wrap the service class constructor
#     """

#     def _service() -> Service:
#         return service(*args, **kwargs)

#     return _service


class WebService(Service):
    """
    Web Dictionary Service
    """

    def __init__(self):
        super(WebService, self).__init__()
        self._cookie = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self._cookie))
        self.query_interval = 1.0

    @property
    def title(self):
        return getattr(self, '_register_label_', self.unique)

    def get_response(self, url, data=None, headers=None, timeout=10):
        default_headers = {
            'User-Agent': _default_ua
        }
        if headers:
            default_headers.update(headers)

        request = urllib2.Request(url, headers=default_headers)
        try:
            response = self._opener.open(request, data=data, timeout=timeout)
            data = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
            return data
        except Exception:
            return u''

    @classmethod
    def download(cls, url, filename, timeout=15):
        import socket
        socket.setdefaulttimeout(timeout)
        try:
            with open(filename, "wb") as f:
                f.write(requests.get(url, headers={
                    'User-Agent': _default_ua
                }).content)
            return True
        except Exception:
            pass

    class TinyDownloadError(ValueError):
        """Raises when a download is too small."""

    def net_stream(self, targets, require=None, method='GET',
                   awesome_ua=False, add_padding=False,
                   custom_quoter=None, custom_headers=None):
        """
        Returns the raw payload string from the specified target(s).
        If multiple targets are specified, their resulting payloads are
        glued together.

        Each "target" is a bare URL string or a tuple containing an
        address and a dict for what to tack onto the query string.

        Finally, a require dict may be passed to enforce a Content-Type
        using key 'mime' and/or a minimum payload size using key 'size'.
        If using multiple targets, these requirements apply to each
        response.

        The underlying library here already understands how to search
        the environment for proxy settings (e.g. HTTP_PROXY), so we do
        not need to do anything extra for that.

        If add_padding is True, then some additional null padding will
        be added onto the stream returned. This is helpful for some web
        services that sometimes return MP3s that `mplayer` clips early.
        """
        DEFAULT_TIMEOUT = 3

        PADDING = '\0' * 2 ** 11

        assert method in ['GET', 'POST'], "method must be GET or POST"

        targets = targets if isinstance(targets, list) else [targets]
        targets = [
            (target, None) if isinstance(target, str)
            else (
                target[0],
                '&'.join(
                    '='.join([
                        key,
                        (
                            custom_quoter[key] if (custom_quoter and
                                                   key in custom_quoter)
                            else urllib2.quote
                        )(
                            val.encode('utf-8') if isinstance(val, str)
                            else str(val),
                            safe='',
                        ),
                    ])
                    for key, val in target[1].items()
                ),
            )
            for target in targets
        ]

        require = require or {}

        payloads = []

        for number, (url, params) in enumerate(targets, 1):
            desc = "web request" if len(targets) == 1 \
                else "web request (%d of %d)" % (number, len(targets))

            headers = {'User-Agent': _default_ua}
            if custom_headers:
                headers.update(custom_headers)

            response = urllib2.urlopen(
                urllib2.Request(
                    url=('?'.join([url, params]) if params and method == 'GET'
                         else url),
                    headers=headers,
                ),
                data=params if params and method == 'POST' else None,
                timeout=DEFAULT_TIMEOUT,
            )

            if not response:
                raise IOError("No response for %s" % desc)

            if response.getcode() != 200:
                value_error = ValueError(
                    "Got %d status for %s" %
                    (response.getcode(), desc)
                )
                try:
                    value_error.payload = response.read()
                    response.close()
                except Exception:
                    pass
                raise value_error

            if 'mime' in require and \
                    require['mime'] != format(response.info().
                                                      gettype()).replace('/x-', '/'):
                value_error = ValueError(
                    "Request got %s Content-Type for %s; wanted %s" %
                    (response.info().gettype(), desc, require['mime'])
                )
                value_error.got_mime = response.info().gettype()
                value_error.wanted_mime = require['mime']
                raise value_error

            payload = response.read()
            response.close()

            if 'size' in require and len(payload) < require['size']:
                raise self.TinyDownloadError(
                    "Request got %d-byte stream for %s; wanted %d+ bytes" %
                    (len(payload), desc, require['size'])
                )

            payloads.append(payload)

        if add_padding:
            payloads.append(PADDING)
        return b''.join(payloads)

    def net_download(self, path, *args, **kwargs):
        """
        Downloads a file to the given path from the specified target(s).
        See net_stream() for information about available options.
        """
        try:
            payload = self.net_stream(*args, **kwargs)
            with open(path, 'wb') as f:
                f.write(payload)
                f.close()
            return True
        except Exception:
            return False


class _DictBackendWorker(QThread):
    """Local Dictionary Builder"""

    def __init__(self, func):
        super(_DictBackendWorker, self).__init__()
        self._backend: Optional[object] = None
        self._func: ObjectBuilder = func

    def run(self):
        try:
            self._backend = self._func()
        except Exception:
            print(traceback.format_exc())
            self._backend = None

    @property
    def backend(self):
        return self._backend


class LocalService(Service):
    """
    Local Dictionary Service
    """

    def __init__(self, dict_path):
        super(LocalService, self).__init__()
        self.dict_path = dict_path
        # self.backend: Optional[object] = None
        self.missed_css = set()
        self.css_files = set()
        self.backend = None

    # MdxBuilder instances map
    _backends: defaultdict[str, object] = defaultdict(dict)
    _mutex_backends = QMutex()

    @staticmethod
    def _get_backend(key: str, builder: ObjectBuilder):
        LocalService._mutex_backends.lock()
        key = md5(str(key).encode('utf-8')).hexdigest()
        # print(f'_get_builder key {key} {func} builders[key] {LocalService._mdx_builders[key]}')
        if builder:
            if not LocalService._backends[key]:
                worker = _DictBackendWorker(builder)
                worker.start()
                while not worker.isFinished():
                    mw.app.processEvents()
                    worker.wait(100)
                LocalService._backends[key] = worker.backend
        LocalService._mutex_backends.unlock()
        return LocalService._backends[key]

    @property
    def support(self):
        return os.path.isfile(self.dict_path)

    @property
    def title(self):
        return getattr(self, '_register_label_', u'Unkown')

    @property
    def _filename(self):
        return os.path.splitext(os.path.basename(self.dict_path))[0]

    def active(self, fld_ord, word):
        self.missed_css.clear()
        return super(LocalService, self).active(fld_ord, word)

from typing import cast

class MdxService(LocalService):
    """
    MDX Local Dictionary Service
    """

    def __init__(self, dict_path):
        super(MdxService, self).__init__(dict_path)
        self._local = threading.local()
        self.media_cache = defaultdict(set)
        self.cache = defaultdict(str)
        self.html_cache = defaultdict(str)
        self.parse_html = True
        self.query_interval = 0.01
        self.styles = []
        self.media_prefix = f'_mdx-{self.unique.lower()}-'
        if MdxService.check(self.dict_path):
            self.backend: MdxBuilder = cast(MdxBuilder, self._get_backend(dict_path, object_builder(MdxBuilder, dict_path)))

    @staticmethod
    def check(dict_path):
        return os.path.isfile(dict_path) and dict_path.lower().endswith('.mdx')

    @property
    def support(self):
        return bool(self.backend and MdxService.check(self.dict_path))

    @property
    def title(self):
        if config.use_filename or not self.backend._title or self.backend._title.startswith('Title'):
            return self._filename
        else:
            return self.backend._title

    @export([u'默认', u'Default'])
    def fld_whole(self):
        html = self.get_default_html()
        return html
        # js = re.findall(r'<script .*?>(.*?)</script>', html, re.DOTALL)
        # js_files = re.findall(r'''<script .*?src=['"](.+?)['"]''', html, re.DOTALL)
        # return QueryResult(result=html, js=u'\n'.join(js), js_files=js_files)

    def _get_definition_mdx(self, word=None, depth = 0):
        """according to the word return mdx dictionary page"""
        if word is None:
            word = self.word
        ignorecase = config.ignore_mdx_wordcase and (word != word.lower() or word != word.upper())
        content = self.backend.mdx_lookup(word, ignorecase=ignorecase)
        
        if not content:
            # print(f'*** [{self.title}] No definition for "{word}"')
            return ""
        
        str_content = ""
        for c in content:
            # print(f"_get_definition_mdx {word}: {len(c) > 100 and c[:100] or c}")
            def replace_link(match):
                # limit redirect depth to 1
                # LDOCE6 word "license" and "licence" are linked to each other, causing dead loop
                MAX_LINK_REDIR_DEPTH = 1
                if depth >= MAX_LINK_REDIR_DEPTH:
                    print(f'*** Max link redirect depth {MAX_LINK_REDIR_DEPTH} exceeded for "{match}"')
                    # return f'No definition for "{match}"'
                    return ""
                target_word = match.group(1).strip()
                tdef = self._get_definition_mdx(target_word, depth + 1)
                return tdef

            c = re.sub(r'@@@LINK=([^\r\n]+)[\r\n]+', replace_link, c)
            str_content += c.replace("\r\n", "").replace("entry:/", "")

        return str_content

    def _get_definition_mdd(self, word):
        """according to the keyword(param word) return the media file contents"""
        word = word.replace('/', '\\')
        ignorecase = config.ignore_mdx_wordcase and (word != word.lower() or word != word.upper())
        content = self.backend.mdd_lookup(word, ignorecase=ignorecase)
        if len(content) > 0:
            return [content[0]]
        else:
            return []
        
    def get_stemmer(self):
        """Retrieves or creates a thread-unique stemmer."""
        if not hasattr(self._local, "stemmer"):
            self._local.stemmer = stemmer("english")
        return self._local.stemmer

    def get_html(self, word: str | None = None) -> str | BeautifulSoup:
        """get self.word's html page from MDX"""
        if word is None:
            word = self.word
        word_lower = word.lower()
        if not self.html_cache[word]:
            html = self._get_definition_mdx(word)
            if not html and word != word_lower:
                html = self._get_definition_mdx(word_lower)
            # if not html:
            #     word_base_form = self.get_stemmer().stemWord(word)
            #     if word != word_base_form:
            #         html = self._get_definition_mdx(word_base_form)
            if html:
                if self.parse_html:
                    self.html_cache[word] = BeautifulSoup(html, 'html.parser')
                else:
                    self.html_cache[word] = html

        return self.html_cache[word]

    def save_file(self, filepath_in_mdx, dest_path):
        """according to filepath_in_mdx to get media file and save it to savepath"""
        try:
            bytes_list = self._get_definition_mdd(filepath_in_mdx)
            if bytes_list:
                if not os.path.exists(dest_path):
                    with open(dest_path, 'wb') as f:
                        f.write(bytes_list[0])
                return dest_path
        except sqlite3.OperationalError as e:
            print(e)
            pass
        return ''

    def get_default_html(self):
        '''
        default get html from mdx interface
        '''
        if not self.cache[self.word]:
            html = self.get_html(self.word)
            if html:
                self.cache[self.word] = self.adapt_to_anki(html)
        return self.cache[self.word]
    
    @staticmethod
    def to_mdd_path(src_path):
        p = re.sub(r'/+', r'\\', src_path)
        p = re.sub(r'\\+', r'\\', p)

        return f'\\{p.lstrip("\\")}'

    def adapt_to_anki(self, html):
        """
        1. convert the media path to actual path in anki's collection media folder.
        2. remove the js codes (js inside will expires.)
        """
        html = deepcopy(html)
        # convert media path, save media files
        media_files_set = set()
        
        # mcss = re.findall(r'href=[\',"](\S+?\.css)[\',"]', html)
        css_files_tags = html.select('link[rel="stylesheet"][href]')
        mcss_files = set( tag['href'] for tag in css_files_tags )
        media_files_set.update(mcss_files)

        # mjs = re.findall(r'src="([\w\./]\S+?\.js)"', html)
        js_files_tags = html.select('script[src$=".js"]')
        mjs_files = set( tag['src'] for tag in js_files_tags )
        media_files_set.update(mjs_files)

        # msrc = re.findall(r'<img.*?src="([\w\./]\S+?)".*?>', html)
        img_tags = html.select('img')
        mimg = set( tag['src'] for tag in img_tags )
        media_files_set.update(mimg)
        # msound = re.findall(r'href="sound:(.*?\.(?:mp3|wav|aac))"', html)
        sound_tags = html.select('a[href^="sound:"]')
        msound = set( tag['href'].removeprefix('sound:/') for tag in sound_tags )

        print(f'mcss {mcss_files}')
        print(f'mjs {mjs_files}')
        print(f'mimg {mimg}')

        print(f'media_files_set {media_files_set}')
        print(f'msound {msound}')
        # TODO
        """
        for import css, add to `Note Type -> Cards -> Styling`
        https://forums.ankiweb.net/t/how-to-add-external-css-in-a-field/17838/9
        from:
            <link rel="stylesheet" href="v.css" type="text/css">
        to (in `Note Type -> Cards -> Template/Styling`):
            <style>@import url(style.css);
                   @import "style.css";</style>
        """
        css_style = ''
        if len(mcss_files) != 0:
            css_list = [f"@import url(_{css});" for css in mcss_files]
            css_style = "\n".join(css_list)
            css_style = f"<style> {css_style} </style>"
        if config.export_media:
            media_files_set.update(msound)
        # for each in media_files_set:
        #     html = html.replace(each, u'_' + each.split('/')[-1])
        print(f'TODO: parse css files')
        # if html != '' and css_style != '':
        #     html = css_style + html
        # find sounds
        # in css ".replay-button" can config play-button
        # p = re.compile(r'<a[^>]+?href=\"sound:_(.*?\.(?:mp3|wav|aac))\"[^>]*?>(.*?)</a>')
        # html = p.sub("[sound:mdx-" + self.title + "-" + u"\\1]\\2", html)

        # save media files
        path_map, errors = self.save_media_files(media_files_set)
        print(f'path_map {path_map}')
        print(f'errors {errors}')

        ### css and js are not allow in field html anymore
        for tag in css_files_tags:
            tag.decompose()
        for tag in js_files_tags:
            tag.decompose()
        for tag in img_tags:
            mdd_path = MdxService.to_mdd_path(tag['src'])
            tag['src'] = path_map[mdd_path]
        if config.export_media:
            for tag in sound_tags:
                mdd_path = MdxService.to_mdd_path(tag['href'].removeprefix('sound:/'))
                tag['href'] = f'sound:{path_map[mdd_path]}'

        wrap_class_names = set()
        for src_css_file in mcss_files:
            target_css_file = path_map[MdxService.to_mdd_path(src_css_file)]
            # if not exists the css file, the user can place the file to media
            # folder first, and it will also execute the wrap process to generate
            # the desired file.
            if not os.path.exists(target_css_file):
                self.missed_css.add(target_css_file)
            new_css_file, wrap_class_name = wrap_css(target_css_file)
            wrap_class_names.add(wrap_class_name)
            self.css_files.add(new_css_file)
            # html = html.replace(css_file, new_css_file)
            # add global div to the result html
            
        mcss = [ str(tag) for tag in html.select('style') ]
        mjs = [ str(tag) for tag in html.select('script:not([src])') ]
        html = f'''<div class="{' '.join(wrap_class_names)}">{str(html)}</div>'''

        return QueryResult(result=html, js_files = mjs_files, css_files = self.css_files)

    def save_default_file(self, src_path, savepath=None):
        '''
        default save file interface
        '''
        filename = src_path.replace('\\', os.path.sep)
        basename = os.path.basename(filename)
        if not savepath:
            savepath = get_canonical_name(self.media_prefix, filename)
        if os.path.exists(savepath):
            return savepath
        
        try:
            print('TODO: save_default_file basename or filename')

            src_fn = os.path.join(os.path.dirname(self.dict_path), basename)
            if os.path.exists(src_fn):
                shutil.copy(src_fn, savepath)
                return savepath

            ignorecase = config.ignore_mdx_wordcase and (
                            src_path != src_path.lower() or src_path != src_path.upper()
                        )
            blob = self.backend.mdd_lookup(src_path, ignorecase=ignorecase)
            if blob:
                with open(savepath, 'wb') as f:
                    f.write(blob[0])
            else:
                print(f'*** Error {src_path} not found in file system and mdd')
                
        except sqlite3.OperationalError as e:
            traceback.print_exc()
            print('save default file error', e)

        return savepath

    def save_media_files(self, data):
        """
        get the necessary static files from local mdx dictionary
        ** kwargs: data = list
        """
        new_files = data - self.media_cache['files']
        self.media_cache['files'].update(new_files)

        mdd_keys, errors = list(), list()
        path_map = {}
        wild = [ '*' + MdxService.to_mdd_path(f) for f in new_files ]
        try:
            for mdd_key in wild:
                keys = self.backend.get_mdd_keys(mdd_key)
                # print(f'keys {keys}')
                if not keys:
                    errors.append(mdd_key)
                    mdd_keys.append(mdd_key[1:])
                else:
                    mdd_keys.extend(keys)
            # lookup and save files
            for mdd_key in mdd_keys:
                savepath = self.save_default_file(mdd_key)
                path_map[mdd_key] = savepath

        except AttributeError:
            traceback.print_exc()
            pass

        return path_map, errors


class StardictService(LocalService):
    '''
    Stardict Local Dictionary Service
    '''

    def __init__(self, dict_path):
        super(StardictService, self).__init__(dict_path)
        self.query_interval = 0.05
        if StardictService.check(self.dict_path):
            dict_path = dict_path[:-4]
            self.backend: StardictBuilder = cast(StardictBuilder, self._get_backend(dict_path, 
                                                object_builder(StardictBuilder, dict_path, in_memory=False)))
            # if self.backend:
            #    self.backend.get_header()

    @staticmethod
    def check(dict_path):
        return os.path.isfile(dict_path) and dict_path.lower().endswith('.ifo')

    @property
    def support(self):
        return bool(self.backend and StardictService.check(self.dict_path))

    @property
    def title(self):
        if config.use_filename or not self.backend.ifo.bookname:
            return self._filename
        else:
            return self.backend.ifo.bookname

    @export([u'默认', u'Default'])
    def fld_whole(self):
        # self.backend.check_build()
        try:
            result = self.backend[self.word]
            result = result.strip().replace('\r\n', '<br />') \
                .replace('\r', '<br />').replace('\n', '<br />')
            return QueryResult(result=result)
        except KeyError:
            return QueryResult.default()


class QueryResult(MapDict):
    """Query Result structure"""

    def __init__(self, *args, **kwargs):
        self['result'] = ''
        self['js'] = []
        self['css'] = []
        super(QueryResult, self).__init__(*args, **kwargs)
        # avoid return None
        # if self['result'] is None:
        #     self['result'] = ""

    @classmethod
    def default(cls):
        return QueryResult(result="")
