async function list_voices()
{
    // 1. Fetch voices and parse JSON
    const voicesResponse = await fetch('http://localhost:8880/v1/voices');
    const voicesData = await voicesResponse.json();

    console.log(`voices`, JSON.stringify(voicesData, null, 2))
}
// list_voices();

function destroyAudioPlay(player) {
    player.pause();
    player.currentTime = 0;
    player.src = '';
    player.load();
}

async function playAudioOfElement() {
    // XDHY head word
    let word = document.querySelector('hw')
    let rawText;
    if (word) {
        word = word.innerText && word.innerText[0]
        let elem = this.cloneNode(true);
        elem.querySelectorAll('num, ps').forEach(e => e.remove())
        rawText = elem.innerText;
        // replace for XDHY
        rawText = rawText.replace(/~|～/g, word);
    } else {
        rawText = this.innerText;
    }
    // const sentences = document.querySelectorAll('.auto-tts, example');
    // let rawText = "谢谢你我很好。";
    const sentences = [rawText];
    // console.log(`--- sentences ${sentences}`)
    
    // 1. Split text into mixed language segments

    // Helper function that returns a Promise resolving when the audio finishes playing
    const playAudio = (url, seg) => {
        return new Promise((resolve) => {
            console.log('--- playAudio', JSON.stringify(seg))
            if (window.audioPlayer) {
                destroyAudioPlay(window.audioPlayer);
            }
            const audio = new Audio(url);
            // audio.playbackRate = seg.speed;
            audio.volume = seg.volume;
            audio.onended = () => resolve();
            audio.onerror = () => resolve(); // Prevent hanging if an audio fails
            audio.play().catch(err => {
                console.error("Playback error:", err);
                resolve();
            });
            window.audioPlayer = audio;
        });
    };

    // const regex = /([\u4e00-\u9fa5]+|[^\u4e00-\u9fa5]+)/g;
    for (let rawText of sentences) {

        console.log(`--- rawText '${rawText}'`)

        // const rawChunks = rawText.match(regex) || [];
        
        // const segments = rawChunks.map(chunk => {
        //     const isChinese = /[\u4e00-\u9fa5]/.test(chunk);
        //     return {
        //         text: chunk.trim(),
        //         lang: isChinese ? 'zh' : 'en-us',
        //         voice: isChinese ? '0' : 'af_sarah',
        //         volume: isChinese ? 1.0 : 1.0,
        //     };
        // }).filter(item => item.text.length > 0);
        const segments = [
            {
                text: rawText.trim(),
                lang: 'ZH',
                duration_factor: 1.2,
                volume: 1.0,
            }
        ]

        try {
            // 2. Fetch audio blobs for each segment sequentially
            const audioBuffers = [];
            for (let seg of segments) {
                const response = await fetch('http://localhost:8880/v1/audio/speech', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        input: seg.text,
                        voice: seg.voice,
                        lang: seg.lang,
                        duration_factor: seg.duration_factor,
                        volume: seg.volume,
                    })
                });

                    //if (!response.ok) throw new Error(`Failed to generate audio for: ${seg.text}`);
                if (!response.ok) {
                    console.log(`Failed to generate audio for: ${seg.text}`);
                    continue;
                }

                
                const blob = await response.blob();
                const audioUrl = URL.createObjectURL(blob);
                await playAudio(audioUrl, seg);

            }
        } catch (error) {
            console.error('Error playing mixed language audio:', error.stack);
        }
    }
}

document.querySelectorAll('example, def_en, .auto-tts-div, .auto-tts li, def').forEach((e) => {e.addEventListener('click', playAudioOfElement)});
// document.getElementById('play-audio-btn').addEventListener('click', playAudioOfElement);
