
(async function() {
    const target = document.querySelector("#definition");
    
    const frontWord = document.querySelector('#front')?.innerText.trim();
    const baseFormWord = document.querySelector('#baseform')?.innerText.trim();

    // Helper function to test if an endpoint exists
    async function checkEndpoint(word) {
        if (!word) return null;
        const url = `http://127.0.0.1:8001/${word}`;
        try {
            let response = await fetch(url, { method: 'HEAD' }); // HEAD request just checks headers
            if (response.ok) return url;
        } catch (e) {
            // Fetch failed or network error
        }
        return null;
    }

    // 1. Try Front
    let targetUrl = await checkEndpoint(frontWord);
    
    // 2. Fallback to BaseForm if Front didn't work
    if (!targetUrl && baseFormWord) {
        console.warn("Front failed, trying BaseForm...");
        targetUrl = await checkEndpoint(baseFormWord);
    }

    // 3. Set the iframe src if a valid URL was found
    if (targetUrl) {
        target.data = targetUrl;
    } else {
        // iframe.srcdoc = "<p style='color: red; font-family: sans-serif;'>Failed to load definition.</p>";
        console.warn(`No definitioin found for ${word}`)
    }
})();
