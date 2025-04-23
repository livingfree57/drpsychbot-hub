let lastBotResponse = "";

function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value;
  if (!message) return;

  const chatBox = document.getElementById("chat-box");
  chatBox.innerHTML += `<p><strong>You:</strong> ${message}</p>`;

  fetch(`/message?message=${encodeURIComponent(message)}`)
    .then(response => response.json())
    .then(data => {
      const reply = data.response;
      lastBotResponse = reply;
      chatBox.innerHTML += `<p><strong>DrPsychBot:</strong> ${reply}</p>`;
      chatBox.scrollTop = chatBox.scrollHeight;
    });
  fetch("/list-bots")


  input.value = "";
}

function speakLastResponse() {
  if (!lastBotResponse) return;
  const utterance = new SpeechSynthesisUtterance(lastBotResponse);
  speechSynthesis.speak(utterance);
}
