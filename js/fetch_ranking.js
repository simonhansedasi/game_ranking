
    function fetchBaseUrl() {
        return fetch('config.txt') // Path to the .txt file
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch config.txt');
                }
                return response.text();
            })
            .then(url => url.trim()); // Trim to avoid whitespace issues
    }





    // Function to fetch and display the current ranking
    function fetchAndDisplayRank(gameType, baseURL) {
        const rankElementId = gameType === 'connections' ? 'currentConnectionsRank' : 'currentStrandsRank';
        const plotImageElement = gameType === 'connections'
            ? document.getElementById('connectionsPlotImage') 
            : document.getElementById('strandsPlotImage');
        const session_id = getCookie('session_id'); // Retrieve session ID
        const requestBody = {
        game_type: gameType,
        session_id: session_id, // Include session ID in the request body
    };

        // const baseURL = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
            // ? `${apiBaseUrl}` // ngrok URL for local dev
            // : 'https://127.0.0.1:4000';

        fetch(`${baseURL}/get_ranking?game_type=${gameType}&session_id=${session_id}`, {
            method: 'GET',
            credentials: 'include',
        })
            .then(response => {
                // Log the response body to inspect it
                console.log('Response:', response);

                // Check if the response is OK (status code 200)
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                // Try parsing the JSON
                return response.json();
            })
            .then(data => {
                console.log(data); // Debugging purposes

                // Select the container div
                const container = document.getElementById(rankElementId);
                container.innerHTML = ""; // Clear any previous content

                // let hasRankings = false;
                for (let i = 1; i <= 5; i++) {
                    const puzzleKey = `puzz${i}`;
                    const rankKey = `rank${i}`;
                    if (data[puzzleKey]) {
                        // Create a new div for each rank entry
                        const entry = document.createElement("div");
                        entry.innerHTML = `Puzzle ${parseFloat(data[puzzleKey])}: ${parseFloat(data[rankKey])}`;
                        container.appendChild(entry);
                    }
                }

                // Display default message if no rankings are found
            if (!data.puzz1) {
                document.getElementById(rankElementId).innerHTML = 'Puzzle not yet ranked';
            }
                // Update the plot image
            const timestamp = new Date().getTime();

                plotImageElement.src = `${baseURL}/static/images/${gameType}_recent_scores.png?t=${timestamp}`;
            })        .catch(error => {
                console.error(`Error fetching ${gameType} ranking:`, error);
                document.getElementById(rankElementId).innerHTML = 'Error fetching ranking.';
            });
    }






// Ensure rankings are fetched on page load
window.onload = function () {
    fetchBaseUrl()
        .then(baseURL => {
            fetchAndDisplayRank('connections', baseURL);
            fetchAndDisplayRank('strands', baseURL);
        })
        .catch(error => {
            console.error('Error fetching base URL:', error);
        });
};