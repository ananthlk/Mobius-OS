/**
 * Mobius Spectacles - Side Panel Logic
 * Manages context switching and dynamic UI components.
 */

// State
let currentContext = 'IDLE'; // IDLE, EMAIL, WEB, PATIENT

// DOM Elements
const contextIndicator = document.getElementById('context-indicator');
const contextName = document.getElementById('context-name');
const statusDot = document.querySelector('.status-dot');
const componentsArea = document.getElementById('context-components');
const chatContainer = document.getElementById('chat-container');
const input = document.getElementById('prompt-input');
const sendBtn = document.getElementById('send-btn');
const introContext = document.getElementById('intro-context');

// --- Context Definitions ---
const CONTEXTS = {
    IDLE: {
        name: 'System Idle',
        class: '',
        color: '#ccc',
        components: `
            <div class="subtitle" style="font-size:11px; color:#999;">Waiting for signal...</div>
        `
    },
    EMAIL: {
        name: 'Email Drafter',
        class: 'active',
        color: '#34A853',
        components: `
            <button class="control-btn primary">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Draft Reply
            </button>
            <button class="control-btn">Summarize</button>
            <button class="control-btn">Action Items</button>
        `
    },
    WEB: {
        name: 'Web Context',
        class: 'warn',
        color: '#FBBC05',
        components: `
            <div class="toggle-switch-wrapper">
                <span>Track Changes</span>
                <input type="checkbox" checked /> 
            </div>
            <button class="control-btn">Scrape Data</button>
        `
    },
    PATIENT: {
        name: 'Secure Patient Data',
        class: 'secure',
        color: '#EA4335',
        components: `
            <input type="text" placeholder="Patient ID" class="input-sm" />
            <button class="control-btn primary">Fetch Record</button>
        `
    }
};

// --- Logic ---

function setContext(mode) {
    if (!CONTEXTS[mode]) return;
    currentContext = mode;
    const ctx = CONTEXTS[mode];

    // Update Header
    contextName.textContent = ctx.name;
    statusDot.className = 'status-dot ' + ctx.class;
    introContext.textContent = ctx.name;

    // Update Components
    componentsArea.innerHTML = ctx.components;

    // Add slide-in animation class to components
    Array.from(componentsArea.children).forEach((child, i) => {
        child.style.opacity = '0';
        child.style.transform = 'translateY(10px)';
        child.style.transition = `all 0.3s ease ${i * 0.1}s`;
        setTimeout(() => {
            child.style.opacity = '1';
            child.style.transform = 'translateY(0)';
        }, 50);
    });

    addSystemMessage(`Context switched to: ${ctx.name}`);
}

function addSystemMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system-message';
    msgDiv.innerHTML = `
        <div class="avatar">
            <svg viewBox="0 0 24 24" class="icon" style="width:14px;height:14px;"><path d="M12 2L2 7l10 5 10-5-10-5zm0 9l2.5-1.25L12 8.5l-2.5 1.25L12 11zm0 2.5l-5-2.5-5 2.5L12 22l10-8.5-5-2.5-5 2.5z" fill="currentColor"/></svg>
        </div>
        <div class="bubble">${text}</div>
    `;
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function addUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user';
    msgDiv.innerHTML = `
        <div class="bubble">${text}</div>
        <div class="avatar">U</div>
    `;
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// --- Event Listeners ---

sendBtn.addEventListener('click', () => {
    const text = input.value.trim();
    if (text) {
        addUserMessage(text);
        input.value = '';
        setTimeout(() => {
            // Simulate response based on context
            if (currentContext === 'EMAIL') addSystemMessage("Drafting reply based on thread context...");
            else if (currentContext === 'PATIENT') addSystemMessage("Querying HIPAA-compliant database...");
            else addSystemMessage("Processing command...");
        }, 600);
    }
});

input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});

// --- Simulation for Demo ---
// In a real extension, this would listen to chrome.tabs.onUpdated or message passing
setTimeout(() => setContext('EMAIL'), 1000);

// Demo: Click header to cycle contexts
document.querySelector('.header').addEventListener('click', () => {
    const modes = Object.keys(CONTEXTS);
    const nextIndex = (modes.indexOf(currentContext) + 1) % modes.length;
    setContext(modes[nextIndex]);
});
