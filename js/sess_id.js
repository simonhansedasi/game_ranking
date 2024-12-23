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

// Helper function to set a cookie
function setCookie(name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000); // Set expiration in milliseconds
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value}; ${expires}; path=/; Secure`;
}

// Helper function to get a cookie by name
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Ensure a session ID exists, creating it only if necessary
function ensureSessionID() {
    const existingSessionID = getCookie('session_id');

    if (!existingSessionID) {
        fetchBaseUrl()
            .then(apiBaseUrl => {
                fetch(`${apiBaseUrl}/get_session_id`, {
                    method: 'GET',
                    credentials: 'include',
                })
                .then(response => response.json())
                .then(data => {
                    setCookie('session_id', data.session_id, 30); // Persist for 30 days
                    console.log('Session ID created and saved:', data.session_id);
                })
                .catch(error => console.error('Error fetching session ID:', error));
            }) // Close fetchBaseUrl() then block here
            .catch(error => console.error('Error fetching base URL:', error));
    } else {
        console.log('Session ID already exists:', existingSessionID);
    }
}

// Ensure session ID on page load
ensureSessionID();
