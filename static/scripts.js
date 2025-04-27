// Part 1: Browser + Device Detection
function isIphone() {
    return /iPhone|iPad|iPod/i.test(navigator.userAgent);
  }
  
  function isChromeOrFirefox() {
    return /CriOS|FxiOS/i.test(navigator.userAgent); 
    // CriOS = Chrome on iOS, FxiOS = Firefox on iOS
  }
  
  window.addEventListener('DOMContentLoaded', () => {
    const micButton = document.getElementById('mic-button'); // replace with your mic button ID
  
    if (isIphone() && isChromeOrFirefox()) {
      if (micButton) {
        micButton.disabled = true; 
        micButton.style.opacity = 0.5; // visually show disabled
      }
      alert("Voice input is not supported on Chrome or Firefox for iPhone. Please use Safari or Edge.");
    }
  });
  
  // Part 2: Speech Recognition Handling
 
  if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
  
    recognition.onresult = function(event) {
      const transcript = event.results[0][0].transcript;
      document.getElementById('user-input').value = transcript; // replace with your input field ID
  
      // Part 3: After finishing voice typing, show reminder
      setTimeout(() => {
        alert("Please tap the Send button to hear the bot’s response.");
      }, 100); 
    };
  
    recognition.onerror = function(event) {
      console.error("Speech recognition error:", event.error);
      alert("Speech recognition error occurred. Please try again.");
    };
  }
  
  // Attach recognition to your mic button
  const micButton = document.getElementById('mic-button');
  if (micButton && recognition) {
    micButton.addEventListener('click', () => {
      recognition.start();
    });
  }
  