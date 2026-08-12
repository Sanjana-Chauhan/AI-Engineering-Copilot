"use client";

import { useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

type RepositorySource = "local" | "github";

interface Source {
  file_path: string;
  language: string;
  start_line: number;
  end_line: number;
  score: number | null;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

function groupFiles(files: string[]) {
  const topLevel: string[] = [];
  const groups = new Map<string, string[]>();

  for (const file of files) {
    const normalized = file.replace(/\\/g, "/");
    const separatorIndex = normalized.indexOf("/");

    if (separatorIndex === -1) {
      topLevel.push(normalized);
      continue;
    }

    const directory = normalized.slice(0, separatorIndex);
    const rest = normalized.slice(separatorIndex + 1);

    if (!groups.has(directory)) {
      groups.set(directory, []);
    }
    groups.get(directory)!.push(rest);
  }

  return { topLevel, groups };
}

export default function Home() {
  const [source, setSource] = useState<RepositorySource>("local");
  const [repositoryPath, setRepositoryPath] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repositoryId, setRepositoryId] = useState<string | null>(null);
  const [repositoryLabel, setRepositoryLabel] = useState<string | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [loadingRepo, setLoadingRepo] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  function toggleDir(directory: string) {
    setExpandedDirs((previous) => {
      const next = new Set(previous);
      if (next.has(directory)) {
        next.delete(directory);
      } else {
        next.add(directory);
      }
      return next;
    });
  }

  async function loadRepository() {
    const inputValue = source === "local" ? repositoryPath : repositoryUrl;

    if (!inputValue.trim() || loadingRepo) {
      return;
    }

    setLoadingRepo(true);
    setRepoError(null);

    try {
      let localPath = inputValue.trim();

      if (source === "github") {
        const cloneResponse = await fetch(
          `${API_BASE}/api/repository/clone?repository_url=${encodeURIComponent(
            localPath
          )}`,
          { method: "POST" }
        );

        if (!cloneResponse.ok) {
          const errorBody = await cloneResponse.json().catch(() => null);
          throw new Error(errorBody?.detail ?? "Failed to clone repository");
        }

        const cloneData = await cloneResponse.json();
        localPath = cloneData.repository_path;
      }

      const [ingestResponse, scanResponse] = await Promise.all([
        fetch(
          `${API_BASE}/api/repository/ingest?repository_path=${encodeURIComponent(
            localPath
          )}`,
          { method: "POST" }
        ),
        fetch(
          `${API_BASE}/api/repository/scan?repository_path=${encodeURIComponent(
            localPath
          )}`
        ),
      ]);

      if (!ingestResponse.ok || !scanResponse.ok) {
        throw new Error("Failed to load repository");
      }

      const ingestData = await ingestResponse.json();
      const scanData = await scanResponse.json();

      setRepositoryId(ingestData.repository_id);
      setRepositoryLabel(
        source === "github" ? repositoryUrl.trim() : repositoryPath.trim()
      );
      setFiles(scanData.files ?? []);
      setMessages([]);
      setSources([]);
    } catch (error) {
      setRepoError(
        error instanceof Error ? error.message : "Could not load that repository."
      );
    } finally {
      setLoadingRepo(false);
    }
  }

  async function sendMessage() {
    if (!input.trim() || !repositoryId || sending) {
      return;
    }

    const question = input.trim();
    setMessages((previous) => [...previous, { role: "user", content: question }]);
    setInput("");
    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: question,
          repository_id: repositoryId,
        }),
      });

      const data = await response.json();

      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: data.message },
      ]);
      setSources(data.sources ?? []);
    } catch {
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      sendMessage();
    }
  }

  const { topLevel, groups } = groupFiles(files);

  return (
    <div className="flex h-screen flex-col">
      {/* App header */}
      <header className="flex items-center justify-between border-b border-black/10 dark:border-white/10 px-5 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-bold tracking-tight">Engineering Copilot</h1>
          <span className="text-xs text-black/45 dark:text-white/45">
            Repository-aware AI developer assistant
          </span>
        </div>

        <div className="flex items-center gap-2">
          {repositoryLabel ? (
            <span className="flex items-center gap-2 rounded-full border border-black/10 dark:border-white/15 px-3 py-1 text-xs">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
              <span className="max-w-[220px] truncate">{repositoryLabel}</span>
            </span>
          ) : (
            <span className="flex items-center gap-2 rounded-full border border-black/10 dark:border-white/15 px-3 py-1 text-xs text-black/45 dark:text-white/45">
              <span className="h-1.5 w-1.5 rounded-full bg-black/30 dark:bg-white/30" />
              No repository loaded
            </span>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden divide-x divide-black/10 dark:divide-white/10">
        {/* Repository / Files panel */}
        <aside className="w-64 flex flex-col overflow-y-auto p-4 bg-black/[0.02] dark:bg-white/[0.03]">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-black/60 dark:text-white/60">
            Repository
          </h2>

          <div className="mt-3 flex rounded-md border border-black/15 dark:border-white/15 p-0.5 text-xs">
            <button
              onClick={() => setSource("local")}
              className={
                "flex-1 rounded px-2 py-1 font-medium transition-colors " +
                (source === "local"
                  ? "bg-blue-600 text-white"
                  : "text-black/60 dark:text-white/60 hover:bg-black/5 dark:hover:bg-white/10")
              }
            >
              Local Path
            </button>
            <button
              onClick={() => setSource("github")}
              className={
                "flex-1 rounded px-2 py-1 font-medium transition-colors " +
                (source === "github"
                  ? "bg-blue-600 text-white"
                  : "text-black/60 dark:text-white/60 hover:bg-black/5 dark:hover:bg-white/10")
              }
            >
              GitHub
            </button>
          </div>

          <div className="mt-3 flex flex-col gap-2">
            {source === "local" ? (
              <input
                type="text"
                value={repositoryPath}
                onChange={(event) => setRepositoryPath(event.target.value)}
                placeholder="C:\path\to\repository"
                className="border border-black/15 dark:border-white/15 rounded px-2 py-1.5 text-sm bg-transparent"
              />
            ) : (
              <input
                type="text"
                value={repositoryUrl}
                onChange={(event) => setRepositoryUrl(event.target.value)}
                placeholder="https://github.com/owner/repo"
                className="border border-black/15 dark:border-white/15 rounded px-2 py-1.5 text-sm bg-transparent"
              />
            )}

            <button
              onClick={loadRepository}
              disabled={loadingRepo}
              className="rounded bg-blue-600 text-white px-2 py-1.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loadingRepo
                ? source === "github"
                  ? "Cloning..."
                  : "Loading..."
                : "Load Repository"}
            </button>

            {repoError && <p className="text-xs text-red-500">{repoError}</p>}

            {repositoryId && (
              <p className="text-xs text-black/50 dark:text-white/50 break-all">
                ID: {repositoryId}
              </p>
            )}
          </div>

          <h3 className="mt-6 text-sm font-semibold uppercase tracking-wide text-black/60 dark:text-white/60">
            Files
          </h3>

          <ul className="mt-2 text-sm space-y-1">
            {topLevel.map((file) => (
              <li key={file} className="truncate">
                {file}
              </li>
            ))}

            {Array.from(groups.entries()).map(([directory, dirFiles]) => (
              <li key={directory}>
                <button
                  onClick={() => toggleDir(directory)}
                  className="w-full text-left font-medium hover:text-black dark:hover:text-white"
                >
                  {expandedDirs.has(directory) ? "▾" : "▸"} {directory}/
                </button>

                {expandedDirs.has(directory) && (
                  <ul className="ml-4 mt-1 space-y-1 text-black/70 dark:text-white/70">
                    {dirFiles.map((file) => (
                      <li key={file} className="truncate">
                        {file}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}

            {files.length === 0 && (
              <li className="text-black/40 dark:text-white/40">
                No repository loaded
              </li>
            )}
          </ul>
        </aside>

        {/* Chat panel */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-black/10 dark:border-white/10">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-black/60 dark:text-white/60">
              AI Chat
            </h2>
            <p className="mt-0.5 text-xs text-black/40 dark:text-white/40">
              Ask questions, get answers grounded in your repository&apos;s code.
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <p className="text-sm text-black/40 dark:text-white/40">
                Load a repository, then ask a question about it.
              </p>
            )}

            {messages.map((message, index) => (
              <div
                key={index}
                className={
                  message.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={
                    "max-w-[75%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap " +
                    (message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-black/5 dark:bg-white/10")
                  }
                >
                  {message.content}
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="max-w-[75%] rounded-lg px-3 py-2 text-sm bg-black/5 dark:bg-white/10 text-black/50 dark:text-white/50">
                  Thinking...
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Sources panel */}
        <aside className="w-72 flex flex-col overflow-y-auto p-4 bg-black/[0.02] dark:bg-white/[0.03]">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-black/60 dark:text-white/60">
            Sources
          </h2>
          <p className="mt-0.5 text-xs text-black/40 dark:text-white/40">
            Code chunks used for the latest answer.
          </p>

          <div className="mt-3 space-y-3">
            {sources.length === 0 && (
              <p className="text-sm text-black/40 dark:text-white/40">
                Sources for the latest answer will appear here.
              </p>
            )}

            {sources.map((sourceRef, index) => (
              <div
                key={index}
                className="border border-black/10 dark:border-white/10 rounded p-2"
              >
                <p className="text-sm font-medium truncate">{sourceRef.file_path}</p>
                <p className="text-xs text-black/50 dark:text-white/50">
                  Lines {sourceRef.start_line}-{sourceRef.end_line}
                </p>
                {sourceRef.score !== null && (
                  <p className="text-xs text-black/40 dark:text-white/40">
                    score: {sourceRef.score.toFixed(3)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </aside>
      </div>

      {/* Input bar */}
      <div className="border-t border-black/10 dark:border-white/10 p-4 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="Ask about your repository..."
          disabled={!repositoryId}
          className="flex-1 border border-black/15 dark:border-white/15 rounded px-3 py-2 text-sm bg-transparent disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={!repositoryId || sending}
          className="rounded bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
