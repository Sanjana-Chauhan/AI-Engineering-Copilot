"use client";

import { useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");

  async function sendMessage() {
    if (!message.trim()) {
      return;
    }

    const response = await fetch(
      "http://127.0.0.1:8000/api/chat?message=" +
        encodeURIComponent(message),
      {
        method: "POST",
      }
    );

    const data = await response.json();

    setResponse(data.message);
  }

  return (
    <main className="min-h-screen p-10">
      <h1 className="text-3xl font-bold">
        Engineering Copilot
      </h1>

      <div className="mt-8 flex gap-3">
        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask something..."
          className="border p-3"
        />

        <button
          onClick={sendMessage}
          className="border px-4 py-2"
        >
          Send
        </button>
      </div>

      {response && (
        <div className="mt-8">
          <h2 className="font-semibold">Response</h2>
          <p className="mt-2">{response}</p>
        </div>
      )}
    </main>
  );
}