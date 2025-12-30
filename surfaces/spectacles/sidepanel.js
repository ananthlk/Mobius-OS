// Basic Side Panel Logic relying on Nexus API
const API_URL = "http://localhost:8000/api/chat/completions";

// Use chrome.storage to get user ID if available, else anonymous
const getUserId = async () => {
    const result = await chrome.storage.local.get(['mobius_user_id']);
    return result.mobius_user_id || 'extension_user_anon';
};

const renderMessage = (role, content) => {
    const chatContainer = document.querySelector('.chat-container');
    const msgDiv = document.createElement('div');
    msgDiv.style.marginBottom = '10px';
    msgDiv.style.padding = '8px 12px';
    msgDiv.style.borderRadius = '8px';
    msgDiv.style.maxWidth = '80%';

    if (role === 'user') {
        msgDiv.style.marginLeft = 'auto';
        msgDiv.style.backgroundColor = '#2563eb';
        msgDiv.style.color = 'white';
    } else {
        msgDiv.style.marginRight = 'auto';
        msgDiv.style.backgroundColor = '#e5e7eb';
        msgDiv.style.color = 'black';
    }

    msgDiv.innerText = content;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
};

const setupUI = () => {
    const root = document.getElementById('root');
    root.innerHTML = `
        <div class="chat-container"></div>
        <div class="input-container">
            <input type="text" id="msg-input" placeholder="Ask Mobius..." style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        </div>
    `;

    const input = document.getElementById('msg-input');
    input.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter' && input.value.trim()) {
            const text = input.value;
            input.value = '';

            // Render User Message
            renderMessage('user', text);

            // Send to Nexus
            try {
                const userId = await getUserId();
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        messages: [{ role: 'user', content: text }]
                    })
                });
                const data = await response.json();
                renderMessage('assistant', data.content);
            } catch (err) {
                renderMessage('assistant', 'Error: Nexus unreachable.');
            }
        }
    });
};

document.addEventListener('DOMContentLoaded', setupUI);
