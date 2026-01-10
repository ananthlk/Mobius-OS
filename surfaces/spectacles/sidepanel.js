/**
 * Möbius Spectacles - Side Panel Logic
 * Manages context switching and dynamic UI components.
 */

// State
let currentContext = 'IDLE'; // IDLE, EMAIL, WEB, PATIENT, ELIGIBILITY
let currentEmailData = null; // Stores extracted email data
let latestSystemMessageId = null; // Track latest system message for feedback
let feedbackInstances = new Map(); // Track feedback instances by message ID
let eligibilitySessionId = null; // Current eligibility session ID
let eligibilityCaseId = null; // Current eligibility case ID
let eligibilityEventSource = null; // SSE connection for eligibility events
let currentThinkingContainer = null; // Current thinking container element

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
            <button class="control-btn primary" id="draft-reply-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Draft Reply
            </button>
            <button class="control-btn" id="refresh-email-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>
                Refresh
            </button>
            <button class="control-btn" id="summarize-btn">Summarize</button>
            <button class="control-btn" id="action-items-btn">Action Items</button>
        `
    },
    WEB: {
        name: 'Web Context',
        class: 'warn',
        color: '#FBBC05',
        components: `
            <button class="control-btn primary" id="scrape-page-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
                Scrape Page
            </button>
            <button class="control-btn" id="scrape-tree-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                Scrape Tree
            </button>
            <button class="control-btn" id="extract-forms-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 18H8"/><path d="M16 14H8"/><path d="M10 6H8"/></svg>
                Extract Forms
            </button>
            <button class="control-btn" id="start-monitor-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
                Monitor Forms
            </button>
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
    },
    ELIGIBILITY: {
        name: 'Eligibility Check',
        class: 'active',
        color: '#6C5CE7',
        components: `
            <input type="text" id="mrn-input" placeholder="Enter MRN (e.g., MRN056)" class="input-sm" style="margin-bottom: 8px;" />
            <button class="control-btn primary" id="check-eligibility-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                Check Eligibility
            </button>
        `
    }
};

// --- Logic ---

function setContext(mode) {
    if (!CONTEXTS[mode]) return;
    
    // Clean up eligibility stream if switching away from ELIGIBILITY context
    if (currentContext === 'ELIGIBILITY' && mode !== 'ELIGIBILITY') {
        if (eligibilityEventSource) {
            eligibilityEventSource.close();
            eligibilityEventSource = null;
        }
        eligibilitySessionId = null;
        eligibilityCaseId = null;
        currentThinkingContainer = null;
        
        // Hide status bar
        const statusBar = document.getElementById('status-bar');
        if (statusBar) {
            statusBar.style.display = 'none';
        }
    }
    
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

    // Attach event listeners for context-specific buttons
    if (mode === 'EMAIL') {
        attachEmailButtonListeners();
        
        // Display email preview if available
        if (currentEmailData) {
            displayEmailPreview(currentEmailData);
        } else {
            // Even if no email data, show that we're in email mode
            addSystemMessage(`${ctx.name} mode activated. Open an email to extract content.`);
        }
    } else if (mode === 'WEB') {
        attachWebButtonListeners();
    } else if (mode === 'ELIGIBILITY') {
        attachEligibilityButtonListeners();
    }

    addSystemMessage(`Context switched to: ${ctx.name}`);
}

function displayEmailPreview(emailData) {
    const hasContent = emailData.subject || emailData.from || emailData.body;
    
    const previewHtml = `
        <div class="email-preview" style="background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; font-size: 12px;">
            <div style="font-weight: 600; margin-bottom: 8px; color: #202124;">📧 Email Preview (${emailData.client || 'unknown'})</div>
            ${hasContent ? (
                `${emailData.subject ? `<div style="margin-bottom: 6px;"><strong>Subject:</strong> ${escapeHtml(emailData.subject)}</div>` : ''}
                ${emailData.from ? `<div style="margin-bottom: 6px;"><strong>From:</strong> ${escapeHtml(emailData.from)}</div>` : ''}
                ${emailData.body ? `<div style="margin-top: 8px; max-height: 100px; overflow-y: auto; color: #5f6368;">${escapeHtml(emailData.body.substring(0, 200))}${emailData.body.length > 200 ? '...' : ''}</div>` : ''}`
            ) : (
                `<div style="color: #5f6368; font-style: italic;">Email client detected (${emailData.client}), but no email content found. Make sure you have an email open.</div>`
            )}
        </div>
    `;
    
    // Remove existing preview if any
    const existingPreview = chatContainer.querySelector('.email-preview');
    if (existingPreview) {
        existingPreview.remove();
    }
    
    // Insert preview after the intro message
    const introMsg = chatContainer.querySelector('.message.system-message');
    if (introMsg) {
        const previewDiv = document.createElement('div');
        previewDiv.innerHTML = previewHtml;
        introMsg.parentNode.insertBefore(previewDiv.firstElementChild, introMsg.nextSibling);
        scrollToBottom();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function attachEmailButtonListeners() {
    // Re-attach listeners after DOM update (componentsArea.innerHTML is reset)
    setTimeout(() => {
        const draftBtn = componentsArea.querySelector('#draft-reply-btn');
        const refreshBtn = componentsArea.querySelector('#refresh-email-btn');
        const summarizeBtn = componentsArea.querySelector('#summarize-btn');
        const actionItemsBtn = componentsArea.querySelector('#action-items-btn');
        
        if (draftBtn) {
            draftBtn.addEventListener('click', handleDraftReply);
        }
        if (refreshBtn) {
            refreshBtn.addEventListener('click', handleRefreshEmail);
        }
        if (summarizeBtn) {
            summarizeBtn.addEventListener('click', handleSummarize);
        }
        if (actionItemsBtn) {
            actionItemsBtn.addEventListener('click', handleActionItems);
        }
    }, 100);
}

async function handleRefreshEmail() {
    console.log('[Möbius Spectacles Side Panel] Manual refresh requested');
    addSystemMessage('🔄 Refreshing email data...');
    
    try {
        // Request extraction from background script
        chrome.runtime.sendMessage({ type: 'REQUEST_EXTRACTION' }).then(() => {
            console.log('[Möbius Spectacles Side Panel] Extraction request sent');
        }).catch(err => {
            console.error('[Möbius Spectacles Side Panel] Error requesting extraction:', err);
            addSystemMessage('⚠️ Error requesting extraction. Make sure you have Gmail open in a tab.');
        });
    } catch (error) {
        console.error('[Möbius Spectacles Side Panel] Error:', error);
        addSystemMessage('⚠️ Error: ' + error.message);
    }
}

async function handleDraftReply() {
    if (!currentEmailData) {
        addSystemMessage("⚠️ No email detected. Please open an email first.");
        return;
    }

    const loadingId = addSystemMessage('<div class="spinner-dots">Drafting reply...</div>', true);

    try {
        const response = await fetch('http://localhost:8000/api/spectacles/email/draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "spectacles_user", // TODO: Get real user
                email_context: {
                    subject: currentEmailData.subject || '',
                    from_: currentEmailData.from || '',  // Use from_ to match Python model
                    body: currentEmailData.body || '',
                    client: currentEmailData.client || 'other'
                }
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        removeMessage(loadingId);
        
        if (data.status === 'success' && data.draft) {
            addSystemMessage(`📝 Draft Reply:\n\n${data.draft}`);
        } else {
            addSystemMessage("⚠️ Failed to generate draft. Please try again.");
        }

        } catch (error) {
            removeMessage(loadingId);
            console.error('Draft reply error:', error);
            if (error.message && error.message.includes('Failed to fetch')) {
                addSystemMessage("⚠️ Connection to Nexus failed. Is the backend running at http://localhost:8000?");
            } else {
                addSystemMessage(`⚠️ Error: ${error.message || 'Unknown error occurred'}`);
            }
        }
}

async function handleSummarize() {
    if (!currentEmailData) {
        addSystemMessage("⚠️ No email detected. Please open an email first.");
        return;
    }
    addSystemMessage("Summarize feature coming soon!");
}

async function handleActionItems() {
    if (!currentEmailData) {
        addSystemMessage("⚠️ No email detected. Please open an email first.");
        return;
    }
    addSystemMessage("Action Items feature coming soon!");
}

function attachWebButtonListeners() {
    // Re-attach listeners after DOM update
    setTimeout(() => {
        const scrapePageBtn = componentsArea.querySelector('#scrape-page-btn');
        const scrapeTreeBtn = componentsArea.querySelector('#scrape-tree-btn');
        const extractFormsBtn = componentsArea.querySelector('#extract-forms-btn');
        const startMonitorBtn = componentsArea.querySelector('#start-monitor-btn');
        
        if (scrapePageBtn) {
            scrapePageBtn.addEventListener('click', handleScrapePage);
        }
        if (scrapeTreeBtn) {
            scrapeTreeBtn.addEventListener('click', handleScrapeTree);
        }
        if (extractFormsBtn) {
            extractFormsBtn.addEventListener('click', handleExtractForms);
        }
        if (startMonitorBtn) {
            startMonitorBtn.addEventListener('click', handleStartFormMonitoring);
        }
    }, 100);
}

function attachEligibilityButtonListeners() {
    // Re-attach listeners after DOM update
    setTimeout(() => {
        const checkEligibilityBtn = componentsArea.querySelector('#check-eligibility-btn');
        const mrnInput = componentsArea.querySelector('#mrn-input');
        
        if (checkEligibilityBtn) {
            checkEligibilityBtn.addEventListener('click', handleEligibilityCheck);
        }
        
        if (mrnInput) {
            // Allow Enter key to trigger check
            mrnInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handleEligibilityCheck();
                }
            });
        }
    }, 100);
}

function handleScrapePageResponse(response, loadingId) {
    if (response && response.success && response.pageData) {
        const data = response.pageData;
        
        // Display scraped content
        const previewHtml = `
            <div class="scraped-content" style="background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; font-size: 12px;">
                <div style="font-weight: 600; margin-bottom: 8px; color: #202124;">📄 Page Scraped</div>
                <div style="margin-bottom: 6px;"><strong>Title:</strong> ${escapeHtml(data.title || 'N/A')}</div>
                <div style="margin-bottom: 6px;"><strong>URL:</strong> <a href="${data.url}" target="_blank" style="color: #1a73e8;">${escapeHtml(data.url)}</a></div>
                <div style="margin-bottom: 6px;"><strong>Text Length:</strong> ${data.textLength || 0} characters</div>
                ${data.links && data.links.length > 0 ? `<div style="margin-bottom: 6px;"><strong>Links:</strong> ${data.links.length} found</div>` : ''}
                ${data.images && data.images.length > 0 ? `<div style="margin-bottom: 6px;"><strong>Images:</strong> ${data.images.length} found</div>` : ''}
                ${data.headings && data.headings.length > 0 ? `<div style="margin-bottom: 6px;"><strong>Headings:</strong> ${data.headings.length} found</div>` : ''}
                <div style="margin-top: 8px; max-height: 200px; overflow-y: auto; color: #5f6368; font-size: 11px; white-space: pre-wrap;">${escapeHtml(data.text ? data.text.substring(0, 1000) : '')}${data.text && data.text.length > 1000 ? '...' : ''}</div>
            </div>
        `;
        
        const previewDiv = document.createElement('div');
        previewDiv.innerHTML = previewHtml;
        chatContainer.appendChild(previewDiv);
        scrollToBottom();
        
        // Send to backend (fire and forget)
        sendScrapedDataToBackend(data, 'page').catch(err => {
            console.error('[Möbius Spectacles] Error sending to backend:', err);
        });
    } else {
        addSystemMessage('⚠️ Failed to scrape page content');
    }
}

async function handleScrapePage() {
    console.log('[Möbius Spectacles Side Panel] Scrape page requested');
    const loadingId = addSystemMessage('🔄 Scraping page content...', true);
    
    try {
        // Get active tab
        chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
            if (!tabs[0]) {
                removeMessage(loadingId);
                addSystemMessage('⚠️ No active tab found');
                return;
            }
            
            const tab = tabs[0];
            const url = tab.url || '';
            
            // Check if URL is injectable (not chrome:// or extension pages)
            if (url.startsWith('chrome://') || url.startsWith('chrome-extension://') || url.startsWith('edge://') || url.startsWith('about:')) {
                removeMessage(loadingId);
                addSystemMessage('⚠️ Cannot scrape this page type. Please navigate to a regular website.');
                return;
            }
            
            try {
                // First, try to send message to existing content script
                chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE_PAGE' }, async (response) => {
                    if (chrome.runtime.lastError) {
                        // Content script not injected - try to inject it programmatically
                        console.log('[Möbius Spectacles] Content script not found, injecting...');
                        
                        try {
                            // Inject the script
                            await chrome.scripting.executeScript({
                                target: { tabId: tab.id },
                                files: ['content.js']
                            });
                            
                            // Wait a bit for script to initialize
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            // Try sending message again
                            chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE_PAGE' }, (response) => {
                                removeMessage(loadingId);
                                
                                if (chrome.runtime.lastError) {
                                    console.error('[Möbius Spectacles] Error:', chrome.runtime.lastError);
                                    addSystemMessage('⚠️ Error: ' + chrome.runtime.lastError.message + '. Try refreshing the page.');
                                    return;
                                }
                                
                                handleScrapePageResponse(response, loadingId);
                            });
                        } catch (injectError) {
                            removeMessage(loadingId);
                            console.error('[Möbius Spectacles] Error injecting script:', injectError);
                            addSystemMessage('⚠️ Cannot inject script on this page. Try refreshing the page first.');
                        }
                        return;
                    }
                    
                    // Success - content script responded
                    removeMessage(loadingId);
                    handleScrapePageResponse(response, loadingId);
                });
            } catch (error) {
                removeMessage(loadingId);
                console.error('[Möbius Spectacles] Error scraping page:', error);
                addSystemMessage('⚠️ Error: ' + error.message);
            }
        });
    } catch (error) {
        removeMessage(loadingId);
        console.error('[Möbius Spectacles] Error:', error);
        addSystemMessage('⚠️ Error: ' + error.message);
    }
}

function handleScrapeTreeResponse(response, loadingId) {
    if (response && response.success && response.treeData) {
        const data = response.treeData;
        
        const treeInfo = JSON.stringify(data.tree, null, 2);
        const treeSize = new Blob([treeInfo]).size;
        
        addSystemMessage(`📊 DOM Tree Scraped\n\nTitle: ${data.title}\nURL: ${data.url}\nTree Size: ${(treeSize / 1024).toFixed(2)} KB\n\nTree structure saved to backend.`);
        
        sendScrapedDataToBackend(data, 'tree').catch(err => {
            console.error('[Möbius Spectacles] Error sending to backend:', err);
        });
    } else {
        addSystemMessage('⚠️ Failed to scrape DOM tree');
    }
}

async function handleExtractForms() {
    const loadingId = addSystemMessage('🔍 Extracting form fields...', true);
    
    try {
        chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
            if (!tabs[0]) {
                removeMessage(loadingId);
                addSystemMessage('⚠️ No active tab found');
                return;
            }
            
            chrome.tabs.sendMessage(tabs[0].id, { type: 'EXTRACT_FORMS' }, (response) => {
                removeMessage(loadingId);
                
                if (chrome.runtime.lastError) {
                    addSystemMessage('⚠️ Error: ' + chrome.runtime.lastError.message + '. Try refreshing the page.');
                    return;
                }
                
                if (response && response.success && response.formData) {
                    displayFormData(response.formData);
                } else {
                    addSystemMessage('⚠️ Failed to extract forms');
                }
            });
        });
    } catch (error) {
        removeMessage(loadingId);
        addSystemMessage('⚠️ Error: ' + error.message);
    }
}

function displayFormData(formData) {
    let message = `📋 Found ${formData.forms.length} form(s) on this page:\n\n`;
    
    formData.forms.forEach((form, idx) => {
        if (form.standalone) {
            message += `**Standalone Fields (${form.fields.length}):**\n`;
        } else {
            message += `**Form ${idx + 1}** (${form.fields.length} fields):\n`;
            if (form.formId) message += `ID: ${form.formId}\n`;
            if (form.formName) message += `Name: ${form.formName}\n`;
        }
        
        form.fields.forEach((field, fieldIdx) => {
            message += `\n${fieldIdx + 1}. `;
            if (field.label) message += `**${field.label}** `;
            message += `(${field.type})`;
            if (field.name) message += ` [name: ${field.name}]`;
            if (field.id) message += ` [id: ${field.id}]`;
            if (field.placeholder) message += `\n   Placeholder: "${field.placeholder}"`;
            if (field.value) message += `\n   Value: "${field.value.substring(0, 50)}"`;
            if (field.required) message += ` [Required]`;
            if (field.disabled) message += ` [Disabled]`;
            if (field.selector) message += `\n   Selector: \`${field.selector}\``;
        });
        
        message += '\n\n';
    });
    
    addSystemMessage(message);
}

async function handleStartFormMonitoring() {
    addSystemMessage('🔍 Starting form monitoring...');
    
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) {
            addSystemMessage('⚠️ No active tab found');
            return;
        }
        
        chrome.tabs.sendMessage(tabs[0].id, { type: 'START_FORM_MONITORING' }, (response) => {
            if (chrome.runtime.lastError) {
                addSystemMessage('⚠️ Error: ' + chrome.runtime.lastError.message);
                return;
            }
            
            if (response && response.success) {
                addSystemMessage('✅ Form monitoring started. Watching for form changes...');
            }
        });
    });
}

// Function to update a form field (can be called from chat or direct command)
async function updateFormFieldValue(selector, value) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) {
            addSystemMessage('⚠️ No active tab found');
            return;
        }
        
        chrome.tabs.sendMessage(tabs[0].id, {
            type: 'UPDATE_FORM_FIELD',
            selector: selector,
            value: value
        }, (response) => {
            if (chrome.runtime.lastError) {
                addSystemMessage('⚠️ Error: ' + chrome.runtime.lastError.message);
                return;
            }
            
            if (response && response.success) {
                addSystemMessage(`✅ Updated field: ${selector} = "${value}"`);
            } else {
                addSystemMessage(`⚠️ Failed to update field: ${response?.result?.error || 'Unknown error'}`);
            }
        });
    });
}

async function handleEligibilityCheck() {
    const mrnInput = componentsArea.querySelector('#mrn-input');
    if (!mrnInput) {
        addSystemMessage('⚠️ MRN input not found');
        return;
    }
    
    const mrn = mrnInput.value.trim().toUpperCase();
    if (!mrn) {
        addSystemMessage('⚠️ Please enter an MRN (e.g., MRN056)');
        return;
    }
    
    // Validate MRN format
    if (!/^MRN\w+$/.test(mrn)) {
        addSystemMessage('⚠️ Invalid MRN format. Expected format: MRN followed by alphanumeric characters (e.g., MRN056)');
        return;
    }
    
    const loadingId = addSystemMessage(`🔄 Checking eligibility for ${mrn}...`, true);
    
    try {
        const response = await fetch('http://localhost:8000/api/spectacles/eligibility/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "spectacles_user", // TODO: Get real user
                mrn: mrn
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        removeMessage(loadingId);
        
        if (data.status === 'success') {
            eligibilitySessionId = data.session_id;
            eligibilityCaseId = data.case_id;
            
            addSystemMessage(`✅ Eligibility check initiated for ${mrn}\nSession ID: ${eligibilitySessionId}\nCase ID: ${eligibilityCaseId}`);
            
            // Start SSE connection
            connectEligibilityStream(eligibilitySessionId);
        } else {
            addSystemMessage(`⚠️ Failed to start eligibility check: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        removeMessage(loadingId);
        console.error('Eligibility check error:', error);
        if (error.message && error.message.includes('Failed to fetch')) {
            addSystemMessage('⚠️ Connection to Nexus failed. Is the backend running at http://localhost:8000?');
        } else {
            addSystemMessage(`⚠️ Error: ${error.message || 'Unknown error occurred'}`);
        }
    }
}

function connectEligibilityStream(sessionId) {
    // Close existing connection if any
    if (eligibilityEventSource) {
        eligibilityEventSource.close();
        eligibilityEventSource = null;
    }
    
    const statusBar = document.getElementById('status-bar');
    const statusText = document.getElementById('status-text');
    
    // Show status bar
    if (statusBar) {
        statusBar.style.display = 'flex';
        statusBar.className = 'status-bar status-in_progress';
        statusText.textContent = 'Connecting to eligibility service...';
    }
    
    const streamUrl = `http://localhost:8000/api/spectacles/eligibility/stream?session_id=${sessionId}`;
    console.log('[Möbius Spectacles] Connecting to SSE stream:', streamUrl);
    
    eligibilityEventSource = new EventSource(streamUrl);
    
    eligibilityEventSource.onopen = () => {
        console.log('[Möbius Spectacles] SSE connection opened');
        if (statusBar && statusText) {
            statusBar.style.display = 'flex';
            statusBar.className = 'status-bar status-in_progress';
            statusText.textContent = 'Connected. Waiting for updates...';
        }
    };
    
    eligibilityEventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('[Möbius Spectacles] SSE event received:', data.type);
            
            if (data.type === 'connected') {
                console.log('[Möbius Spectacles] SSE stream connected for session', data.session_id);
                return;
            }
            
            if (data.type === 'status') {
                handleStatusEvent(data.payload);
            } else if (data.type === 'thinking') {
                handleThinkingEvent(data.payload);
            } else if (data.type === 'chat') {
                handleChatEvent(data.payload);
            } else if (data.type === 'error') {
                console.error('[Möbius Spectacles] SSE error:', data.message);
                addSystemMessage(`⚠️ Stream error: ${data.message}`);
                if (statusBar && statusText) {
                    statusBar.className = 'status-bar status-error';
                    statusText.textContent = `Error: ${data.message}`;
                }
            }
        } catch (error) {
            console.error('[Möbius Spectacles] Error parsing SSE event:', error, event.data);
        }
    };
    
    eligibilityEventSource.onerror = (error) => {
        console.error('[Möbius Spectacles] SSE connection error:', error);
        if (eligibilityEventSource.readyState === EventSource.CLOSED) {
            console.log('[Möbius Spectacles] SSE connection closed, attempting reconnect...');
            // Reconnect after 2 seconds
            setTimeout(() => {
                if (eligibilitySessionId) {
                    connectEligibilityStream(eligibilitySessionId);
                }
            }, 2000);
        }
    };
}

function handleStatusEvent(payload) {
    const statusBar = document.getElementById('status-bar');
    const statusText = document.getElementById('status-text');
    const statusDetails = document.getElementById('status-details');
    const statusProbability = document.getElementById('status-probability');
    const statusVisits = document.getElementById('status-visits');
    
    if (!statusBar || !statusText) {
        console.warn('[Möbius Spectacles] Status bar elements not found');
        return;
    }
    
    const phase = payload.phase || 'unknown';
    const status = payload.status || 'unknown';
    const message = payload.message || 'Processing...';
    const data = payload.data || {};
    
    // Update status bar classes and message
    statusBar.className = `status-bar status-${status}`;
    statusText.textContent = `${phase.charAt(0).toUpperCase() + phase.slice(1)}: ${message}`;
    
    // Show rich details if available (e.g., scoring complete with probability data)
    if (data.overall_probability !== undefined && status === 'complete' && phase === 'scoring') {
        // Format probability as percentage
        const probabilityPercent = (data.overall_probability * 100).toFixed(1);
        if (statusProbability) {
            statusProbability.textContent = `Overall Likelihood to Pay: ${probabilityPercent}%`;
        }
        
        // Format visit dates
        if (data.visits && data.visits.length > 0) {
            const visitDates = data.visits
                .filter(v => v.visit_date)
                .map(v => {
                    const date = new Date(v.visit_date);
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                })
                .join(', ');
            
            if (visitDates && statusVisits) {
                statusVisits.textContent = `Visit Dates: ${visitDates}`;
            }
        }
        
        // Show details section
        if (statusDetails) {
            statusDetails.style.display = 'flex';
        }
    } else {
        // Hide details for other phases
        if (statusDetails) {
            statusDetails.style.display = 'none';
        }
    }
    
    console.log('[Möbius Spectacles] Status update:', { phase, status, message, data });
    
    // Show status bar if hidden
    if (statusBar.style.display === 'none' || statusBar.style.display === '') {
        statusBar.style.display = 'flex';
    }
    
    // If status is complete or error, stop streaming animation on thinking container
    if (status === 'complete' || status === 'error') {
        if (currentThinkingContainer) {
            const label = currentThinkingContainer._label;
            if (label) {
                label.textContent = 'Thinking';
            }
        }
    }
}

function handleThinkingEvent(payload) {
    // Get or create thinking container
    if (!currentThinkingContainer) {
        currentThinkingContainer = createThinkingContainer();
        chatContainer.appendChild(currentThinkingContainer);
        scrollToBottom();
    }
    
    // Extract thinking message - THINKING events have payload.message
    const message = payload.message || payload.content || '';
    if (!message) return;
    
    // Update thinking container with streaming state
    updateThinkingContainer(currentThinkingContainer, message, true);
}

function handleChatEvent(payload) {
    // Handle OUTPUT events - these contain chat messages/questions
    // OUTPUT events from eligibility v2 have structure: {role: 'assistant', content: '...'}
    // But eligibility v2 also sends presentation_summary and next_questions in turn responses
    // which get stored in OUTPUT bucket
    
    const content = payload.content || payload.presentation_summary || '';
    const nextQuestions = payload.next_questions || [];
    
    // Stop thinking animation when chat message arrives
    if (currentThinkingContainer) {
        const label = currentThinkingContainer._label;
        if (label) {
            label.textContent = 'Thinking';
        }
    }
    
    if (content) {
        addSystemMessage(content);
    }
    
    if (nextQuestions && nextQuestions.length > 0) {
        // Display questions
        const questionsHtml = nextQuestions.map((q, idx) => {
            const questionText = typeof q === 'string' ? q : (q.text || q.question || '');
            return `<div style="margin: 8px 0; padding: 8px; background: var(--bg-secondary); border-radius: 6px; border-left: 3px solid var(--primary-blue);">
                <strong>Question ${idx + 1}:</strong> ${escapeHtml(questionText)}
            </div>`;
        }).join('');
        
        const questionsDiv = document.createElement('div');
        questionsDiv.innerHTML = `
            <div style="margin-top: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">Questions:</div>
            ${questionsHtml}
        `;
        chatContainer.appendChild(questionsDiv);
        scrollToBottom();
    }
}

function createThinkingContainer() {
    const container = document.createElement('div');
    container.className = 'thinking-container';
    container.id = 'thinking-' + Date.now();
    
    let isExpanded = true; // Start expanded when streaming
    let thinkingMessages = [];
    
    const toggleButton = document.createElement('button');
    toggleButton.className = 'thinking-toggle';
    toggleButton.style.cssText = 'width: 100%; text-align: left; display: flex; align-items: center; justify-content: space-between; padding: 8px 0; background: none; border: none; cursor: pointer; color: var(--text-secondary);';
    
    const leftSection = document.createElement('div');
    leftSection.style.cssText = 'display: flex; align-items: center; gap: 8px;';
    
    const indicator = document.createElement('div');
    indicator.className = 'thinking-indicator';
    indicator.style.cssText = 'width: 0.5px; height: 16px; background: var(--primary-blue); flex-shrink: 0;';
    
    const label = document.createElement('span');
    label.className = 'thinking-label';
    label.style.cssText = 'font-size: 11px; font-weight: 500; color: var(--primary-blue);';
    label.textContent = 'Thinking';
    
    const count = document.createElement('span');
    count.className = 'thinking-count';
    count.style.cssText = 'font-size: 11px; color: var(--text-muted);';
    count.textContent = '(0)';
    
    const chevron = document.createElement('span');
    chevron.className = 'thinking-chevron';
    chevron.innerHTML = '▼';
    chevron.style.cssText = 'font-size: 10px; color: var(--text-muted); transition: transform 0.2s;';
    
    leftSection.appendChild(indicator);
    leftSection.appendChild(label);
    leftSection.appendChild(count);
    toggleButton.appendChild(leftSection);
    toggleButton.appendChild(chevron);
    
    const contentArea = document.createElement('div');
    contentArea.className = 'thinking-content';
    contentArea.style.cssText = 'margin-left: 10px; margin-top: 4px; max-height: 300px; overflow-y: auto; display: block;';
    
    const messagesContainer = document.createElement('div');
    messagesContainer.className = 'thinking-messages';
    messagesContainer.style.cssText = 'display: flex; flex-direction: column; gap: 6px;';
    contentArea.appendChild(messagesContainer);
    
    toggleButton.addEventListener('click', () => {
        isExpanded = !isExpanded;
        if (isExpanded) {
            contentArea.style.display = 'block';
            chevron.style.transform = 'rotate(0deg)';
        } else {
            contentArea.style.display = 'none';
            chevron.style.transform = 'rotate(-90deg)';
        }
    });
    
    container.appendChild(toggleButton);
    container.appendChild(contentArea);
    
    // Store messages array in container for updates
    container._thinkingMessages = thinkingMessages;
    container._messagesContainer = messagesContainer;
    container._count = count;
    container._label = label;
    
    return container;
}

function updateThinkingContainer(container, message, isStreaming) {
    if (!container || !container._thinkingMessages) return;
    
    const messages = container._thinkingMessages;
    const messagesContainer = container._messagesContainer;
    const count = container._count;
    const label = container._label;
    
    // Add new message if provided
    if (message && !messages.includes(message)) {
        messages.push(message);
        
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = 'font-size: 11px; color: var(--text-secondary); line-height: 1.5; padding-left: 8px; border-left: 2px solid var(--primary-blue-light);';
        messageDiv.textContent = message;
        messagesContainer.appendChild(messageDiv);
    }
    
    // Update count
    if (count) {
        count.textContent = `(${messages.length})`;
    }
    
    // Update label for streaming state
    if (label) {
        if (isStreaming) {
            label.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 4px;"><span style="width: 4px; height: 4px; background: var(--primary-blue); border-radius: 50%; animation: pulse 1.5s ease-in-out infinite;"></span>Thinking</span>';
        } else {
            label.textContent = 'Thinking';
        }
    }
    
    // Scroll to bottom
    const contentArea = container.querySelector('.thinking-content');
    if (contentArea) {
        contentArea.scrollTop = contentArea.scrollHeight;
    }
    
    scrollToBottom();
}

async function handleScrapeTree() {
    console.log('[Möbius Spectacles Side Panel] Scrape DOM tree requested');
    const loadingId = addSystemMessage('🔄 Scraping DOM tree structure...', true);
    
    try {
        chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
            if (!tabs[0]) {
                removeMessage(loadingId);
                addSystemMessage('⚠️ No active tab found');
                return;
            }
            
            const tab = tabs[0];
            const url = tab.url || '';
            
            // Check if URL is injectable
            if (url.startsWith('chrome://') || url.startsWith('chrome-extension://') || url.startsWith('edge://') || url.startsWith('about:')) {
                removeMessage(loadingId);
                addSystemMessage('⚠️ Cannot scrape this page type. Please navigate to a regular website.');
                return;
            }
            
            try {
                chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE_DOM_TREE' }, async (response) => {
                    if (chrome.runtime.lastError) {
                        // Try to inject script
                        console.log('[Möbius Spectacles] Content script not found, injecting...');
                        
                        try {
                            await chrome.scripting.executeScript({
                                target: { tabId: tab.id },
                                files: ['content.js']
                            });
                            
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE_DOM_TREE' }, (response) => {
                                removeMessage(loadingId);
                                
                                if (chrome.runtime.lastError) {
                                    console.error('[Möbius Spectacles] Error:', chrome.runtime.lastError);
                                    addSystemMessage('⚠️ Error: ' + chrome.runtime.lastError.message);
                                    return;
                                }
                                
                                handleScrapeTreeResponse(response, loadingId);
                            });
                        } catch (injectError) {
                            removeMessage(loadingId);
                            console.error('[Möbius Spectacles] Error injecting script:', injectError);
                            addSystemMessage('⚠️ Cannot inject script on this page. Try refreshing the page first.');
                        }
                        return;
                    }
                    
                    removeMessage(loadingId);
                    handleScrapeTreeResponse(response, loadingId);
                });
            } catch (error) {
                removeMessage(loadingId);
                console.error('[Möbius Spectacles] Error scraping tree:', error);
                addSystemMessage('⚠️ Error: ' + error.message);
            }
        });
    } catch (error) {
        removeMessage(loadingId);
        console.error('[Möbius Spectacles] Error:', error);
        addSystemMessage('⚠️ Error: ' + error.message);
    }
}

async function sendScrapedDataToBackend(data, type) {
    try {
        const response = await fetch('http://localhost:8000/api/spectacles/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "spectacles_user", // TODO: Get real user
                scrape_type: type, // 'page' or 'tree'
                data: data
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('[Möbius Spectacles] Scraped data sent to backend:', result);
        } else {
            console.error('[Möbius Spectacles] Backend error:', response.status);
        }
    } catch (error) {
        console.error('[Möbius Spectacles] Error sending to backend:', error);
        // Don't show error to user - scraping still worked locally
    }
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

sendBtn.addEventListener('click', async () => {
    const text = input.value.trim();
    if (!text) return;
    
    addUserMessage(text);
    input.value = '';

    // Show loading indicator
    const loadingId = addSystemMessage('<div class="spinner-dots">Thinking...</div>', true);

    try {
        // Route to eligibility endpoint if in ELIGIBILITY context with active session
        if (currentContext === 'ELIGIBILITY' && eligibilitySessionId && eligibilityCaseId) {
            // Send to eligibility v2 turn endpoint
            const uiEvent = {
                event_type: "user_message",
                data: { message: text },
                timestamp: new Date().toISOString()
            };
            
            const response = await fetch(`http://localhost:8000/api/eligibility-v2/cases/${eligibilityCaseId}/turn`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': String(eligibilitySessionId),
                    'X-User-ID': 'spectacles_user',
                    'X-Patient-ID': eligibilityCaseId.replace('spectacles_', '').split('_')[0] || ''
                },
                body: JSON.stringify(uiEvent)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Remove loading indicator
            removeMessage(loadingId);
            
            // The SSE stream will handle the response (thinking messages, status updates, chat messages)
            // We don't need to display anything here as the stream will update the UI
            console.log('[Möbius Spectacles] Message sent to eligibility v2, awaiting stream updates...');
            
        } else {
            // Default: send to generic chat endpoint
            const response = await fetch('http://localhost:8000/api/spectacles/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: "spectacles_user", // TODO: Get real user
                    messages: [{ role: "user", content: text }], // In real app, send full history
                    stream: false
                })
            });

            const data = await response.json();

            // Remove loading and show response
            removeMessage(loadingId);
            // Extract memory_event_id if available (from FEEDBACK_UI artifact or response)
            const memoryEventId = data.memory_event_id || null;
            addSystemMessage(data.content, false, memoryEventId);
        }

    } catch (error) {
        removeMessage(loadingId);
        addSystemMessage("⚠️ Connection to Nexus failed. Is the backend running?");
        console.error('[Möbius Spectacles] Error sending message:', error);
    }
});

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// Modify addSystemMessage to return ID and allow HTML, and support memory_event_id
function addSystemMessage(text, isHtml = false, memoryEventId = null) {
    const msgDiv = document.createElement('div');
    const id = 'msg-' + Date.now();
    msgDiv.id = id;
    msgDiv.className = 'message system-message';
    msgDiv.setAttribute('data-memory-event-id', memoryEventId || '');
    msgDiv.innerHTML = `
        <div class="avatar">
            <svg viewBox="0 0 24 24" class="icon" style="width:14px;height:14px;"><path d="M12 2L2 7l10 5 10-5-10-5zm0 9l2.5-1.25L12 8.5l-2.5 1.25L12 11zm0 2.5l-5-2.5-5 2.5L12 22l10-8.5-5-2.5-5 2.5z" fill="currentColor"/></svg>
        </div>
        <div class="bubble">${isHtml ? text : text}</div>
    `;
    chatContainer.appendChild(msgDiv);
    
    // Update latest system message
    if (latestSystemMessageId) {
        // Hide feedback on previous message
        const prevMsg = document.getElementById(latestSystemMessageId);
        if (prevMsg) {
            const prevFeedback = prevMsg.querySelector('.feedback-capture');
            if (prevFeedback) {
                prevFeedback.style.display = 'none';
            }
        }
    }
    latestSystemMessageId = id;
    
    // Add feedback capture if memory_event_id is provided
    if (memoryEventId) {
        const bubble = msgDiv.querySelector('.bubble');
        if (bubble) {
            // Load existing feedback
            loadAndRenderFeedback(bubble, memoryEventId, id);
        }
    }
    
    scrollToBottom();
    return id;
}

// Load and render feedback for a message
async function loadAndRenderFeedback(container, memoryEventId, messageId) {
    try {
        // Load existing feedback
        const apiUrl = "http://localhost:8000";
        const feedbackRes = await fetch(`${apiUrl}/api/feedback/${memoryEventId}?user_id=spectacles_user`);
        let existingFeedback = null;
        if (feedbackRes.ok) {
            existingFeedback = await feedbackRes.json();
        }
        
        // Check if this is the latest message
        const isLatest = messageId === latestSystemMessageId;
        
        // Create feedback instance
        if (typeof FeedbackCapture !== 'undefined') {
            // Clean up previous instance for this message if any
            if (feedbackInstances.has(messageId)) {
                feedbackInstances.get(messageId).destroy();
            }
            
            const feedbackInstance = new FeedbackCapture(
                container,
                memoryEventId,
                "spectacles_user",
                isLatest,
                existingFeedback
            );
            feedbackInstances.set(messageId, feedbackInstance);
        }
    } catch (error) {
        console.error("Error loading feedback:", error);
    }
}

input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});

// Listen for email context updates from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[Möbius Spectacles Side Panel] Received message:', request.type);
    
    if (request.type === 'EMAIL_CONTEXT_UPDATE') {
        if (!request.emailData) {
            console.log('[Möbius Spectacles Side Panel] EMAIL_CONTEXT_UPDATE received but emailData is null/undefined');
            return true;
        }
        
        console.log('[Möbius Spectacles Side Panel] Email context update received:', {
            client: request.emailData.client,
            hasSubject: !!request.emailData.subject,
            hasFrom: !!request.emailData.from,
            hasBody: !!request.emailData.body,
            url: request.emailData.url
        });
        
        currentEmailData = request.emailData;
        
        // Auto-switch to EMAIL context if not already
        if (currentContext !== 'EMAIL') {
            console.log('[Möbius Spectacles Side Panel] Switching to EMAIL context');
            setContext('EMAIL');
        } else {
            // Update preview if already in EMAIL context
            console.log('[Möbius Spectacles Side Panel] Already in EMAIL context, updating preview');
            displayEmailPreview(request.emailData);
        }
    }
    return true;
});

// Check for email context on load
console.log('[Möbius Spectacles Side Panel] Checking for existing email context...');
chrome.runtime.sendMessage({ type: 'GET_EMAIL_CONTEXT' }).then(response => {
    if (response && response.emailData) {
        console.log('[Möbius Spectacles Side Panel] Found existing email context');
        currentEmailData = response.emailData;
        setContext('EMAIL');
    } else {
        console.log('[Möbius Spectacles Side Panel] No existing email context found');
    }
}).catch((err) => {
    // No email context available, that's OK
    console.log('[Möbius Spectacles Side Panel] Error getting email context (this is OK):', err);
});

// Demo: Click header to cycle contexts (keep for testing)
document.querySelector('.header').addEventListener('click', () => {
    const modes = Object.keys(CONTEXTS);
    const nextIndex = (modes.indexOf(currentContext) + 1) % modes.length;
    setContext(modes[nextIndex]);
});
