/**
 * Mobius Spectacles - Background Worker
 * Handles extension lifecycle and side panel toggling.
 */

// Open side panel when the action button is clicked
chrome.runtime.onInstalled.addListener(() => {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});
