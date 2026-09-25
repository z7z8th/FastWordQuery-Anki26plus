from collections import defaultdict
import json
import requests
import markdown

from ..base import WebService, export, register
from ... import context
from ...context import config
from ...utils.llm import *


@register([u'LLM中文解释', u'LLM Chinese'], enabled=True)
class LLM_Chinese(WebService):
    def __init__(self):
        super().__init__()

    def _get_from_api(self):
        with context.get_worker_lock('llm'):
            ret = self._query_ollama_word(self.word)
            return ret
        
    def _query_ollama_word(self, word) -> dict:
        """
        使用 requests 向 Ollama 查询汉语词语解释和例句（自动 Keep-Alive）
        """

        field_separator = '~~~~~~'
        prompt = (
            f"请详细解释汉语词语 '{word}' 的含义、用法和背景。\n"
            f"然后请给出 3 到 5 个使用了该词语的例句。\n"
            f"注意：在详细解释和例句之间，请务必用 '{field_separator}' 作为单独的一行进行分隔。"
        )
        
        print(f"正在查询词语 [{word}]，请稍候...\n")

        raw_response = query_ollama(prompt, think=False)
        print("\n\n[查询完成]")
        if not raw_response:
            return defaultdict(str)

        explains, examples = raw_response.split(field_separator)
        explains, examples = [ 
            markdown.markdown(x, extensions=["tables", "fenced_code"])
            if ('#' in x or '*' in x) else x
            for x in [explains, examples] 
        ]

        return {
            'explains': explains,
            'examples': examples,
        }

    @export([u'例句', 'Examples'])
    def fld_explains(self):
        return self._get_field('examples')
    
    @export([u'详细解释', 'Explains'])
    def fld_explain(self):
        return self._get_field('explains')

    @export (['LLM模型名', 'LLM Model Name'])
    def fld_model_name(self):
        # print(f'TODO: model name')
        return config.ollama_model
    