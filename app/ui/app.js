const form = document.getElementById("ask-form");
const questionInput = document.getElementById("question");
const submitButton = document.getElementById("submit-btn");
const landingView = document.getElementById("landing-view");
const chatThread = document.getElementById("chat-thread");
const promptList = document.getElementById("prompt-list");
const chatMain = document.getElementById("chat-main");

let isFirstMessage = true;

function smoothScrollToBottom() {
  setTimeout(() => {
    chatMain.scrollTo({ top: chatMain.scrollHeight, behavior: 'smooth' });
  }, 50);
}

function appendUserMessage(text) {
  if (isFirstMessage) {
    landingView.style.display = 'none';
    chatThread.style.display = 'flex';
    isFirstMessage = false;
  }
  
  const template = document.getElementById('user-msg-template');
  const clone = template.content.cloneNode(true);
  clone.querySelector('.msg-content').textContent = text;
  chatThread.appendChild(clone);
  
  smoothScrollToBottom();
}

function appendLoadingIndicator() {
  const div = document.createElement('div');
  div.className = 'msg-bubble ai-msg-container loading-msg';
  div.innerHTML = `
    <div class="ai-avatar">✨</div>
    <div class="msg-content ai-blob loading-dots">
      <span>.</span><span>.</span><span>.</span>
    </div>
  `;
  chatThread.appendChild(div);
  smoothScrollToBottom();
  return div;
}

function appendAIMessage(payload, loadingNode) {
  loadingNode.remove();
  
  const template = document.getElementById('ai-msg-template');
  const clone = template.content.cloneNode(true);
  
  clone.querySelector('.answer-text').textContent = payload.answer || "No answer returned.";
  
  const confValue = typeof payload.confidence === "number" ? (payload.confidence * 100).toFixed(0) : "-";
  clone.querySelector('.confidence-chip').textContent = `Confidence: ${confValue}%`;
  
  const sectionsListEl = clone.querySelector('.sections-chip-list');
  if (payload.applicable_sections && payload.applicable_sections.length > 0) {
    payload.applicable_sections.forEach(sec => {
      const sp = document.createElement('span');
      sp.className = 'sec-chip';
      sp.textContent = sec;
      sectionsListEl.appendChild(sp);
    });
  } else {
    const sp = document.createElement('span');
    sp.className = 'sec-chip empty';
    sp.textContent = "No Found Sections";
    sectionsListEl.appendChild(sp);
  }
  
  clone.querySelector('.disclaimer-text').textContent = payload.note || "No note returned.";
  
  chatThread.appendChild(clone);
  smoothScrollToBottom();
}

function appendError(message, loadingNode) {
  loadingNode.remove();
  
  const div = document.createElement('div');
  div.className = 'msg-bubble ai-msg-container error-msg';
  div.innerHTML = `
    <div class="ai-avatar" style="background:#E11D48;">🚨</div>
    <div class="msg-content ai-blob error-text">
       ${message}
    </div>
  `;
  chatThread.appendChild(div);
  smoothScrollToBottom();
}

async function submitQuestion(question) {
  appendUserMessage(question);
  questionInput.value = "";
  submitButton.disabled = true;
  
  const loadingNode = appendLoadingIndicator();

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    const data = await response.json();
    if (!response.ok) {
      appendError(data.detail || "Request failed.", loadingNode);
      return;
    }
    
    appendAIMessage(data, loadingNode);
  } catch (error) {
    appendError("Network error while contacting the API.", loadingNode);
  } finally {
    submitButton.disabled = false;
    questionInput.focus();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  await submitQuestion(question);
});

promptList.addEventListener("click", (event) => {
  const target = event.target.closest('.prompt-chip');
  if (!target) return;
  const spans = target.querySelectorAll('span');
  const text = spans[1] ? spans[1].textContent : target.textContent.trim();
  
  // Directly submit the question
  submitQuestion(text);
});
