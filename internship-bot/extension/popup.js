const API_URL = "http://localhost:8000/api/session/upload";
const KEY_URL = "http://localhost:8000/api/session/key";

async function getApiKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["applyflowApiKey"], (result) => {
      let key = result.applyflowApiKey;
      if (!key) {
        key = prompt("Please enter your Dashboard API Key to continue:");
        if (key) {
          chrome.storage.local.set({ applyflowApiKey: key });
        }
      }
      resolve(key);
    });
  });
}

async function fetchSecretKey(apiKey) {
  const res = await fetch(KEY_URL, {
    headers: { "X-API-Key": apiKey }
  });
  if (!res.ok) throw new Error("Failed to fetch secret key. Is the API Key correct?");
  const data = await res.json();
  return data.key;
}

async function encryptData(dataStr, secretKey) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(secretKey),
    { name: "PBKDF2" },
    false,
    ["deriveBits", "deriveKey"]
  );
  
  // Use a static salt for MVP simplicity, in production this should be random
  const salt = enc.encode("applyflow_salt");
  const key = await crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: salt,
      iterations: 100000,
      hash: "SHA-256"
    },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"]
  );

  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv },
    key,
    enc.encode(dataStr)
  );

  return {
    ciphertext: Array.from(new Uint8Array(encrypted)),
    iv: Array.from(iv)
  };
}

function showStatus(message, type = "") {
  const statusEl = document.getElementById("status");
  statusEl.textContent = message;
  statusEl.className = type;
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".capture-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const button = e.target;
      const platformDiv = button.closest(".platform");
      const platformId = platformDiv.dataset.id;
      const domain = button.dataset.domain;
      const targetUrl = button.dataset.url;
      
      button.disabled = true;
      button.textContent = "Capturing...";
      showStatus(`Capturing ${platformId} session...`);

      try {
        // Get active tab to check if we are on the right domain
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (!tab || !tab.url.includes(domain.replace(/^\./, ""))) {
          throw new Error(`Please navigate to ${targetUrl} first.`);
        }

        // Get all cookies for the domain
        const cookies = await chrome.cookies.getAll({ domain: domain });
        
        // Get localStorage by executing script in the active tab
        const [{ result: localStorageData }] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            const data = {};
            for (let i = 0; i < localStorage.length; i++) {
              const key = localStorage.key(i);
              data[key] = localStorage.getItem(key);
            }
            return data;
          }
        });

        const sessionData = {
          cookies: cookies,
          localStorage: localStorageData,
          capturedAt: new Date().toISOString(),
          domain: domain
        };

        const apiKey = await getApiKey();
        if (!apiKey) throw new Error("API Key is required to capture sessions.");

        const secretKey = await fetchSecretKey(apiKey);
        const { ciphertext, iv } = await encryptData(JSON.stringify(sessionData), secretKey);

        const response = await fetch(API_URL, {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "X-API-Key": apiKey
          },
          body: JSON.stringify({
            platform: platformId,
            encrypted_blob: ciphertext,
            iv: iv
          })
        });

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        showStatus(`Successfully captured ${platformId}!`, "success");
        button.textContent = "Done";
      } catch (err) {
        showStatus(`Error: ${err.message}`, "error");
        button.textContent = "Capture";
        button.disabled = false;
      }
    });
  });
});