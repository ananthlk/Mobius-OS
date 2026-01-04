/**
 * Möbius Spectacles - Background Worker
 * Handles extension lifecycle and side panel toggling.
 */

console.log('[Möbius Spectacles] Background script loaded');

// Open side panel when the action button is clicked
chrome.runtime.onInstalled.addListener(() => {
    console.log('[Möbius Spectacles] Extension installed/updated');
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// Store current email context
let currentEmailContext = null;

// Listen for messages from content script and side panel
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[Möbius Spectacles Background] Received message:', request.type);
    
    if (request.type === 'EMAIL_DETECTED') {
        console.log('[Möbius Spectacles Background] Email detected:', {
            client: request.emailData?.client,
            hasSubject: !!request.emailData?.subject,
            hasFrom: !!request.emailData?.from,
            hasBody: !!request.emailData?.body
        });
        
        currentEmailContext = request.emailData;
        
        // Forward to side panel if open
        chrome.runtime.sendMessage({
            type: 'EMAIL_CONTEXT_UPDATE',
            emailData: request.emailData
        }).then(() => {
            console.log('[Möbius Spectacles Background] Email context forwarded to side panel');
        }).catch(() => {
            // Side panel might not be open, that's OK
            console.log('[Möbius Spectacles Background] Side panel not open (this is OK)');
        });
        
        sendResponse({ success: true });
        return true;
    } else if (request.type === 'GET_EMAIL_CONTEXT') {
        // Handle request from side panel for current email context
        console.log('[Möbius Spectacles Background] GET_EMAIL_CONTEXT requested');
        sendResponse({ emailData: currentEmailContext });
        return true;
    } else if (request.type === 'REQUEST_EXTRACTION') {
        // Request extraction from content script in active tab
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].url) {
                const emailDomains = ['mail.google.com', 'outlook.live.com', 'outlook.office.com', 'mail.yahoo.com'];
                const isEmailClient = emailDomains.some(domain => tabs[0].url.includes(domain));
                
                if (isEmailClient) {
                    chrome.tabs.sendMessage(tabs[0].id, { type: 'EXTRACT_EMAIL' }, (response) => {
                        if (chrome.runtime.lastError) {
                            console.error('[Möbius Spectacles Background] Error sending message to content script:', chrome.runtime.lastError.message);
                            console.log('[Möbius Spectacles Background] Make sure you have Gmail open and the page is fully loaded');
                            return;
                        }
                        
                        if (response && response.success && response.emailData) {
                            console.log('[Möbius Spectacles Background] Manual extraction successful');
                            currentEmailContext = response.emailData;
                            
                            // Forward to side panel
                            chrome.runtime.sendMessage({
                                type: 'EMAIL_CONTEXT_UPDATE',
                                emailData: response.emailData
                            }).catch(() => {
                                console.log('[Möbius Spectacles Background] Side panel not open');
                            });
                        } else {
                            console.log('[Möbius Spectacles Background] Extraction response:', response);
                        }
                    });
                } else {
                    console.log('[Möbius Spectacles Background] Current tab is not an email client');
                }
            }
        });
        sendResponse({ success: true });
        return true;
    }
    return false;
});

// Monitor tab updates to detect email clients
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        const emailDomains = [
            'mail.google.com',
            'outlook.live.com',
            'outlook.office.com',
            'mail.yahoo.com'
        ];
        
        const isEmailClient = emailDomains.some(domain => tab.url.includes(domain));
        
        if (isEmailClient) {
            // Content script will extract and send email data
            // Reset context when navigating to email client
            currentEmailContext = null;
        }
    }
});
