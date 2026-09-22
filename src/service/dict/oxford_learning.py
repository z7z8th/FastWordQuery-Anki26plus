# coding=utf-8
from functools import cached_property
from bs4 import Tag
from ..base import *
from ...utils.misc import format_multi_query_word


@register([u'牛津学习词典', u'Oxford Learner'])
@auto_bind_exports
class OxfordLearning(WebService):

    @with_styles(css_file='_oxford.css')
    def _fld_ee(self):
        return self._get_field('ee')
    
    # Field Registry: (field_method_name, export_labels, getter_fn)
    _EXPORTS = [
        ('fld_phonetic', 'PHON', lambda self: self._get_field('phonetic')),
        ('fld_phonetic_us', 'AME_PHON', lambda self: self._get_field('phon_ame')),
        ('fld_phonetic_uk', 'BRE_PHON', lambda self: self._get_field('phon_bre')),
        ('fld_pos', [u'词性', u'POS'], lambda self: self._get_field('pos')),
        ('fld_ee', 'DEF', lambda self: self._fld_ee()),
        ('fld_image_full', 'IMAGE', lambda self: self.get_image_full()),
        ('fld_image_thumb', [u'缩略图', u'Thumbnails'], lambda self: self.get_image_thumb()),
        ('fld_sound_bre', 'BRE_PRON', lambda self: self.get_sound_bre()),
        ('fld_sound_ame', 'AME_PRON', lambda self: self.get_sound_ame()),
        ('fld_sound_pri', [u'英式发音优先', u'British Pronunciation First'],
         lambda self: self.get_sound_bre() or self.get_sound_ame()),
        ('fld_examples', 'EXAMPLE', lambda self: self._get_field('examples')),
        ('fld_word_origin', 'WORD_ORIGIN', lambda self: self._get_field('word_origin')),
        ('fld_idiom', ['俚语', 'Idioms'], lambda self: self._get_field('idioms')),
    ]

    def __init__(self):
        super().__init__()

    def query(self, word: str):
        """Query Oxford Learner's Dictionary for target word."""
        qry_url = f'https://www.oxfordlearnersdictionaries.com/definition/english/{format_multi_query_word(word)}'

        for _ in range(10):
            try:
                rsp = self.get_response(qry_url, timeout=15)
                if rsp:
                    return OxfordLearningDictWord(rsp)
                break
            except Exception:
                continue
        return None

    def _get_from_api(self):
        ret = self.query(self.quote_word)
        if not ret:
            return None

        return self.cache_this(
            {
                'phonetic': f'{ret.phon_bre} {ret.phon_ame}'.strip(),
                'phon_bre': ret.phon_bre,
                'phon_ame': ret.phon_ame,
                'pos': ret.pos,
                'img_full': ret.image_full_url,
                'img_thumb': ret.image_thumb_url,
                'ee': ''.join(ret.definitions_html),
                's_bre': ret.sound_url_bre,
                's_ame': ret.sound_url_nam,
                'examples': ret.examples,
                'word_origin': ret.word_origin,
                'idioms': ret.idioms,
            }
        )

    # --- Media Handlers ---

    def _download_asset(self, field_key: str, ext: str, label_type: str) -> str:
        url = self._get_field(field_key)
        if not url:
            return ''
        filename = get_hex_name(self.unique.lower(), url, ext)
        return self.get_anki_label(filename, label_type) if self.download(url, filename) else ''

    def get_image_full(self):
        return self._download_asset('img_full', 'jpg', 'img')

    def get_image_thumb(self):
        return self._download_asset('img_thumb', 'jpg', 'img')

    def get_sound_bre(self):
        return self._download_asset('s_bre', 'mp3', 'audio')

    def get_sound_ame(self):
        return self._download_asset('s_ame', 'mp3', 'audio')
    

class OxfordLearningDictWord:

    def __init__(self, markups):
        if not markups:
            return
        self.page = parse_html(markups)
        self._defs = []
        self._defs_html = []

    # --- Navigation & Extraction Helpers ---

    def _get_text(self, selector: str, scope=None) -> str:
        target = (scope or self.page).select_one(selector)
        return target.get_text(strip=True) if target else ''

    def _get_attr(self, selector: str, attr: str, scope=None) -> str:
        target = (scope or self.page).select_one(selector)
        return target.get(attr, '') if target else ''

    def _get_phonetic(self, selector: str, remove_label: str) -> str:
        scope = self.page.select_one(selector)
        if not scope:
            return ''
        phon = self._get_text('span.phon', scope=scope).replace('/', '').replace(remove_label, '').strip()
        return f'/{phon}/' if phon else ''

    # --- Cached Properties ---

    @cached_property
    def phon_bre(self) -> str:
        return self._get_phonetic('.phonetics .phons_br', 'BrE')

    @cached_property
    def phon_ame(self) -> str:
        return self._get_phonetic('.phonetics .phons_n_am', 'NAmE')

    @cached_property
    def pos(self) -> str:
        return self._get_text('div.webtop span.pos')

    @cached_property
    def image_full_url(self) -> str:
        return self._get_attr('a.topic', 'href')

    @cached_property
    def image_thumb_url(self) -> str:
        return self._get_attr('a.topic img.thumb', 'src')

    @cached_property
    def sound_url_bre(self) -> str:
        return self._get_attr('.phons_br div.sound.audio_play_button.pron-uk', 'data-src-mp3')

    @cached_property
    def sound_url_nam(self) -> str:
        return self._get_attr('.phons_n_am div.sound.audio_play_button.pron-us', 'data-src-mp3')

    # --- Definitions ---

    def get_definitions(self):
        tag_exp = self.page.select_one('.def')
        if tag_exp and not self._defs:
            cleaned = self._clean(tag_exp)
            lis = cleaned.find_all('li')

            if not lis:
                self._defs_html = [str(cleaned.prettify())]
                self._defs = [cleaned.get_text(strip=True)]
            else:
                self._defs_html = [str(li.prettify()) for li in lis]
                self._defs = [li.get_text(strip=True) for li in lis]

        return self._defs, self._defs_html

    @property
    def definitions(self):
        return self.get_definitions()[0]

    @property
    def definitions_html(self):
        return self.get_definitions()[1]

    # --- HTML Sanitization ---

    def _clean(self, tg: Tag) -> Tag:
        if not tg or not isinstance(tg, Tag):
            return tg

        decompose_classes = ['.xr-gs', '.sound', '.heading', '.topic', '.collapse', '.oxford3000']
        for cls in decompose_classes:
            for elem in tg.select(cls):
                elem.decompose()

        rmv_attrs = {'dpsid', 'id', 'psg', 'reg'}
        for child in tg.find_all(True):
            if child.attrs:
                child.attrs = {k: v for k, v in child.attrs.items() if k not in rmv_attrs}

        return tg

    # --- Supplementary Sections ---

    @cached_property
    def examples(self):
        return str(self.page.select_one('.entry .sense > .examples'))

    @cached_property
    def word_origin(self):
        return str(self.page.select_one('.entry [unbox="wordorigin"]'))

    @cached_property
    def idioms(self):
        return str(self.page.select_one('.entry .idioms'))