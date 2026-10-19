# TTS

## IndexTTS2 for Both Chinese and English, good, but a bit slow

```sh
git clone https://github.com/index-tts/index-tts.git
cd index-tts
pip install -U uv 
#uv sync --all-extras
￼
uv sync --all-extras --default-index "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
￼
uv tool install "huggingface-hub"

# IndexTTS-2.5
hf download IndexTeam/IndexTTS-2.5 --local-dir=checkpoints

# IndexTTS-2
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints_2
#[!NOTE] Some small models are downloaded automatically on first run. If your network has slow access to HuggingFace, set a mirror before running the code:
export HF_ENDPOINT="https://hf-mirror.com"
￼
# IndexTTS-2.5 (default)
uv run webui.py

uv run python indextts2_5_service.py
```

```sh
# cd FWQ code dir
cp services/indextts2.service ~/.config/systemd/user/
systemctl status --user indextts2.service 
systemctl enable --user indextts2.service 
systemctl restart --user indextts2.service 
systemctl status --user indextts2.service 
```

## Kokoro ONNX for English, lightweighted, low latency and good

```sh
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

## Sherpa VITS for Chinese (very bad for multi-pron Chinese char)

* Prefer

```sh
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/matcha-icefall-zh-baker.tar.bz2
tar xvf matcha-icefall-zh-baker.tar.bz2
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos-22khz-univ.onnx
```

* Optional

```sh
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-zh-aishell3.tar.bz2
tar xvf vits-zh-aishell3.tar.bz2
```

## Offline pytorch

```sh
pip download torch torchvision   --index-url https://download.pytorch.org/whl/cu132   --python-version 3.13    --only-binary=:all: -d ~/Downloads/pytorch_wheels-cp3.13/cu132
pip download torch torchvision    --index-url https://download.pytorch.org/whl/cu121   --python-version 3.13    --only-binary=:all: -d ~/Downloads/pytorch_wheels-cp3.13/cu121

pip download torch torchvision  torchaudio  --index-url https://download.pytorch.org/whl/cu124   --python-version 3.13    --only-binary=:all: -d ~/Downloads/pytorch_wheels-cp3.13/cu124

uv pip install --no-index --find-links ~/Downloads/pytorch_wheels-cp3.13/cu124 torch torchvision torchaudio
```


## Anki

### Style

```css

example, def_en, .auto-tts-div, .auto-tts li, def {
    list-style-type: none;
    cursor: pointer;
}

example::before, def_en::before, .auto-tts-div::before, .auto-tts li::before, def::before {
    content: "";
    display: inline-block;
    width: 16px;  /* Set your desired width */
    height: 16px; /* Set your desired height */
    margin-right: 6px;
    background-image: url('_spkr.png');
    background-size: contain;
    background-repeat: no-repeat;
    vertical-align: middle;
}

```

### Template

* EnglishSimpleWords -> Back

```html
<div class="front auto-tts-div">{{Pron}}{{Front}}</div>

<hr id=answer>
/{{Phon}}/<br>

{{Back}}

<hr>
<div class="auto-tts-div">{{Explains}}</div>
<hr>
<div class="auto-tts">{{Examples}}</div>

<script src="_indextts2.js" />

```

* XDHY -> Back
