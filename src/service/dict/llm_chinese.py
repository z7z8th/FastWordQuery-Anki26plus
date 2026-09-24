from collections import defaultdict
import json
import requests
import markdown

from ..base import WebService, export, register
from ... import context

OLLAMA_HOST="localhost"
OLLAMA_MODEL="qwen3.8:27b"

print(f"TODO: use config.ollama_host config.ollama_model")

@register([u'LLM中文解释', u'LLM Chinese'], enabled=True)
class LLM_Chinese(WebService):
    def __init__(self):
        super().__init__()

    def _get_from_api(self):
        with context.get_worker_lock('llm'):
            ret = self.query_ollama_word(self.word)
            return ret

    def query_ollama_word(self, word, model=OLLAMA_MODEL, timeout=180) -> dict:
        """
        使用 requests 向 Ollama 查询汉语词语解释和例句（自动 Keep-Alive）
        
        :param word: 要查询的词语
        :param model: 使用的 Ollama 模型名称
        :param timeout: 超时时间（秒）
        """
        url = f"http://{OLLAMA_HOST}:11434/api/generate"

        field_separator = '~~~~~~'
        prompt = (
            f"请详细解释汉语词语 '{word}' 的含义、用法和背景。\n"
            f"然后请给出 3 到 5 个使用了该词语的例句。\n"
            f"注意：在详细解释和例句之间，请务必用 '{field_separator}' 作为单独的一行进行分隔。"
        )
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_ctx": int(32768/2),
                "num_predict": int(24576/2),
                "think": "medium"
            }
        }
        
        print(f"正在查询词语 [{word}]，请稍候...\n")
        
        # 使用 Session 会话对象，自动管理 HTTP Keep-Alive 连接池
        session = requests.Session()
        raw_response = []
        try:
            # stream=True 开启流式响应；json=payload 自动序列化并设置 Content-Type Header
            response = session.post(url, json=payload, stream=True, timeout=timeout)
            response.raise_for_status()  # 检查 HTTP 状态码（如 404, 500 等）
            
            # 按行读取流式返回的数据
            for line in response.iter_lines():
                if line:
                    # 解析单行 JSON
                    body = json.loads(line.decode('utf-8'))
                    response_text = body.get("response", "")
                    raw_response.append(response_text)
                    # 实时输出到控制台
                    print(response_text, end="", flush=True)
                    
                    if body.get("done", False):
                        break
                        
            print("\n\n[查询完成]")
            explains, examples = ''.join(raw_response).split(field_separator)
            explains, examples = [ 
                markdown.markdown(x, extensions=["tables", "fenced_code"])
                if ('#' in x or '*' in x) else x
                for x in [explains, examples] 
            ]

            return {
                'explains': explains,
                'examples': examples,
            }

        except requests.exceptions.Timeout:
            print(f"\n[错误] 请求超时！Ollama 在 {timeout} 秒内未回应。")
        except requests.exceptions.ConnectionError:
            print("\n[网络/连接错误] 无法连接到 Ollama 服务，请确认服务已启动 (http://localhost:11434)。")
        except requests.exceptions.HTTPError as e:
            print(f"\n[HTTP 错误] 服务返回状态码错误: {e}")
        except Exception as e:
            print(f"\n[未知错误] {e}")
        finally:
            session.close()

        return defaultdict(str)

    @export([u'例句', 'Examples'])
    def fld_explains(self):
        return self._get_field('examples')
    
    @export([u'详细解释', 'Explains'])
    def fld_explain(self):
        return self._get_field('explains')
    