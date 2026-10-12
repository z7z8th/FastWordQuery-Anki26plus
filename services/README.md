# TTS

## Kokoro ONNX for English

```sh
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```


## Sherpa VITS for Chinese

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

## Anki

```css

example, def_en, .auto-tts-div, .auto-tts li {
    list-style-type: none;
    cursor: pointer;
}

example::before, def_en::before, .auto-tts-div::before, .auto-tts li::before {
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


