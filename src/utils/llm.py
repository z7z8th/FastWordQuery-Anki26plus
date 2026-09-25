import json
import re
import traceback
import requests
from ..context import config


def _norm_ollam_host(host):
    if not host.startswith("http"):
        host = f"http://{host}"

    return host


def get_ollama_models(host=config.ollama_host):
    try:
        host = _norm_ollam_host(host)
        response = requests.get(f"{host}/api/tags")
        response.raise_for_status()

        data = response.json()
        models = data.get("models", [])

        print("Available models:")
        for model in models:
            name = model.get("name")
            size_gb = model.get("size", 0) / (1024**3)
            print(f"- {name} ({size_gb:.2f} GB)")

        return models
    except Exception as e:
        traceback.print_exc()
        print(f"Failed to fetch models: {e}")

    return [{"name": "Error fetching ollama models..."}]

# NOTE: gemini recommends: think should be false for translation/explain related work
def query_ollama(
    prompt, host=config.ollama_host, model=config.ollama_model, think=False, timeout=180
) -> str:
    """Queries Ollama using requests and prints performance metrics and generation speed."""
    host = _norm_ollam_host(host)
    url = f"{host}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "keep_alive": "24h",
        "think": think,
        "stream": True,
        "options": {
            "num_ctx": int(32768 / 4),
            "num_predict": int(24576 / 4),
            # "think": "medium",
        },
    }

    session = requests.Session()
    raw_response_list = []
    stats = {}  # Dictionary to store performance statistics

    try:
        response = session.post(url, json=payload, stream=True, timeout=timeout)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                body = json.loads(line.decode("utf-8"))
                response_text = body.get("response", "")
                raw_response_list.append(response_text)

                # Real-time streaming output
                print(response_text, end="", flush=True)

                # Extract performance metrics when generation is finished (units are in nanoseconds)
                if body.get("done", False):
                    stats = {
                        "total_duration": body.get("total_duration", 0),
                        "load_duration": body.get("load_duration", 0),
                        "prompt_eval_count": body.get("prompt_eval_count", 0),
                        "prompt_eval_duration": body.get("prompt_eval_duration", 0),
                        "eval_count": body.get("eval_count", 0),
                        "eval_duration": body.get("eval_duration", 0),
                    }
                    break

        print("\n")  # Newline separator between output and performance stats

        # Print performance statistics
        if stats:
            total_sec = stats["total_duration"] / 1e9
            eval_count = stats["eval_count"]
            eval_dur_sec = stats["eval_duration"] / 1e9

            prompt_count = stats["prompt_eval_count"]
            prompt_dur_sec = stats["prompt_eval_duration"] / 1e9

            # Calculate token generation speed (tokens/s)
            gen_speed = (eval_count / eval_dur_sec) if eval_dur_sec > 0 else 0
            prompt_speed = (
                (prompt_count / prompt_dur_sec) if prompt_dur_sec > 0 else 0
            )

            print("=" * 40)
            print("📊 Performance Statistics")
            print(f"- Total Duration       : {total_sec:.2f} s")
            print(
                f"- Generation Speed     : {gen_speed:.2f} tokens/s ({eval_count} tokens)"
            )
            print(
                f"- Prompt Eval Speed    : {prompt_speed:.2f} tokens/s ({prompt_count} tokens)"
            )
            print("=" * 40 + "\n")

        raw_response = "".join(raw_response_list)
        clean_text = re.sub(
            r"<think>.*?</think>", "", raw_response, flags=re.DOTALL
        )
        return clean_text

    except requests.exceptions.Timeout:
        print(f"\n[Error] Request timed out! Ollama did not respond within {timeout} seconds.")
    except requests.exceptions.ConnectionError:
        print(
            "\n[Network/Connection Error] Failed to connect to Ollama service. Please make sure the service is running (http://localhost:11434)."
        )
    except requests.exceptions.HTTPError as e:
        print(f"\n[HTTP Error] Service returned an error status code: {e}")
        if e.response is not None and e.response.status_code == 404:
            print(f'Possible reason is model `{model}` Not Found')
            get_ollama_models(host)
    except Exception as e:
        print(f"\n[Unknown Error] {e}")
    finally:
        session.close()

    return ""


if __name__ == "__main__":
    get_ollama_models()
    query_ollama("山药蛋")
    query_ollama("皂角")