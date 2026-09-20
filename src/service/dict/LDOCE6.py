#-*- coding:utf-8 -*-
import os
import re
import random
from copy import deepcopy
from bs4 import BeautifulSoup, Tag

from ..base import *


# VOICE_PATTERN = r'''<a\s+href=['"]sound://([\w/]+\w*\.mp3)['"]\s*>\s*<img\s+src=['"]img/spkr_%s.png['"]\s*/?>\s*</a\s*>'''
# VOICE_PATTERN_WQ = r'''<span\s+class=['"]%s['"]\s*>\s*<a\s+href=['"]sound://([\w/]+\w*\.mp3)['"]\s*/?>(.*?)</span\s+%s\s*>'''
# MAPPINGS = [
#     ['br', [re.compile(VOICE_PATTERN % r'r'), re.compile(VOICE_PATTERN_WQ % (r'brevoice', r'brevoice'))]],
#     ['us', [re.compile(VOICE_PATTERN % r'b'), re.compile(VOICE_PATTERN_WQ % (r'amevoice', r'amevoice'))]]
# ]
# LANG_TO_REGEXPS = {lang: regexps for lang, regexps in MAPPINGS}
FORCE_DICT_PATH = u'' # u'E:\\BaiduYunDownload\\mdx\\L6mp3.mdx'

from typing import cast

### Stuck in mw.app.processEvents() when use multiprocessing instead of QThread in query/worker.py
'''
$ uv pip install py-spy
Resolved 1 package in 421ms
Prepared 1 package in 404ms
Installed 1 package in 7ms
 + py-spy==0.4.2
(FastWordQuery-Anki26plus) 0  ~/Education/Anki/FastWordQuery-Anki26plus  (master)
$ py-spy dump --pid 152068
Process 152068: anki
Python v3.13.13 (/home/bob/Education/Anki/anki-26.08.1-linux-x86_64/anki)

Thread 152068 (idle): "MainThread"
    _get_backend (FastWordQuery-Anki26plus/service/base.py:667) calling mw.app.processEvents() and stuck
    __init__ (FastWordQuery-Anki26plus/service/base.py:717)
    get_service (FastWordQuery-Anki26plus/service/manager.py:57)
    get (FastWordQuery-Anki26plus/service/pool.py:43)
    __init__ (FastWordQuery-Anki26plus/service/dict/LDOCE6.py:73)
    get_service (FastWordQuery-Anki26plus/service/manager.py:57)
    get (FastWordQuery-Anki26plus/service/pool.py:43)
    query_flds (FastWordQuery-Anki26plus/query/common.py:310)
    _process_worker_loop (FastWordQuery-Anki26plus/query/worker.py:56)
    run (multiprocessing/process.py:108)
    _bootstrap (multiprocessing/process.py:313)
    _launch (multiprocessing/popen_fork.py:74)
    __init__ (multiprocessing/popen_fork.py:20)
    _Popen (multiprocessing/context.py:288)
    _Popen (multiprocessing/context.py:230)
    start (multiprocessing/process.py:121)
    start (FastWordQuery-Anki26plus/query/worker.py:107)
    query_all (FastWordQuery-Anki26plus/query/__init__.py:114)
    query_from_editor_fields (FastWordQuery-Anki26plus/query/__init__.py:90)
    query_from_browser (FastWordQuery-Anki26plus/query/__init__.py:55)
    <lambda> (FastWordQuery-Anki26plus/common.py:79)
    _run (__init__.py:789)
    run (__init__.py:582)
    main (app.py:8)
    <module> (__main__.py:21)
    _run_code (<frozen runpy>:88)
    _run_module_as_main (<frozen runpy>:199)
'''

@register([u'本地词典-朗文6', u'MDX-LDOCE6'], enabled = True)
class Ldoce6(MdxService):

    def __init__(self):
        dict_path = FORCE_DICT_PATH
        # if FORCE_DICT_PATH is a path, stop auto detect
        if not dict_path:
            from ...service import service_manager, service_pool
            for clazz in service_manager.mdx_services:
                service: MdxService = cast(MdxService, service_pool.get(clazz._unique_))
                title = service.backend._title if service and service.support else u''
                service_pool.put(service)
                # print(f'Dict Service: {title} -- {service.dict_path}')
                if title.startswith(u'LDOCE6') or u'LDOCE6' in os.path.basename(service.dict_path):
                    print(f"--- MDX-LDOCE6 Found dict_path: {service.dict_path}")
                    dict_path = service.dict_path
                    break
        super(Ldoce6, self).__init__(dict_path)

    @property
    def title(self):
        return getattr(self, '_register_label_', self.unique)

    @export('PHON')
    def fld_phonetic(self):
        html = self.get_html()
        # m = re.search(r'<span class="pron">(.*?)</span>', html)
        tag = html.select_one('.entry .pron')
        # print(f'fld_phonetic html {type(html)} tag {tag}')
        # print(f'fld_phonetic {tag}')
        if tag:
            return str(tag)
        return ''

    def _fld_voice(self, html, spkr_src):
        """获取发音字段"""
        tag = html.select_one(f"a[href^='sound:']:has(img[src='img/{spkr_src}'])")
        # print(f'_fld_voice region {spkr_src} tag {tag}')
        if not tag:
            return ''

        return str(self._save_audio(tag))

    region_to_audio_img = {
        "uk": "spkr_r.png",
        "us": "spkr_b.png"
    }

    @export('BRE_PRON')
    def fld_voicebre(self):
        return self._fld_voice(self.get_html(), Ldoce6.region_to_audio_img['uk'])

    @export('AME_PRON')
    def fld_voiceame(self):
        return self._fld_voice(self.get_html(), Ldoce6.region_to_audio_img['us'])

    @export('IMAGE')
    def fld_image(self):
        html = self.get_html()
        # m = re.search(r'<span class="imgholder"><img src="(.*?)".*?></span>', html)
        tags = html.select(f'.imgholder img')
        if not tags:
            return ''

        html_imgs = ''.join([str(self._save_image(tag)) for tag in tags])
        return html_imgs

    @export('EXAMPLE')
    def fld_sentence(self):
        return self._range_sentence_audio('all', with_audio=False)


    @export([u'例句加音频', u'Examples with audios'])
    def fld_sentence_audio(self):
        return self._range_sentence_audio('all')
    
    def _fld_definition(self, sel):
        html = self.get_html()
        # m = m = re.findall(r'<span class="def"\s*.*>\s*.*<\/span>', self.get_html())
        tags = html.select(sel)
        if not tags:
            return ''
        html_defs = u''.join([ str(tag) for tag in tags])
        return self._css(html_defs)

    @export('DEF')
    def fld_definition(self):
        return self._fld_definition('.def')

    @export('DEF_CN')
    def fld_definition_cn(self):
        return self._fld_definition('.defcn')

    @export([u'随机例句', u'Random example'])
    def fld_random_sentence(self):
        return self._range_sentence_audio('rand', with_audio=False)

    @export([u'首2个例句', u'First 2 examples'])
    def fld_first2_sentence(self):
        return self._range_sentence_audio([0, 1], with_audio=False)
    
    @export([u'随机例句加音频', u'Random example with audio'])
    def fld_random_sentence_audio(self):
        return self._range_sentence_audio('rand')

    @export([u'首2个例句加音频', u'First 2 examples with audios'])
    def fld_first2_sentence_audio(self):
        return self._range_sentence_audio([0, 1])

    def _range_sentence_audio(self, range_arr: list | str | range = 'all', with_audio=True):
        # m = re.findall(r'<span class="example"\s*.*>\s*.*<\/span>', self.get_html())
        html: BeautifulSoup = self.get_html()

        if with_audio:
            tags = html.select(f'.entry .sense .example:has(a[href^="sound:"]), .entry .tail .collocate .example:has(a[href^="sound:"])')
        else:
            tags = html.select(f'.entry .sense .example, .entry .tail .collocate .example')
        # print(f"_range_sentence_audio {len(tags)}")
        if not tags:
            return ''

        if range_arr == 'rand':
            range_arr = [random.randrange(0, len(tags), 1)]
        elif range_arr == 'all':
            range_arr = range(0, len(tags))

        examples = []
        for i in range_arr:
            if i < 0 or i >= len(tags):
                print(f'*** Error: _range_sentence_audio: {i} is out of range [0, {len(tags)})')
                continue
            # deepcopy before modify, so self.get_html() always return the same one
            example = deepcopy(tags[i])

            if with_audio:
                tag = example.select_one(f'a[href^="sound:"]')
                mp3 = self._save_audio(tag, do_html_deepcopy=False, anki_label=False)
                
            for img in example.select(f'img'):
                self._save_image(img, do_html_deepcopy=False)

            examples.append(str(example))
        return self._css('\n'.join(examples))



    # @export([u'额外例句', u'Extra Examples'])
    # def fld_extra_examples(self):
    #     lst = re.findall(r'href="/(@examples_.*?)\">.*?<', )
    #     html = self.get_html()
    #     tags = html.select(f'')
    #     if lst:
    #         str_content = u''
    #         for m in lst:
    #             content = self.backend.mdx_lookup(m)
    #             if len(content) > 0:
    #                 for c in content:
    #                     str_content += c.replace("\r\n","").replace("entry:/","")
    #         return self._css(str_content)
    #     return ''    

    @with_styles(css_file={ 'light': '_ldoce6.css', 'dark': '_ldoce6_dark.css' })
    def _css(self, val):
        return val
    