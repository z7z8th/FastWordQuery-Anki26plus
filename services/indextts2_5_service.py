import re
import io
import traceback
import unicodedata

from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import torch
import torchaudio

import os
import hashlib
import shutil
from collections import OrderedDict
from typing import Optional


class TTSLRUCache:

    def __init__(self, capacity: int = 1000, cache_dir: str = "/tmp/index-tts-cache/"):
        self.capacity = capacity
        self.cache_dir = cache_dir
        self.cache = OrderedDict()

        # Ensure the cache directory exists
        os.makedirs(self.cache_dir, exist_ok = True)

        # Scan directory on initialization to populate the cache
        self._scan_cache()

    def _get_sha1(self, text: str) -> str:
        """Computes the SHA1 hash of the input text to use as a unique key."""
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def _scan_cache(self):
        """Scans the cache directory on startup, sorting files by modification time 
        to accurately reconstruct the LRU order."""
        files_info = []

        if not os.path.exists(self.cache_dir):
            return

        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".wav"):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    key = os.path.splitext(filename)[0]
                    try:
                        mtime = os.path.getmtime(filepath)
                        files_info.append((mtime, key, filepath))
                    except OSError:
                        continue

        # Sort by modification time (oldest first, newest last)
        files_info.sort(key = lambda x: x[0])

        # Populate the OrderedDict, evicting excess files if capacity is exceeded
        for _, key, filepath in files_info:
            if len(self.cache) >= self.capacity:
                oldest_key, oldest_path = self.cache.popitem(last = False)
                if os.path.exists(oldest_path):
                    try:
                        os.remove(oldest_path)
                    except OSError:
                        pass
            self.cache[key] = filepath

    def get_key(self, text: str) -> str:
        return self._get_sha1(text)

    def get(self, text: str) -> Optional[str]:
        """Retrieves the audio file path if it exists, updating its recency."""
        key = self._get_sha1(text)

        if key not in self.cache:
            return None

        audio_path = self.cache[key]

        # Verify the file still actually exists on disk
        if not os.path.exists(audio_path):
            del self.cache[key]
            return None

        # Mark as recently used by moving it to the end
        self.cache.move_to_end(key)
        return audio_path

    def put(self, text: str, source_audio_path: str) -> str:
        """Stores or updates an audio entry, evicting the least recently used item if full."""
        key = self._get_sha1(text)
        dest_path = os.path.join(self.cache_dir, f"{key}.wav")

        # Copy the generated audio file into the cache directory if it isn't already there
        if os.path.abspath(source_audio_path) != os.path.abspath(dest_path):
            shutil.copy(source_audio_path, dest_path)

        # If key already exists, update its position and path
        if key in self.cache:
            self.cache.move_to_end(key)
            self.cache[key] = dest_path
            return dest_path

        # If cache is at full capacity, evict the least recently used item (the first item)
        if len(self.cache) >= self.capacity:
            oldest_key, oldest_path = self.cache.popitem(last = False)
            if os.path.exists(oldest_path):
                try:
                    os.remove(oldest_path)
                except OSError:
                    pass

        # Add new entry
        self.cache[key] = dest_path
        return dest_path


tts_cache = TTSLRUCache(capacity=5000, cache_dir=os.path.expanduser("~/.cache/index-tts-cache/"))

# Import IndexTTS inference module
from indextts.infer_v2_5 import IndexTTS2

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# Initialize IndexTTS on your local GPU/weights directory
# Ensure your offline environment variable is set if running air-gapped: export HF_HUB_OFFLINE=1
# tts = IndexTTS(model_dir="checkpoints/IndexTTS-2")
# tts = IndexTTS2(cfg_path="checkpoints/config.yaml", model_dir="checkpoints", use_bf16=True)
IS_V25 = True
HALF_PRECISION = True
model_dir = "./checkpoints"


def build_tts(use_accel = False, use_torch_compile = False):
    """Build an IndexTTS2 instance with the requested acceleration options."""
    import torch

    kwargs = dict(
        model_dir = model_dir,
        cfg_path = f"{model_dir}/config.yaml",
        use_deepspeed = False,
        use_cuda_kernel = False,
        use_accel = use_accel,
        use_torch_compile = use_torch_compile,
        use_qwen_emo = True,
    )
    if IS_V25:
        use_bf16 = HALF_PRECISION and torch.cuda.is_bf16_supported()
        if HALF_PRECISION and not use_bf16:
            print(
                ">> BF16 is not supported on this device, falling back to full precision."
            )
        kwargs["use_bf16"] = use_bf16
    else:
        kwargs["use_fp16"] = HALF_PRECISION
    print(f"--- build_tts options {kwargs}")
    return IndexTTS2(**kwargs)


tts = build_tts(use_accel = False, use_torch_compile = False)


def normalize_circled_chars(text: str) -> str:
    # White circled digits (① to ⑳) -> Unicode U+2460 to U+2473
    trans_white = {chr(0x2460 + i - 1): str(i) for i in range(1, 21)}

    # Black circled digits (❶ to ❿) -> Unicode U+2776 to U+277F
    trans_black = {chr(0x2776 + i - 1): str(i) for i in range(1, 11)}

    # Combine both dictionaries
    mapping = {**trans_white, **trans_black}

    # Translate text using the mapping
    text = text.translate(str.maketrans(mapping))
    text = re.sub(r'[|｜]', ',', text)

    return text


class SpeechRequest(BaseModel):
    input: str
    speaker_audio: str = "preset-kokoro.wav"
    duration_factor: float = 1.0
    emotion: str = "neutral"
    lang: str = "ZH"  # Default to Chinese


@app.post("/v1/audio/speech")
def generate_audio(req: SpeechRequest):
    try:
        print(f"--- req {req}")
        cc_path = tts_cache.get(req.input)
        if cc_path:
            print(f"--- hit cache {tts_cache.get_key(req.input)}")
            # Read the resulting wav file into a buffer to return via FastAPI
            with open(cc_path, "rb") as f:
                audio_bytes = f.read()

            return Response(content = audio_bytes, media_type = "audio/wav")

        output_path = "/tmp/output_speech.wav"
        # 过滤掉所有标点符号
        cleaned_text = [
            c for c in req.input if not unicodedata.category(c).startswith('P')
        ]
        if not cleaned_text:
            return

        input = normalize_circled_chars(req.input)
        print(f'--- normalized input `{input}`')

        # IndexTTS generates audio conditioned on the reference speaker clip and text input
        # Note: You can also inject explicit pinyin inline (e.g., "银行hang2长") to override multi-pronunciation errors
        # kwargs = {
        #     'emo_audio_prompt': None,
        #     'emo_alpha': 1,
        #     'emo_vector': None,
        #     'use_emo_text': False,
        #     'emo_text': None,
        #     'use_random': False,
        #     'verbose': False,
        #     'max_text_tokens_per_segment': 120,
        #     'do_sample': True,
        #     'top_p': 0.8,
        #     'top_k': 30,
        #     'temperature': 0.8,
        #     'length_penalty': 0.0,
        #     'num_beams': 3,
        #     'repetition_penalty': 10.0,
        #     'max_mel_tokens': 1500,
        #     'lang': 'ZH',
        #     'duration_factor': 1.0,
        # }
        kwargs = dict(
            spk_audio_prompt = req.speaker_audio,
            text = input,
            output_path = output_path,
            duration_factor = req.duration_factor,
            lang = 'ZH',
        )

        tts.infer(**kwargs)

        tts_cache.put(req.input, output_path)
        # Read the resulting wav file into a buffer to return via FastAPI
        with open(output_path, "rb") as f:
            audio_bytes = f.read()

        return Response(content = audio_bytes, media_type = "audio/wav")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code = 500, detail = str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host = "127.0.0.1", port = 8880)
