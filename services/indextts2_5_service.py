from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
import traceback
import unicodedata

from indextts.infer_v2_5 import IndexTTS2  # Adjust import based on your exact module path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# model_dir = "checkpoints_2_5"
model_dir = "checkpoints"

# Initialize IndexTTS
tts = IndexTTS2(model_dir=model_dir, cfg_path=f"{model_dir}/config.yaml", use_bf16=False, use_accel=False, use_torch_compile=False)

class SpeechRequest(BaseModel):
    input: str
    speaker_audio: str = "preset-kokoro.wav"
    speed: float = 1.0  # Changed from speed to duration_factor
    lang: str = "ZH"

@app.post("/v1/audio/speech")
def generate_audio(req: SpeechRequest):
    try:
        print(f'--- req {req}')
        output_path = "/tmp/output_speech.wav"
        # 过滤掉所有标点符号
        cleaned_text = [c for c in req.input if not unicodedata.category(c).startswith('P')]
        if not cleaned_text:
            return
        
        # Pass duration_factor instead of speed
        tts.infer(
            spk_audio_prompt=req.speaker_audio,
            text=req.input,
            output_path=output_path,
            # duration_factor=req.speed,  # <-- Updated parameter
            lang='ZH',
            max_mel_tokens = 16384,
        )
        
        with open(output_path, "rb") as f:
            audio_bytes = f.read()
            
        return Response(content=audio_bytes, media_type="audio/wav")
            
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8880)
