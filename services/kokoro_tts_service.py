import io
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import soundfile as sf

# Import TTS engines
from kokoro_onnx import Kokoro
import sherpa_onnx
import numpy as np


app = FastAPI(title="Hybrid Kokoro + Sherpa TTS Service")

# Allow requests from Anki's web view environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Initialize Kokoro-ONNX (Best for English)
kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

# 2. Initialize Sherpa-ONNX (Best for Mandarin Chinese)
# rule_fsts_paths = [
#     "vits-zh-aishell3/phone.fst",
#     "vits-zh-aishell3/date.fst",
#     "vits-zh-aishell3/number.fst",
#     "vits-zh-aishell3/new_heteronym.fst"
# ]

# sherpa_config = sherpa_onnx.OfflineTtsConfig(
#     model=sherpa_onnx.OfflineTtsModelConfig(
#         vits=sherpa_onnx.OfflineTtsVitsModelConfig(
#             model="vits-zh-aishell3/vits-aishell3.onnx",
#             lexicon="vits-zh-aishell3/lexicon.txt",
#             tokens="vits-zh-aishell3/tokens.txt",
#         )
#     ),
#     rule_fsts=",".join(rule_fsts_paths),
#     rule_fars="vits-zh-aishell3/rule.far",
#     max_num_sentences=1,
# )
# sherpa_tts = sherpa_onnx.OfflineTts(sherpa_config)

rule_fsts_paths = [
    "matcha-icefall-zh-baker/phone.fst",
    "matcha-icefall-zh-baker/date.fst",
    "matcha-icefall-zh-baker/number.fst"
]

sherpa_config = sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
            acoustic_model="matcha-icefall-zh-baker/model-steps-3.onnx",
            vocoder="vocos-22khz-univ.onnx",
            lexicon="matcha-icefall-zh-baker/lexicon.txt",
            tokens="matcha-icefall-zh-baker/tokens.txt",
        )
    ),
    rule_fsts=",".join(rule_fsts_paths),
    max_num_sentences=1,
)
sherpa_tts = sherpa_onnx.OfflineTts(sherpa_config)

print("Hybrid TTS Service initialized with Kokoro and Matcha-Sherpa!")

class SpeechRequest(BaseModel):
    input: str
    voice: str = "af_sarah"  # Kokoro voice ID or Sherpa speaker index (e.g., "0")
    speed: float = 1.0
    lang: str = "en-us"
    volume: float = 1.0

@app.post("/v1/audio/speech")
def generate_audio(req: SpeechRequest):
    try:
        lang = req.lang.lower()
        
        # Route Chinese requests to Sherpa-ONNX for high-quality Mandarin synthesis
        if lang.lower() in ["zh", "zh-cn", "zh_cn", "cmn", "chinese"]:
            sid = int(req.voice) if req.voice.isdigit() else 0
            audio = sherpa_tts.generate(req.input, sid=sid, speed=req.speed)
            samples = audio.samples
            sample_rate = audio.sample_rate
            
        elif lang.lower() in ["en", "en-us", "en_us", "en-uk", "en_uk"]:
            # Route English/other languages to Kokoro-ONNX
            samples, sample_rate = kokoro.create(
                text=req.input,
                voice=req.voice,
                speed=req.speed,
                lang=lang
            )
        else:
            raise Exception(f"*** Error: Unsupported lang {lang}")

        if req.volume != 1.0:
            print(f"amplify volume {req.volume}")
            samples = np.array(samples, dtype=np.float32)
            samples = np.clip(samples * req.volume, -1.0, 1.0)

        # Write audio data into an in-memory buffer as WAV
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, samples, sample_rate, format="WAV")
        audio_buffer.seek(0)
        
        return Response(content=audio_buffer.read(), media_type="audio/wav")
        
    except Exception as e:
        # traceback.print_exc()
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/voices")
def get_available_voices():
    kokoro_voices = kokoro.get_voices()
    # Aishell3 contains built-in speakers (IDs 0 to 173). Exposing the first 10 for testing:
    sherpa_speakers = [str(i) for i in range(10)]
    
    return {
        "kokoro_voices": kokoro_voices,
        "sherpa_chinese_speakers": sherpa_speakers,
        "voices": kokoro_voices + sherpa_speakers
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8880)