from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import io
import torch
import torchaudio
import traceback

# Import IndexTTS inference module
from indextts.infer_v2_5 import IndexTTS2

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize IndexTTS on your local GPU/weights directory
# Ensure your offline environment variable is set if running air-gapped: export HF_HUB_OFFLINE=1
# tts = IndexTTS(model_dir="checkpoints/IndexTTS-2")
# tts = IndexTTS2(cfg_path="checkpoints/config.yaml", model_dir="checkpoints", use_bf16=True)
IS_V25 = True
HALF_PRECISION = True


def build_tts(use_accel=False, use_torch_compile=False):
    """Build an IndexTTS2 instance with the requested acceleration options."""
    import torch

    kwargs = dict(
        model_dir='./checkpoints',
        cfg_path="checkpoints/config.yaml",
        use_deepspeed=False,
        use_cuda_kernel=False,
        use_accel=use_accel,
        use_torch_compile=use_torch_compile,
        use_qwen_emo=True,
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
    print(f"build_tts options {kwargs}")
    return IndexTTS2(**kwargs)


tts = build_tts(use_accel=False, use_torch_compile=False)


class SpeechRequest(BaseModel):
    input: str
    speaker_audio: str = (
        "examples/voice_06.wav"  # Reference voice clip required for Zero-Shot cloning
    )
    speed: float = 1.0
    emotion: str = "neutral"
    lang: str = "ZH"  # Default to Chinese


@app.post("/v1/audio/speech")
def generate_audio(req: SpeechRequest):
    try:
        output_path = "/tmp/output_speech.wav"
        print(f"--- req {req}")

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
        kwargs = { 
            'lang': 'ZH'
        }

        kwargs.update(dict(
            spk_audio_prompt=req.speaker_audio,
            text=req.input,
            output_path=output_path,
            duration_factor=req.speed,
        ))

        tts.infer(**kwargs)

        # Read the resulting wav file into a buffer to return via FastAPI
        with open(output_path, "rb") as f:
            audio_bytes = f.read()

        return Response(content=audio_bytes, media_type="audio/wav")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8880)
