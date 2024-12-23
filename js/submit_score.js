function submitScore(gameType) {
    fetchBaseUrl()
        .then(baseURL => {
            let puzzleString = '';
            let scoreElementId = '';
            let rankElementId = '';
            let plotImageElement; // Declare plotImageElement only once

            if (gameType === 'connections') {
                puzzleString = document.getElementById("connectionsString").value;
                scoreElementId = "connectionsScore";
                rankElementId = "currentConnectionsRank";
                plotImageElement = document.getElementById('connectionsPlotImage');
            } else if (gameType === 'strands') {
                puzzleString = document.getElementById("strandsString").value;
                scoreElementId = "strandsScore";
                rankElementId = "currentStrandsRank";
                plotImageElement = document.getElementById('strandsPlotImage');
            }

            if (!plotImageElement) {
                console.error('Error: plotImageElement is null or undefined.');
                return;
            }

            const session_id = getCookie('session_id'); // Retrieve session ID from cookies

            // Send the puzzle string to the appropriate endpoint
            fetch(`${baseURL}/score_game`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_string: gameType, // Pass game type to identify the game
                    puzzle_string: puzzleString,
                    session_id: session_id, // Send the persistent session ID
                }),
                credentials: 'include',
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById(scoreElementId).innerHTML = `Your score: ${data.score}`;
                    const timestamp = new Date().getTime();
                    fetchAndDisplayRank(gameType, baseURL); 

                    plotImageElement.src = `${baseURL}/static/images/${gameType}_recent_scores.png?t=${timestamp}`;
                })
                .catch(error => {
                    document.getElementById(scoreElementId).textContent = `Error: ${error.message}`;
                    console.error('Error:', error);
                });
        })
        .catch(error => {
            console.error('Error fetching BaseUrl:', error);
        });
}
