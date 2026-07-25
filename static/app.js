// State constants
const STATE_STANDBY = 'standby';
const STATE_LISTENING = 'listening';
const STATE_THINKING = 'thinking';
const STATE_SPEAKING = 'speaking';
const STATE_ERROR = 'error';

let currentState = STATE_STANDBY;
let recognition = null;
let isVoiceActive = false;
let currentUtterance = null;

// UI Elements
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const reactorCore = document.getElementById('reactor-core');
const reactorStateText = document.getElementById('reactor-state-text');
const voiceToggleBtn = document.getElementById('voice-toggle-btn');
const chatHistory = document.getElementById('chat-history');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const ttsToggle = document.getElementById('tts-toggle');
const continuousToggle = document.getElementById('continuous-toggle');
const diagnosticsLog = document.getElementById('diagnostics-log');

// Log to diagnostics feed
function logToDiagnostics(type, message) {
  const time = new Date().toTimeString().split(' ')[0];
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.innerHTML = `<span class="log-timestamp">[${time}]</span> ${message}`;
  diagnosticsLog.appendChild(entry);
  diagnosticsLog.scrollTop = diagnosticsLog.scrollHeight;
}

// Update reactor and header status UI
function updateUIState(state, customLabel = '') {
  currentState = state;
  
  // Clear classes
  reactorCore.classList.remove('listening', 'thinking', 'speaking', 'error');
  statusDot.classList.remove('disconnected', 'thinking');
  
  switch(state) {
    case STATE_LISTENING:
      reactorCore.classList.add('listening');
      statusText.innerText = 'LISTENING CORE ACTIVE';
      reactorStateText.innerText = 'LISTENING...';
      reactorStateText.style.color = 'var(--neon-cyan)';
      break;
    case STATE_THINKING:
      reactorCore.classList.add('thinking');
      statusDot.classList.add('thinking');
      statusText.innerText = 'NEURAL THINKING';
      reactorStateText.innerText = 'THINKING...';
      reactorStateText.style.color = 'var(--neon-gold)';
      break;
    case STATE_SPEAKING:
      reactorCore.classList.add('speaking');
      statusText.innerText = 'VOCAL OUTPUT ACTIVE';
      reactorStateText.innerText = 'SPEAKING';
      reactorStateText.style.color = 'var(--neon-cyan)';
      break;
    case STATE_ERROR:
      reactorCore.classList.add('error');
      statusDot.classList.add('disconnected');
      statusText.innerText = 'SYSTEM ERROR';
      reactorStateText.innerText = 'CORE FAULT';
      reactorStateText.style.color = 'var(--neon-red)';
      break;
    case STATE_STANDBY:
    default:
      statusText.innerText = 'SYSTEM STANDBY';
      reactorStateText.innerText = customLabel || 'TAP TO ACTIVATE';
      reactorStateText.style.color = 'var(--text-secondary)';
      break;
  }
}

// Add message to conversation container
function addMessage(sender, text) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender.toLowerCase()}`;
  
  const labelSpan = document.createElement('span');
  labelSpan.className = 'msg-label';
  labelSpan.innerText = sender.toUpperCase();
  
  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = 'msg-bubble';
  bubbleDiv.innerText = text;
  
  msgDiv.appendChild(labelSpan);
  msgDiv.appendChild(bubbleDiv);
  chatHistory.appendChild(msgDiv);
  
  // Auto-scroll
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Clean text of markdown, bullet points, and special symbols for natural voice synthesis
function cleanTextForSpeech(text) {
  let clean = text;
  
  // Remove markdown headers (e.g. ### Header)
  clean = clean.replace(/#+\s+/g, '');
  
  // Remove bold/italic markup (e.g. **bold**, *italic*, _italic_)
  clean = clean.replace(/\*\*|__|\*|_/g, '');
  
  // Remove inline links [text](url) -> keep only text
  clean = clean.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  
  // Remove list indicators at the start of lines (e.g. - item, * item, 1. item)
  clean = clean.replace(/^\s*[-*+]\s+/gm, '');
  clean = clean.replace(/^\s*\d+\.\s+/gm, '');
  
  // Replace common symbols with spoken words
  clean = clean.replace(/%/g, ' percent');
  clean = clean.replace(/\$/g, ' dollars ');
  
  // Replace multiple spaces or newlines with a single space
  clean = clean.replace(/\s+/g, ' ').trim();
  
  return clean;
}

// Speak text using browser Speech Synthesis
function speakText(text) {
  if (!ttsToggle.checked) {
    if (continuousToggle.checked && isVoiceActive) {
      startSpeechRecognition();
    } else {
      updateUIState(STATE_STANDBY);
    }
    return;
  }

  // Cancel any active speech
  window.speechSynthesis.cancel();
  
  // Intercept text to replace spelling with pronunciation and clean markdown
  let spokenText = cleanTextForSpeech(text);
  spokenText = spokenText.replace(/Tsakane/gi, "Sekani");
  currentUtterance = new SpeechSynthesisUtterance(spokenText);
  
  // Find selected voice
  const selectedVoiceName = voiceSelect.value;
  if (selectedVoiceName && voices.length > 0) {
    const voice = voices.find(v => v.name === selectedVoiceName);
    if (voice) {
      currentUtterance.voice = voice;
    }
  } else {
    // Fallback: search for premium/natural female voice default
    const premiumKeywords = ['natural', 'online', 'google', 'enhanced'];
    const femaleKeywords = ['susan', 'samantha', 'zira', 'hazel', 'victoria', 'karen', 'moira', 'tessa', 'female'];
    let selectedVoice = null;
    
    // 1. Try to find a premium/natural female voice
    for (let pKw of premiumKeywords) {
      selectedVoice = voices.find(v => {
        const name = v.name.toLowerCase();
        return name.includes(pKw) && femaleKeywords.some(fKw => name.includes(fKw)) && v.lang.startsWith('en');
      });
      if (selectedVoice) break;
    }
    
    // 2. Try to find any female voice
    if (!selectedVoice) {
      for (let fKw of femaleKeywords) {
        selectedVoice = voices.find(v => v.name.toLowerCase().includes(fKw) && v.lang.startsWith('en'));
        if (selectedVoice) break;
      }
    }
    
    // 3. Fallback to any premium/natural English voice
    if (!selectedVoice) {
      for (let pKw of premiumKeywords) {
        selectedVoice = voices.find(v => v.name.toLowerCase().includes(pKw) && v.lang.startsWith('en'));
        if (selectedVoice) break;
      }
    }
    
    // 4. Ultimate fallback to first English voice
    if (!selectedVoice && voices.length > 0) {
      selectedVoice = voices.find(v => v.lang.startsWith('en'));
    }
    
    if (selectedVoice) {
      currentUtterance.voice = selectedVoice;
    }
  }
  
  currentUtterance.rate = 1.1; // slightly faster like FRIDAY
  currentUtterance.pitch = 1.0;

  currentUtterance.onstart = () => {
    logToDiagnostics('info', 'Vocal synthesis core active.');
    updateUIState(STATE_SPEAKING);
  };
  
  currentUtterance.onend = () => {
    logToDiagnostics('info', 'Vocal synthesis completed.');
    currentUtterance = null;
    
    if (isVoiceActive) {
      // Small pause before resuming listening
      setTimeout(() => {
        if (currentState !== STATE_THINKING) {
          startSpeechRecognition();
        }
      }, 500);
    } else {
      updateUIState(STATE_STANDBY);
    }
  };
  
  currentUtterance.onerror = (e) => {
    logToDiagnostics('error', `Speech synthesis error: ${e.error}`);
    updateUIState(STATE_STANDBY);
  };
  
  window.speechSynthesis.speak(currentUtterance);
}

// Send user message to the local FastAPI backend
async function sendToBackend(message) {
  // If user spoke/typed exit, turn off voice
  if (message.trim().toLowerCase() === 'exit') {
    stopVoiceLoop();
    addMessage('Friday', 'Logging off. Have a good night, boss.');
    speakText('Logging off. Have a good night, boss.');
    return;
  }

  updateUIState(STATE_THINKING);
  logToDiagnostics('info', `Sending neural request: "${message}"`);
  
  try {
    const modelSelect = document.getElementById('model-select');
    const provider = modelSelect ? modelSelect.value : null;

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        message: message,
        provider: provider
      })
    });
    
    if (!response.ok) {
      let errorMsg = `HTTP error ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.detail) {
          errorMsg = errorJson.detail;
        }
      } catch (e) {
        // ignore
      }
      throw new Error(errorMsg);
    }
    
    const data = await response.json();
    
    // Add diagnostics logs if backend returned them
    if (data.logs && Array.isArray(data.logs)) {
      data.logs.forEach(log => {
        logToDiagnostics(log.type || 'info', log.message);
      });
    }
    
    addMessage('Friday', data.response);
    speakText(data.response);
    
  } catch (error) {
    logToDiagnostics('error', `Neural link failed: ${error.message}`);
    updateUIState(STATE_ERROR);
    addMessage('Friday', 'Apologies boss, but my connection is fluctuating. Please verify the backend status.');
    speakText('Apologies boss, but my connection is fluctuating.');
  }
}

// Setup and start Web Speech Recognition
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    logToDiagnostics('error', 'Web Speech Recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
    updateUIState(STATE_ERROR, 'STT NOT SUPPORTED');
    voiceToggleBtn.disabled = true;
    return false;
  }
  
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  
  recognition.onstart = () => {
    logToDiagnostics('info', 'Microphone audio feed online.');
    updateUIState(STATE_LISTENING);
  };
  
  recognition.onresult = (event) => {
    const speechToText = event.results[0][0].transcript;
    logToDiagnostics('info', `Voice input transcribed: "${speechToText}"`);
    addMessage('Boss', speechToText);
    
    // Send to Friday agent
    sendToBackend(speechToText);
  };
  
  recognition.onerror = (event) => {
    // Ignore no-speech errors in continuous mode to prevent spamming logs
    if (event.error === 'no-speech') {
      if (continuousToggle.checked && isVoiceActive) {
        // Auto-restart
        return;
      }
      logToDiagnostics('info', 'No voice detected. Core standby.');
      updateUIState(STATE_STANDBY);
      return;
    }
    
    logToDiagnostics('error', `Mic error: ${event.error}`);
    updateUIState(STATE_STANDBY);
  };
  
  recognition.onend = () => {
    logToDiagnostics('info', 'Microphone feed closed.');
    
    // If voice is active and we are not thinking or speaking, restart listening
    if (isVoiceActive && continuousToggle.checked && currentState === STATE_LISTENING) {
      startSpeechRecognition();
    } else if (currentState === STATE_LISTENING) {
      isVoiceActive = false;
      voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Listening';
      voiceToggleBtn.classList.remove('active');
      updateUIState(STATE_STANDBY);
    }
  };
  
  return true;
}

function startSpeechRecognition() {
  if (!recognition) return;
  
  // Make sure speech synthesis is quiet before we start listening
  if (window.speechSynthesis.speaking) {
    return;
  }
  
  try {
    recognition.start();
  } catch (e) {
    // Already running, ignore
  }
}

let greetingSpoken = false;
let greetingText = "Greetings boss, you're up late at night today. What are you up to?";

function startVoiceLoop() {
  isVoiceActive = true;
  voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i> Stop Listening';
  voiceToggleBtn.classList.add('active');
  
  if (!greetingSpoken) {
    greetingSpoken = true;
    speakText(greetingText);
  } else {
    startSpeechRecognition();
  }
}

function stopVoiceLoop() {
  isVoiceActive = false;
  voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Listening';
  voiceToggleBtn.classList.remove('active');
  
  if (recognition) {
    recognition.abort();
  }
  window.speechSynthesis.cancel();
  updateUIState(STATE_STANDBY);
  greetingSpoken = false;
}

// UI Event Listeners
voiceToggleBtn.addEventListener('click', () => {
  if (isVoiceActive) {
    stopVoiceLoop();
    logToDiagnostics('info', 'Voice Core deactivated manually.');
  } else {
    logToDiagnostics('info', 'Initializing Voice Core...');
    startVoiceLoop();
  }
});

reactorCore.addEventListener('click', () => {
  // Trigger click same as button
  voiceToggleBtn.click();
});

chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  
  addMessage('Boss', text);
  chatInput.value = '';
  
  // Send text to Friday
  sendToBackend(text);
});

const voiceSelect = document.getElementById('voice-select');
let voices = [];

function populateVoiceList() {
  if (typeof speechSynthesis === 'undefined') {
    return;
  }
  
  voices = speechSynthesis.getVoices();
  console.log("F.R.I.D.A.Y. Speech Core - All detected voices:", voices.map(v => v.name));
  logToDiagnostics('info', `Vocal database loaded: ${voices.length} voices detected.`);
  const selectedName = voiceSelect.value;
  voiceSelect.innerHTML = '';
  
  // Filter for English voices first, but fall back to all if none
  let englishVoices = voices.filter(v => v.lang.startsWith('en'));
  let listToUse = englishVoices.length > 0 ? englishVoices : voices;
  
  // Filter ONLY for Ava, Sonia, Jenny, and Aria
  const targetVoices = ['ava', 'sonia', 'jenny', 'aria'];
  let filteredVoices = listToUse.filter(voice => {
    const name = voice.name.toLowerCase();
    return targetVoices.some(target => name.includes(target));
  });
  
  // Fallback to the original list only if none of these natural voices are loaded/registered yet
  let finalList = filteredVoices.length > 0 ? filteredVoices : listToUse;
  
  // Sort them so they appear in your preferred target order (Ava, Sonia, Jenny, Aria)
  finalList.sort((a, b) => {
    const aName = a.name.toLowerCase();
    const bName = b.name.toLowerCase();
    
    const aIndex = targetVoices.findIndex(target => aName.includes(target));
    const bIndex = targetVoices.findIndex(target => bName.includes(target));
    
    return aIndex - bIndex;
  });

  finalList.forEach((voice) => {
    const option = document.createElement('option');
    option.textContent = `${voice.name} (${voice.lang})`;
    option.value = voice.name;
    
    // Auto-select the first voice on startup if nothing was selected previously
    if (!selectedName && finalList.length > 0) {
      if (voice.name === finalList[0].name) {
        option.selected = true;
      }
    } else if (voice.name === selectedName) {
      option.selected = true;
    }
    
    voiceSelect.appendChild(option);
  });
}

async function initializeGreeting() {
  try {
    const response = await fetch('/api/history');
    if (response.ok) {
      const data = await response.json();
      const history = data.history;
      
      // Clear current placeholder chat history
      chatHistory.innerHTML = '';
      
      // Render all messages from database history
      history.forEach(msg => {
        if (msg.role === 'user') {
          addMessage('Boss', msg.content);
        } else if (msg.role === 'assistant') {
          addMessage('Friday', msg.content);
        }
      });
      
      if (history.length === 1 && history[0].role === 'assistant') {
        greetingText = history[0].content;
        greetingSpoken = false;
      } else {
        // Conversation has already progressed, do not repeat greeting on start listening
        greetingSpoken = true;
      }
      
      logToDiagnostics('info', `Neural link synchronized. Chat history restored with ${history.length} messages.`);
    }
  } catch (e) {
    logToDiagnostics('error', `Failed to sync history with backend: ${e.message}`);
  }
}

// Initialize Speech
window.addEventListener('DOMContentLoaded', () => {
  setupSpeechRecognition();
  populateVoiceList();
  initializeGreeting();
  
  // Make sure voices are loaded (chrome loading voice list delay)
  if (typeof speechSynthesis !== 'undefined' && speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = () => {
      populateVoiceList();
      logToDiagnostics('info', 'Vocal synthesis database loaded.');
    };
  }
});
