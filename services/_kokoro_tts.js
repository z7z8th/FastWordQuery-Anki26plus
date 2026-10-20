async function list_voices()
{
    // 1. Fetch voices and parse JSON
    const voicesResponse = await fetch('http://localhost:8880/v1/voices');
    const voicesData = await voicesResponse.json();

    console.log(`voices`, JSON.stringify(voicesData, null, 2))
}
list_voices();

async function playAudioOfElement() {
    // const sentences = document.querySelectorAll('.auto-tts, example');
    // let rawText = "谢谢你我很好。";
    const sentences = [this];
    
    // 1. Split text into mixed language segments
    const regex = /([\u4e00-\u9fa5]+|[^\u4e00-\u9fa5]+)/g;

    // Helper function that returns a Promise resolving when the audio finishes playing
    const playAudio = (url, volume=1.0) => {
        return new Promise((resolve) => {
            const audio = new Audio(url);
            audio.volume = volume;
            audio.onended = () => resolve();
            audio.onerror = () => resolve(); // Prevent hanging if an audio fails
            audio.play().catch(err => {
                console.error("Playback error:", err);
                resolve();
            });
        });
    };

    for (let rawText of sentences) {
        rawText = rawText.innerText;
        const rawChunks = rawText.match(regex) || [];
        
        const segments = rawChunks.map(chunk => {
            const isChinese = /[\u4e00-\u9fa5]/.test(chunk);
            return {
                text: chunk.trim(),
                lang: isChinese ? 'zh' : 'en-us',
                voice: isChinese ? '0' : 'af_sarah',
                volume: isChinese ? 1.0 : 1.0,
            };
        }).filter(item => item.text.length > 0);

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
                        speed: 1.0,
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
                await playAudio(audioUrl);

            }
        } catch (error) {
            console.error('Error playing mixed language audio:', error.stack);
        }
    }
}

document.querySelectorAll('example, .auto-tts-div, .auto-tts li').forEach((e) => {e.addEventListener('click', playAudioOfElement)});
// document.getElementById('play-audio-btn').addEventListener('click', playAudioOfElement);
