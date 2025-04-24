let recognition;

function typeUserMessage(text, callback) {
  if (!text || text.trim() === "") return;
  const chatBox = document.getElementById("chat-box");
  const userMsg = document.createElement("p");
  const userSpan = document.createElement("span");
  userMsg.innerHTML = `You (spoken): `;
  userSpan.id = 'user-typing';
  userMsg.appendChild(userSpan);
  chatBox.appendChild(userMsg);
  let i = 0;
  const interval = setInterval(() => {
    if (i < text.length) {
      userSpan.textContent += text.charAt(i);
      i++;
    } else {
      clearInterval(interval);
      if (callback) callback();
    }
    chatBox.scrollTop = chatBox.scrollHeight;
  }, 30);
}

function typeReply(text, callback) {
  if (!text || text.trim() === "") return;
  const chatBox = document.getElementById("chat-box");
  const replyParagraph = document.createElement("p");
  const replySpan = document.createElement("span");
  replyParagraph.innerHTML = `DrPsychBot: `;
  replySpan.id = 'typing';
  replyParagraph.appendChild(replySpan);
  chatBox.appendChild(replyParagraph);
  let i = 0;
  const interval = setInterval(() => {
    if (i < text.length) {
      replySpan.textContent += text.charAt(i);
      i++;
    } else {
      clearInterval(interval);
      chatBox.scrollTop = chatBox.scrollHeight;
      if (callback) callback();
    }
  }, 30);
}

function sendMessage(fromTyped = false) {
  const input = document.getElementById("user-input").value.trim();
  if (!input) return;
  document.getElementById("status").innerText = "Processing...";
  if (fromTyped) {
    typeUserTyped(input);
  }
  fetch("/voice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: input })
  })
    .then(res => res.json())
    .then(data => {
      const reply = data.text;
      const audioUrl = data.audio_url;
      if (reply) {
        typeReply(reply);
        if (audioUrl) {
          const audio = new Audio(audioUrl);
          audio.play();
          audio.onended = () => {
            startListening();
          };
        }
      }
    })
    .catch(err => {
      console.error("Error:", err);
      typeReply("Sorry, something went wrong.", () => startListening());
    });
  document.getElementById("user-input").value = "";
}

function typeUserTyped(text) {
  const chatBox = document.getElementById("chat-box");
  const userTyped = document.createElement("p");
  userTyped.innerHTML = `You: ${text}`;
  chatBox.appendChild(userTyped);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function startListening() {
  if (recognition) {
    recognition.stop();
  }
  recognition = new webkitSpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  document.getElementById("status").innerText = "🎤 Listening...";
  recognition.onresult = function(event) {
    const spokenText = event.results[0][0].transcript;
    if (spokenText.trim()) {
      typeUserMessage(spokenText, () => {
        document.getElementById("user-input").value = spokenText;
        sendMessage();
      });
    }
  };
  recognition.onerror = function(event) {
    console.error("Speech recognition error:", event.error);
    document.getElementById("status").innerText = "🎤 Error. Tap mic to retry.";
  };
  recognition.onend = function() {
    document.getElementById("status").innerText = "";
  };
  recognition.start();
}