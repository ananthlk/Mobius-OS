/**
 * Möbius Spectacles - Content Script
 * Extracts email content from Gmail, Outlook, and other email clients
 */

(function() {
    'use strict';
    
    try {
        // Check if chrome.runtime is available (extension context)
        if (typeof chrome === 'undefined' || !chrome || !chrome.runtime || !chrome.runtime.sendMessage) {
            console.error('[Möbius Spectacles] chrome.runtime not available - content script may not be running in extension context');
            return; // Exit early if not in extension context
        }

        console.log('[Möbius Spectacles] Content script loaded');
    } catch (e) {
        console.error('[Möbius Spectacles] Error during initialization:', e);
        return;
    }

    // Detect email client from URL
    function detectEmailClient() {
        const hostname = window.location.hostname;
        if (hostname.includes('mail.google.com')) {
            return 'gmail';
        } else if (hostname.includes('outlook.live.com') || hostname.includes('outlook.office.com')) {
            return 'outlook';
        } else if (hostname.includes('mail.yahoo.com')) {
            return 'yahoo';
        }
        return 'other';
    }

    // Extract email content from Gmail
    function extractGmailEmail() {
        console.log('[Möbius Spectacles] Extracting Gmail email...');
        
        // Gmail selectors (multiple fallbacks for Gmail's dynamic DOM)
        const subjectSelectors = [
            'h2[data-thread-perm-id]',
            'h2[data-thread-id]',
            '.hP',
            'h2.qr',
            'div[data-thread-perm-id] h2',
            '[role="main"] h2'
        ];
        
        const fromSelectors = [
            'span[email]',
            'span[data-email]',
            '.gD',
            '.go',
            '[data-activation-label]',
            'span[title*="@"]'
        ];
        
        const bodySelectors = [
            '.a3s',
            'div[aria-label*="Message Body"]',
            '.ii.gt',
            '[role="main"] div[dir="ltr"]',
            '.Am.Al.editable'
        ];
        
        let subjectEl = null;
        for (const selector of subjectSelectors) {
            subjectEl = document.querySelector(selector);
            if (subjectEl) break;
        }
        
        let fromEl = null;
        for (const selector of fromSelectors) {
            fromEl = document.querySelector(selector);
            if (fromEl) break;
        }
        
        let bodyEl = null;
        for (const selector of bodySelectors) {
            bodyEl = document.querySelector(selector);
            if (bodyEl) break;
        }
        
        const result = {
            subject: subjectEl ? subjectEl.textContent.trim() : '',
            from: fromEl ? (fromEl.getAttribute('email') || fromEl.getAttribute('data-email') || fromEl.textContent.trim()) : '',
            body: bodyEl ? bodyEl.textContent.trim() : ''
        };
        
        console.log('[Möbius Spectacles] Gmail extraction result:', {
            subject: result.subject.substring(0, 50) + (result.subject.length > 50 ? '...' : ''),
            from: result.from.substring(0, 50),
            bodyLength: result.body.length
        });
        
        return result;
    }

    // Extract email content from Outlook
    function extractOutlookEmail() {
        // Outlook selectors
        const subjectEl = document.querySelector('div[aria-label*="Subject"]') ||
                         document.querySelector('.x_hz') ||
                         document.querySelector('h1[role="heading"]');
        
        const fromEl = document.querySelector('button[aria-label*="From"]') ||
                      document.querySelector('.x_7') ||
                      document.querySelector('span[title*="@"]');
        
        const bodyEl = document.querySelector('div[aria-label*="Message body"]') ||
                      document.querySelector('.x_allowTextSelection') ||
                      document.querySelector('[role="textbox"]');
        
        return {
            subject: subjectEl ? subjectEl.textContent.trim() : '',
            from: fromEl ? (fromEl.getAttribute('title') || fromEl.textContent.trim()) : '',
            body: bodyEl ? bodyEl.textContent.trim() : ''
        };
    }

    // Extract email content based on client type
    function extractEmailContent() {
        const client = detectEmailClient();
        console.log('[Möbius Spectacles] Detected email client:', client);
        
        let emailData = {
            subject: '',
            from: '',
            body: ''
        };

        try {
            switch(client) {
                case 'gmail':
                    emailData = extractGmailEmail();
                    break;
                case 'outlook':
                    emailData = extractOutlookEmail();
                    break;
                default:
                    // Generic extraction - try common patterns
                    const subject = document.querySelector('h1, h2, [role="heading"]');
                    const from = document.querySelector('[title*="@"], [email]');
                    const body = document.querySelector('[role="article"], main, .message-body');
                    
                    emailData = {
                        subject: subject ? subject.textContent.trim() : '',
                        from: from ? (from.getAttribute('email') || from.getAttribute('title') || from.textContent.trim()) : '',
                        body: body ? body.textContent.trim() : ''
                    };
                    break;
            }
        } catch (error) {
            console.error('[Möbius Spectacles] Error extracting email content:', error);
        }

        return {
            client: client,
            url: window.location.href,
            ...emailData
        };
    }

    // Send email data to background script
    function sendEmailData() {
        try {
            const emailData = extractEmailContent();
            const client = detectEmailClient();
            
            // Always send EMAIL_DETECTED if we're on an email client, even if extraction failed
            // This allows the extension to at least switch to EMAIL context
            if (client !== 'other') {
                console.log('[Möbius Spectacles] Sending email data to background script:', {
                    client: emailData.client,
                    hasSubject: !!emailData.subject,
                    hasFrom: !!emailData.from,
                    hasBody: !!emailData.body
                });
                
                // Double-check chrome.runtime is available before using it
                if (typeof chrome !== 'undefined' && chrome && chrome.runtime && typeof chrome.runtime.sendMessage === 'function') {
                    chrome.runtime.sendMessage({
                        type: 'EMAIL_DETECTED',
                        emailData: emailData
                    }).then(() => {
                        console.log('[Möbius Spectacles] Email data sent successfully');
                    }).catch(err => {
                        console.error('[Möbius Spectacles] Error sending email data:', err);
                    });
                } else {
                    console.error('[Möbius Spectacles] chrome.runtime.sendMessage not available');
                }
            } else {
                console.log('[Möbius Spectacles] Not an email client, skipping');
            }
        } catch (error) {
            console.error('[Möbius Spectacles] Error in sendEmailData:', error);
        }
    }

    // Monitor for email view changes (Gmail uses SPAs, so we need to observe)
    function setupEmailObserver() {
        // Send initial extraction
        setTimeout(sendEmailData, 1000);

        // Throttle function to prevent excessive calls
        let lastSent = 0;
        const throttleDelay = 2000; // Only send every 2 seconds max
        
        function throttledSendEmailData() {
            const now = Date.now();
            if (now - lastSent > throttleDelay) {
                lastSent = now;
                sendEmailData();
            }
        }

        // Observe DOM changes (for SPAs like Gmail) - but throttle to avoid excessive calls
        const observer = new MutationObserver(() => {
            throttledSendEmailData();
        });

        // Make sure document.body exists before observing
        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        } else {
            console.error('[Möbius Spectacles] document.body not available for observation');
        }

        // Also listen for URL changes (hash changes for SPAs)
        let lastUrl = window.location.href;
        setInterval(() => {
            const currentUrl = window.location.href;
            if (currentUrl !== lastUrl) {
                lastUrl = currentUrl;
                setTimeout(sendEmailData, 500);
            }
        }, 1000);
    }

    // Initialize when DOM is ready
    console.log('[Möbius Spectacles] Content script initialization - readyState:', document.readyState);
    
    function initScript() {
        // Add a visible indicator that the script loaded
        if (document.body) {
            const initIndicator = document.createElement('div');
            initIndicator.style.cssText = 'position:fixed;top:0;left:0;background:red;color:white;padding:4px;z-index:999999;font-size:10px;';
            initIndicator.textContent = 'Möbius Content Script Loaded';
            document.body.appendChild(initIndicator);
            setTimeout(() => {
                if (initIndicator.parentNode) {
                    initIndicator.remove();
                }
            }, 3000);
        }
        setupEmailObserver();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            console.log('[Möbius Spectacles] DOMContentLoaded fired');
            initScript();
        });
    } else {
        console.log('[Möbius Spectacles] DOM already ready, setting up observer immediately');
        // If body isn't ready yet, wait a bit
        if (document.body) {
            initScript();
        } else {
            console.log('[Möbius Spectacles] document.body not ready, waiting...');
            setTimeout(initScript, 500);
        }
    }

    // Scrape current page content (text, links, images)
    function scrapePageContent() {
        console.log('[Möbius Spectacles] Scraping page content...');
        
        try {
            // Remove script and style elements
            const scripts = document.querySelectorAll('script, style, noscript');
            scripts.forEach(el => el.remove());
            
            // Get main content
            const bodyText = document.body ? document.body.innerText : '';
            const title = document.title || '';
            const url = window.location.href;
            
            // Extract links
            const links = Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.textContent.trim(),
                href: a.href
            })).filter(link => link.text && link.href);
            
            // Extract images
            const images = Array.from(document.querySelectorAll('img[src]')).map(img => ({
                alt: img.alt || '',
                src: img.src
            })).filter(img => img.src);
            
            // Extract headings for structure
            const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => ({
                level: h.tagName,
                text: h.textContent.trim()
            })).filter(h => h.text);
            
            return {
                title: title,
                url: url,
                text: bodyText.substring(0, 50000), // Limit to 50k chars
                links: links.slice(0, 100), // Limit to 100 links
                images: images.slice(0, 50), // Limit to 50 images
                headings: headings,
                textLength: bodyText.length,
                scrapedAt: new Date().toISOString()
            };
        } catch (error) {
            console.error('[Möbius Spectacles] Error scraping page content:', error);
            return { error: error.message };
        }
    }
    
    // Scrape full DOM tree structure
    function scrapeDOMTree(element = document.body, maxDepth = 10, currentDepth = 0) {
        if (!element || currentDepth >= maxDepth) {
            return null;
        }
        
        try {
            const nodeInfo = {
                tag: element.tagName ? element.tagName.toLowerCase() : '#text',
                type: element.nodeType,
                depth: currentDepth
            };
            
            // Add attributes for elements
            if (element.attributes && element.attributes.length > 0) {
                nodeInfo.attributes = {};
                for (let attr of element.attributes) {
                    nodeInfo.attributes[attr.name] = attr.value;
                }
            }
            
            // Add text content if it's a text node or leaf element
            if (element.nodeType === Node.TEXT_NODE) {
                const text = element.textContent.trim();
                if (text && text.length > 0 && text.length < 200) {
                    nodeInfo.text = text;
                }
            } else if (element.children.length === 0) {
                const text = element.textContent.trim();
                if (text && text.length > 0 && text.length < 500) {
                    nodeInfo.text = text.substring(0, 500);
                }
            }
            
            // Add class and id if present
            if (element.className && typeof element.className === 'string') {
                nodeInfo.class = element.className;
            }
            if (element.id) {
                nodeInfo.id = element.id;
            }
            
            // Recursively process children (limit to prevent huge trees)
            if (element.children && element.children.length > 0 && currentDepth < maxDepth) {
                const children = [];
                const maxChildren = 50; // Limit children per node
                for (let i = 0; i < Math.min(element.children.length, maxChildren); i++) {
                    const child = scrapeDOMTree(element.children[i], maxDepth, currentDepth + 1);
                    if (child) {
                        children.push(child);
                    }
                }
                if (children.length > 0) {
                    nodeInfo.children = children;
                }
            }
            
            return nodeInfo;
        } catch (error) {
            console.error('[Möbius Spectacles] Error scraping DOM tree:', error);
            return null;
        }
    }
    
    // Scrape full page tree (wrapper function)
    function scrapeFullPageTree() {
        console.log('[Möbius Spectacles] Scraping full DOM tree...');
        
        try {
            const tree = scrapeDOMTree(document.body, 8); // Max depth of 8 levels
            return {
                url: window.location.href,
                title: document.title || '',
                tree: tree,
                scrapedAt: new Date().toISOString()
            };
        } catch (error) {
            console.error('[Möbius Spectacles] Error scraping full page tree:', error);
            return { error: error.message };
        }
    }

    // === FORM MONITORING AND MANIPULATION ===
    
    // Track all forms on the page
    let formMonitor = null;
    let monitoredForms = new Map();
    
    // Generate a reliable CSS selector for an element
    function generateSelector(element) {
        if (element.id) {
            return `#${element.id}`;
        }
        
        if (element.name && element.tagName.toLowerCase() !== 'body' && element.tagName.toLowerCase() !== 'html') {
            return `${element.tagName.toLowerCase()}[name="${element.name}"]`;
        }
        
        // Build path from parent
        const path = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE && current.tagName.toLowerCase() !== 'body') {
            let selector = current.tagName.toLowerCase();
            
            if (current.className && typeof current.className === 'string') {
                const classes = current.className.split(' ').filter(c => c.length > 0).slice(0, 2);
                if (classes.length > 0) {
                    selector += '.' + classes.join('.');
                }
            }
            
            // Add nth-child if needed for uniqueness
            const siblings = Array.from(current.parentNode?.children || [])
                .filter(el => el.tagName === current.tagName);
            if (siblings.length > 1) {
                const index = siblings.indexOf(current) + 1;
                selector += `:nth-child(${index})`;
            }
            
            path.unshift(selector);
            current = current.parentElement;
        }
        
        return path.join(' > ');
    }
    
    // Detect and extract form fields
    function extractFormFields() {
        console.log('[Möbius Spectacles] Extracting form fields...');
        
        const forms = document.querySelectorAll('form');
        const formData = [];
        
        forms.forEach((form, formIndex) => {
            const fields = [];
            
            // Get all input elements
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach((input, index) => {
                const fieldInfo = {
                    index: index,
                    type: input.type || input.tagName.toLowerCase(),
                    name: input.name || '',
                    id: input.id || '',
                    placeholder: input.placeholder || '',
                    value: input.value || '',
                    label: '',
                    required: input.required || false,
                    disabled: input.disabled || false,
                    readonly: input.readOnly || false,
                    className: input.className || '',
                    selector: generateSelector(input)
                };
                
                // Try to find associated label
                if (input.id) {
                    const label = document.querySelector(`label[for="${input.id}"]`);
                    if (label) {
                        fieldInfo.label = label.textContent.trim();
                    }
                } else {
                    // Look for parent label
                    const parentLabel = input.closest('label');
                    if (parentLabel) {
                        fieldInfo.label = parentLabel.textContent.trim();
                    }
                }
                
                // For select elements, get options
                if (input.tagName.toLowerCase() === 'select') {
                    fieldInfo.options = Array.from(input.options).map(opt => ({
                        value: opt.value,
                        text: opt.text,
                        selected: opt.selected
                    }));
                }
                
                fields.push(fieldInfo);
            });
            
            if (fields.length > 0) {
                formData.push({
                    formIndex: formIndex,
                    formId: form.id || '',
                    formName: form.name || '',
                    formAction: form.action || '',
                    formMethod: form.method || 'get',
                    fields: fields,
                    selector: generateSelector(form)
                });
            }
        });
        
        // Also get standalone inputs/textarea/select outside forms
        const standaloneInputs = document.querySelectorAll('input:not(form input), textarea:not(form textarea), select:not(form select)');
        if (standaloneInputs.length > 0) {
            const standaloneFields = Array.from(standaloneInputs).map((input, index) => {
                const fieldInfo = {
                    index: index,
                    type: input.type || input.tagName.toLowerCase(),
                    name: input.name || '',
                    id: input.id || '',
                    placeholder: input.placeholder || '',
                    value: input.value || '',
                    label: '',
                    required: input.required || false,
                    disabled: input.disabled || false,
                    readonly: input.readOnly || false,
                    className: input.className || '',
                    selector: generateSelector(input),
                    standalone: true
                };
                
                // Try to find label
                if (input.id) {
                    const label = document.querySelector(`label[for="${input.id}"]`);
                    if (label) {
                        fieldInfo.label = label.textContent.trim();
                    }
                }
                
                return fieldInfo;
            });
            
            formData.push({
                formIndex: -1,
                standalone: true,
                fields: standaloneFields
            });
        }
        
        console.log('[Möbius Spectacles] Found', formData.length, 'form(s) with', 
                   formData.reduce((sum, f) => sum + f.fields.length, 0), 'total fields');
        
        return {
            url: window.location.href,
            timestamp: new Date().toISOString(),
            forms: formData
        };
    }
    
    // Update a form field value
    function updateFormField(selector, value, options = {}) {
        console.log('[Möbius Spectacles] Updating form field:', selector, '=', value);
        
        try {
            let element = null;
            
            // Try multiple selector strategies
            if (selector.startsWith('#')) {
                element = document.querySelector(selector);
            } else if (selector.startsWith('[') && selector.includes('name=')) {
                element = document.querySelector(selector);
            } else {
                // Try as CSS selector first
                element = document.querySelector(selector);
                
                // If not found, try xpath (for complex selectors)
                if (!element && options.xpath) {
                    const xpathResult = document.evaluate(options.xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    element = xpathResult.singleNodeValue;
                }
            }
            
            if (!element) {
                throw new Error(`Field not found: ${selector}`);
            }
            
            // Check if field is disabled or readonly (unless force option is set)
            if (!options.force) {
                if (element.disabled) {
                    throw new Error(`Field is disabled: ${selector}`);
                }
                if (element.readOnly) {
                    throw new Error(`Field is readonly: ${selector}`);
                }
            }
            
            // Update based on field type
            const tagName = element.tagName.toLowerCase();
            const fieldType = element.type?.toLowerCase();
            
            if (tagName === 'select') {
                // For select, try to match by value or text
                const option = Array.from(element.options).find(opt => 
                    opt.value === value || opt.text === value
                );
                if (option) {
                    element.value = option.value;
                } else {
                    element.value = value;
                }
            } else if (tagName === 'textarea') {
                element.value = value;
            } else if (fieldType === 'checkbox') {
                element.checked = Boolean(value);
            } else if (fieldType === 'radio') {
                // For radio, find the radio button with matching value
                const radioGroup = document.querySelectorAll(`input[name="${element.name}"][type="radio"]`);
                const matchingRadio = Array.from(radioGroup).find(radio => radio.value === value);
                if (matchingRadio) {
                    matchingRadio.checked = true;
                }
            } else {
                // Standard text/email/password/etc input
                element.value = value;
            }
            
            // Trigger events to simulate user input (important for React/Vue/etc)
            const events = ['input', 'change', 'blur'];
            events.forEach(eventType => {
                const event = new Event(eventType, { bubbles: true, cancelable: true });
                element.dispatchEvent(event);
            });
            
            // Also trigger React/Vue specific events
            if (element._valueTracker) {
                element._valueTracker.setValue('');
            }
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (nativeInputValueSetter && tagName === 'input') {
                nativeInputValueSetter.call(element, value);
            }
            
            console.log('[Möbius Spectacles] Successfully updated field:', selector);
            
            return {
                success: true,
                selector: selector,
                oldValue: element.defaultValue || '',
                newValue: value,
                fieldType: fieldType || tagName
            };
            
        } catch (error) {
            console.error('[Möbius Spectacles] Error updating form field:', error);
            return {
                success: false,
                selector: selector,
                error: error.message
            };
        }
    }
    
    // Monitor form changes using MutationObserver
    function startFormMonitoring() {
        if (formMonitor) {
            console.log('[Möbius Spectacles] Form monitoring already active');
            return;
        }
        
        console.log('[Möbius Spectacles] Starting form monitoring...');
        
        // Initial scan
        const initialForms = extractFormFields();
        initialForms.forms.forEach(form => {
            if (form.formIndex >= 0) {
                monitoredForms.set(form.formIndex, form);
            }
        });
        
        // Monitor DOM changes
        formMonitor = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                // Check if forms were added/removed
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Check if a form was added
                            if (node.tagName?.toLowerCase() === 'form') {
                                console.log('[Möbius Spectacles] New form detected');
                                const formData = extractFormFields();
                                chrome.runtime.sendMessage({
                                    type: 'FORM_DETECTED',
                                    formData: formData
                                }).catch(err => console.error('Error sending form data:', err));
                            }
                            
                            // Check if any inputs were added
                            const newInputs = node.querySelectorAll?.('input, textarea, select');
                            if (newInputs && newInputs.length > 0) {
                                console.log('[Möbius Spectacles] New input fields detected');
                                const formData = extractFormFields();
                                chrome.runtime.sendMessage({
                                    type: 'FORM_FIELDS_CHANGED',
                                    formData: formData
                                }).catch(err => console.error('Error sending form change:', err));
                            }
                        }
                    });
                }
                
                // Monitor value changes on inputs
                if (mutation.type === 'attributes' && mutation.target.tagName) {
                    const tag = mutation.target.tagName.toLowerCase();
                    if (['input', 'textarea', 'select'].includes(tag) && mutation.attributeName === 'value') {
                        console.log('[Möbius Spectacles] Form field value changed:', mutation.target);
                    }
                }
            });
        });
        
        // Start observing
        formMonitor.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['value', 'checked', 'selected']
        });
        
        console.log('[Möbius Spectacles] Form monitoring active');
    }
    
    function stopFormMonitoring() {
        if (formMonitor) {
            formMonitor.disconnect();
            formMonitor = null;
            monitoredForms.clear();
            console.log('[Möbius Spectacles] Form monitoring stopped');
        }
    }

    // Listen for requests from background script
    if (chrome.runtime && chrome.runtime.onMessage) {
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.type === 'EXTRACT_EMAIL') {
                console.log('[Möbius Spectacles] Received EXTRACT_EMAIL request from background');
                const emailData = extractEmailContent();
                sendResponse({ success: true, emailData: emailData });
                return true; // Keep channel open for async response
            } else if (request.type === 'SCRAPE_PAGE') {
                console.log('[Möbius Spectacles] Received SCRAPE_PAGE request');
                const pageData = scrapePageContent();
                sendResponse({ success: true, pageData: pageData });
                return true;
            } else if (request.type === 'SCRAPE_DOM_TREE') {
                console.log('[Möbius Spectacles] Received SCRAPE_DOM_TREE request');
                const treeData = scrapeFullPageTree();
                sendResponse({ success: true, treeData: treeData });
                return true;
            } else if (request.type === 'EXTRACT_FORMS') {
                console.log('[Möbius Spectacles] Received EXTRACT_FORMS request');
                const formData = extractFormFields();
                sendResponse({ success: true, formData: formData });
                return true;
            } else if (request.type === 'UPDATE_FORM_FIELD') {
                console.log('[Möbius Spectacles] Received UPDATE_FORM_FIELD request');
                const result = updateFormField(request.selector, request.value, request.options || {});
                sendResponse({ success: result.success, result: result });
                return true;
            } else if (request.type === 'START_FORM_MONITORING') {
                console.log('[Möbius Spectacles] Received START_FORM_MONITORING request');
                startFormMonitoring();
                sendResponse({ success: true, message: 'Form monitoring started' });
                return true;
            } else if (request.type === 'STOP_FORM_MONITORING') {
                console.log('[Möbius Spectacles] Received STOP_FORM_MONITORING request');
                stopFormMonitoring();
                sendResponse({ success: true, message: 'Form monitoring stopped' });
                return true;
            }
            return false;
        });
    } else {
        console.error('[Möbius Spectacles] chrome.runtime.onMessage not available');
    }

    // Auto-start form monitoring on secure pages (LinkedIn, etc.)
    if (window.location.hostname.includes('linkedin.com') || 
        window.location.hostname.includes('facebook.com') ||
        window.location.protocol === 'https:') {
        console.log('[Möbius Spectacles] Secure page detected, starting form monitoring...');
        setTimeout(() => {
            startFormMonitoring();
        }, 2000); // Wait 2 seconds for page to load
    }

})();

