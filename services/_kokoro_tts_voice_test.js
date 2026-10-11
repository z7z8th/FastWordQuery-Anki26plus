document.getElementById('play-audio-btn').addEventListener('click', async () => {
    let rawText = "谢谢你我很好。很高兴见到你。";
    
    try {
        // 1. Fetch voices and parse JSON
        const voicesResponse = await fetch('http://localhost:8880/v1/voices');
        const voicesData = await voicesResponse.json();
        const voices = voicesData.voices || [];
        
        const segments = voices.map(voice => {
            return {
                text: voice.replace(/_0+/, " ") + " " + rawText,
                lang: 'cmn', // Use 'cmn' for Mandarin Chinese
                voice: voice
            };
        });

        // Helper function that returns a Promise resolving when the audio finishes playing
        const playAudio = (url) => {
            return new Promise((resolve) => {
                const audio = new Audio(url);
                audio.onended = () => resolve();
                audio.onerror = () => resolve(); // Prevent hanging if an audio fails
                audio.play().catch(err => {
                    console.error("Playback error:", err);
                    resolve();
                });
            });
        };

        // 2. Loop through segments: Fetch -> Play -> Wait for finish -> Next
        for (let seg of segments) {
            const response = await fetch('http://localhost:8880/v1/audio/speech', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input: seg.text,
                    voice: seg.voice,
                    lang: seg.lang,
                    speed: 1.0
                })
            });

            if (!response.ok) {
                console.log(`Failed to generate audio for voice: ${seg.voice}`);
                continue;
            }

            const blob = await response.blob();
            const audioUrl = URL.createObjectURL(blob);

            // 3. Await playback completion before moving to the next iteration
            await playAudio(audioUrl);
        }

    } catch (error) {
        console.error('Error playing sequential audio:', error);
    }
});