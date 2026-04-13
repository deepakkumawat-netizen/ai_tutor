// All API calls go through here — keeps the API key safe on the backend

const BASE_URL = "/api";

export async function sendChat({ message, grade, subject, requestType, history, reExplain, pendingQuestion }) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, grade, subject, requestType, history, reExplain, pendingQuestion }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Server error");
  }

  return res.json(); // { reply, blocked, blockReason, requestType }
}

export async function getCurriculum(grade) {
  const res = await fetch(`${BASE_URL}/curriculum/${grade}`);
  if (!res.ok) throw new Error("Failed to load curriculum");
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

// ─── YouTube video search ─────────────────────────────────────────────────────
export async function searchYouTubeVideos({ query, grade, subject }) {
  const res = await fetch(`${BASE_URL}/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, grade, subject }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "YouTube search failed");
  }
  return res.json(); // { videos: [...] }
}

