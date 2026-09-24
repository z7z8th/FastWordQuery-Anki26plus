import requests
import json
from ..context import config

def get_ollama_models(host="http://localhost:11434"):
    try:
        response = requests.get(f"{host}/api/tags")
        response.raise_for_status()
        
        data = response.json()
        models = data.get("models", [])
        
        print("Available models:")
        for model in models:
            name = model.get("name")
            size_gb = model.get("size", 0) / (1024 ** 3)
            print(f"- {name} ({size_gb:.2f} GB)")
            
        return models
    except Exception as e:
        print(f"Failed to fetch models: {e}")

def query_ollama(prompt, host=config.ollama_host, model=config.ollama_model, timeout=180) -> str:
    """
    使用 requests 向 Ollama 查询汉语词语解释和例句（自动 Keep-Alive）
    
    :param word: 要查询的词语
    :param model: 使用的 Ollama 模型名称
    :param timeout: 超时时间（秒）
    """
    url = f"http://{host}:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "keep_alive": "24h",
        "think": True,
        "stream": True,
        "options": {
            "num_ctx": int(32768/4),
            "num_predict": int(24576/4),
            "think": "medium"
        }
    }
    
    # 使用 Session 会话对象，自动管理 HTTP Keep-Alive 连接池
    session = requests.Session()
    raw_response_list = []
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
                raw_response_list.append(response_text)
                # 实时输出到控制台
                print(response_text, end="", flush=True)
                
                if body.get("done", False):
                    break

        raw_response = ''.join(raw_response_list)
        return raw_response
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

    return ''


if __name__ == "__main__":
    get_ollama_models()