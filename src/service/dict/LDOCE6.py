#-*- coding:utf-8 -*-
import os
import re
import random
from ..base import *


VOICE_PATTERN = r'''<a\s+href=['"]sound://([\w/]+\w*\.mp3)['"]\s*>\s*<img\s+src=['"]img/spkr_%s.png['"]\s*/?>\s*</a\s*>'''
VOICE_PATTERN_WQ = r'''<span\s+class=['"]%s['"]\s*>\s*<a\s+href=['"]sound://([\w/]+\w*\.mp3)['"]\s*/?>(.*?)</span\s+%s\s*>'''
MAPPINGS = [
    ['br', [re.compile(VOICE_PATTERN % r'r'), re.compile(VOICE_PATTERN_WQ % (r'brevoice', r'brevoice'))]],
    ['us', [re.compile(VOICE_PATTERN % r'b'), re.compile(VOICE_PATTERN_WQ % (r'amevoice', r'amevoice'))]]
]
LANG_TO_REGEXPS = {lang: regexps for lang, regexps in MAPPINGS}
DICT_PATH = u'' # u'E:\\BaiduYunDownload\\mdx\\L6mp3.mdx'


@register([u'本地词典-LDOCE6', u'MDX-LDOCE6'], enabled = True)
class Ldoce6(MdxService):

    def __init__(self):
        dict_path = DICT_PATH
        # if DICT_PATH is a path, stop auto detect
        if not dict_path:
            from ...service import service_manager, service_pool
            for clazz in service_manager.mdx_services:
                service = service_pool.get(clazz.__unique__)
                title = service.builder._title if service and service.support else u''
                service_pool.put(service)
                print(f'Dict Service: {title} -- {service.dict_path}')
                if title.startswith(u'LDOCE6') or u'LDOCE6' in os.path.basename(service.dict_path):
                    print(f"*** MDX-LDOCE6 Found dict_path: {service.dict_path}")
                    dict_path = service.dict_path
                    break
        super(Ldoce6, self).__init__(dict_path)

    @property
    def title(self):
        return getattr(self, '__register_label__', self.unique)

    @export('PHON')
    def fld_phonetic(self):
        html = self.get_html()
        m = re.search(r'<span class="pron">(.*?)</span>', html)
        if m:
            return m.groups()[0]
        return ''

    def _fld_voice(self, html, voice):
        """获取发音字段"""
        for regexp in LANG_TO_REGEXPS[voice]:
            match = regexp.search(html)
            # print(f'_fld_voice regexp {regexp}')
            if match:
                # print(f'_fld_voice match {match}')
                val = '/' + match.group(1)
                ## uniq name by uuid
                # name = get_hex_name('mdx-'+self.unique.lower(), val, 'mp3')
                dest_name = get_canonical_name(f'_mdx-{self.unique.lower()}-', val)
                dest_name = self.save_file(val, dest_name)
                if dest_name:
                    return self.get_anki_label(dest_name, 'audio')
        return ''

    @export('BRE_PRON')
    def fld_voicebre(self):
        return self._fld_voice(self.get_html(), 'br')

    @export('AME_PRON')
    def fld_voiceame(self):
        return self._fld_voice(self.get_html(), 'us')

    def _fld_image(self, img):
        val = '/' + img
        # file extension isn't always jpg
        file_extension = os.path.splitext(img)[1][1:].strip().lower()
        dest_name = get_canonical_name(f'_mdx-{self.unique.lower()}-', val)
        dest_name = self.save_file(val, dest_name)
        if dest_name:
            return self.get_anki_label(dest_name, 'img')
        return ''

    @export('IMAGE')
    def fld_image(self):
        html = self.get_html()
        m = re.search(r'<span class="imgholder"><img src="(.*?)".*?></span>', html)
        if m:
            return self._fld_image(m.groups()[0])
        return ''

    @export('EXAMPLE')
    def fld_sentence(self):
        return self._range_sentence([i for i in range(0, 100)])

    def _fld_audio(self, audio):
        dest_name = get_canonical_name(f'_mdx-{self.unique.lower()}', audio)
        dest_name = self.save_file(audio, dest_name)
        if dest_name:
            return self.get_anki_label(dest_name, 'audio')
        return ''

    @export([u'例句加音频', u'Examples with audios'])
    def fld_sentence_audio(self):
        return self._range_sentence_audio([i for i in range(0, 100)])

    @export('DEF')
    def fld_definate(self):
        m = m = re.findall(r'<span class="def"\s*.*>\s*.*<\/span>', self.get_html())
        if m:
            soup = parse_html(m[0])
            el_list = soup.findAll('span', {'class':'def'})
            if el_list:
                maps = [u''.join(str(content) for content in element.contents) 
                                    for element in el_list]
            my_str = ''
            for i_str in maps:
                my_str = my_str + '<li>' + i_str + '</li>'
            return self._css(my_str)
        return ''

    @export([u'随机例句', u'Random example'])
    def fld_random_sentence(self):
        return self._range_sentence()

    @export([u'首2个例句', u'First 2 examples'])
    def fld_first2_sentence(self):
        return self._range_sentence([0, 1])
    
    @export([u'随机例句加音频', u'Random example with audio'])
    def fld_random_sentence_audio(self):
        return self._range_sentence_audio()

    @export([u'首2个例句加音频', u'First 2 examples with audios'])
    def fld_first2_sentence_audio(self):
        return self._range_sentence_audio([0, 1])

    def _range_sentence(self, range_arr=None):
        m = re.findall(r'<span class="example"\s*.*>\s*.*<\/span>', self.get_html())
        if m:
            soup = parse_html(m[0])
            el_list = soup.findAll('span', {'class':'example'})
            if el_list:
                maps = [u''.join(str(content) for content in element.contents) 
                                    for element in el_list]
            my_str = ''
            range_arr = range_arr if range_arr else [random.randrange(0, len(maps) - 1, 1)]
            for i, i_str in enumerate(maps):
                if i in range_arr:
                    i_str = re.sub(r'<a[^>]+?href=\"sound\:.*\.mp3\".*</a>', '', i_str).strip()
                    my_str = my_str + '<li>' + i_str + '</li>'
            return self._css(my_str)
        return ''

    def _range_sentence_audio(self, range_arr=None):
        m = re.findall(r'<span class="example"\s*.*>\s*.*<\/span>', self.get_html())
        if m:
            soup = parse_html(m[0])
            el_list = soup.findAll('span', {'class':'example'})
            if el_list:
                maps = []
                for element in el_list:
                    i_str = ''
                    for content in element.contents:
                        i_str = i_str + str(content)
                    sound = re.search(r'<a[^>]+?href=\"sound\:\/(.*?\.mp3)\".*</a>', i_str)
                    if sound:
                        maps.append([sound, i_str])
            my_str = ''
            range_arr = range_arr if range_arr else [random.randrange(0, len(maps) - 1, 1)]
            for i, e in enumerate(maps):
                if i in range_arr:
                    i_str = e[1]
                    sound = e[0]
                    mp3 = self._fld_audio(sound.groups()[0])
                    i_str = re.sub(r'<a[^>]+?href=\"sound\:.*\.mp3\".*</a>', '', i_str).strip()
                    my_str = my_str + '<li>' + i_str + ' ' + mp3 + '</li>'
            return self._css(my_str)
        return ''

    @export([u'额外例句', u'Extra Examples'])
    def fld_extra_examples(self):
        lst = re.findall(r'href="/(@examples_.*?)\">.*?<', self.get_html())
        if lst:
            str_content = u''
            for m in lst:
                content = self.builder.mdx_lookup(m)
                if len(content) > 0:
                    for c in content:
                        str_content += c.replace("\r\n","").replace("entry:/","")
            return self._css(str_content)
        return ''    

    @with_styles(cssfile='_ldoce6.css')
    def _css(self, val):
        return val
    