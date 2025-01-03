
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



function fetchAndDisplayRank(gameType, baseURL) {
    // Determine the appropriate rank element ID based on the game type
    let rankElementId;
    let plotImageElement;
    
    if (gameType === 'connections') {
        rankElementId = 'currentConnectionsRank';
        plotImageElement = document.getElementById('connectionsPlotImage');
    } else if (gameType === 'strands') {
        rankElementId = 'currentStrandsRank';
        plotImageElement = document.getElementById('strandsPlotImage');
    } else if (gameType === 'wordle') {
        rankElementId = 'currentWordleRank';
        plotImageElement = document.getElementById('wordlePlotImage');
    } else {
        console.error('Invalid game type:', gameType);
        return; // Exit the function if the game type is invalid
    }

    // Retrieve session ID
    const session_id = getCookie('session_id'); 

    // Create the request body with game type and session ID
    const requestBody = {
        game_type: gameType,
        session_id: session_id,
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
                    const dateKey = `date${i}`;
                    const muKey = `mu${i}`;
                    const varKey = `var${i}`;
                    
                    if (data[puzzleKey]) {
                        // Create a new div for each rank entry
                        const entry = document.createElement("div");
                        
                            const formattedDate = data[dateKey] ? data[dateKey].toString() : 'N/A';

                        entry.innerHTML = `# ${i} Puzzle ${parseFloat(data[puzzleKey])} -- ${formattedDate}<br> &mu; = ${data[muKey]}; &sigma;<sup>2</sup>  = ${data[varKey]}; D = ${parseFloat(data[rankKey])}<br><br><br>`;
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
            fetchAndDisplayRank('wordle', baseURL);
        })
        .catch(error => {
            console.error('Error fetching base URL:', error);
        });
};