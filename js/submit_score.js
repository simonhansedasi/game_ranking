function submitScore() {
    const puzzleStringInput = document.getElementById("puzzleString");

    const puzzleString = puzzleStringInput.value.trim();
    const gameType = puzzleString.split(/\s+/)[0].toLowerCase(); // Detect game type from first word
    const scoreElement = document.getElementById("dynamicScore");
    let plotImageElement;
    puzzleStringInput.value = '';

    // Determine plot image based on game type
    if (gameType === 'connections') {
        plotImageElement = document.getElementById('connectionsPlotImage');
    } else if (gameType === 'strands') {
        plotImageElement = document.getElementById('strandsPlotImage');
    } else if (gameType === 'wordle') {
        plotImageElement = document.getElementById('wordlePlotImage');
    } else {
        scoreElement.innerHTML = 'Unknown game type. Please enter a valid puzzle.';
        return;
    }

    // Simulate score fetch and update dynamically
    fetchBaseUrl()
        .then(baseURL => {
            const session_id = getCookie('session_id'); // Get session ID
            fetch(`${baseURL}/score_game`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_string: gameType,
                    puzzle_string: puzzleString,
                    session_id: session_id,
                }),
                credentials: 'include',
            })
            .then(response => response.json())
            .then(data => {
                scoreElement.innerHTML = `Your ${gameType} score: ${data.score}`;
                plotImageElement.src = `${baseURL}/static/images/${gameType}_recent_scores.png?t=${Date.now()}`;
                plotImageElement.style.display = 'block';
                
            fetchAndDisplayRanking(gameType, baseURL);

            })
            .catch(error => {
                scoreElement.textContent = `Error: ${error.message}`;
            });
        })
        .catch(error => {
            console.error('Error fetching BaseUrl:', error);
        });
}
