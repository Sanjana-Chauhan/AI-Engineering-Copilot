"use client";

import { useEffect, useRef, useState } from "react";

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

interface FileEntry {
  name: string;
  path: string;
}

function groupFiles(files: string[]) {
  const topLevel: FileEntry[] = [];
  const groups = new Map<string, FileEntry[]>();

  for (const rawPath of files) {
    const normalized = rawPath.replace(/\\/g, "/");
    const separatorIndex = normalized.indexOf("/");

    if (separatorIndex === -1) {
      topLevel.push({ name: normalized, path: rawPath });
      continue;
    }

    const directory = normalized.slice(0, separatorIndex);
    const rest = normalized.slice(separatorIndex + 1);

    if (!groups.has(directory)) {
      groups.set(directory, []);
    }
    groups.get(directory)!.push({ name: rest, path: rawPath });
  }

  return { topLevel, groups };
}

function IconChevron({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

function IconFile({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z" />
      <path d="M13 3v6h6" />
    </svg>
  );
}

function IconSparkle({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2l1.8 5.6L19 9l-5.2 1.6L12 16l-1.8-5.4L5 9l5.2-1.4z" />
    </svg>
  );
}

function IconArrowUp({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.25}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 19V5" />
      <path d="M5 12l7-7 7 7" />
    </svg>
  );
}

function IconSource({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M4 6h16" />
      <path d="M4 12h10" />
      <path d="M4 18h7" />
    </svg>
  );
}

function IconClose({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.25}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function IconSpinner({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="3"
        opacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

interface SseEvent {
  event: string;
  data: string;
}

async function* readSseEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<SseEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventType = "message";
      const dataLines: string[] = [];

      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).replace(/^ /, ""));
        }
      }

      yield { event: eventType, data: dataLines.join("\n") };
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce"
          style={{ animationDelay: `${index * 0.12}s` }}
        />
      ))}
    </span>
  );
}

export default function Home() {
  const [source, setSource] = useState<RepositorySource>("local");
  const [repositoryPath, setRepositoryPath] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repositoryId, setRepositoryId] = useState<string | null>(null);
  const [repositoryLabel, setRepositoryLabel] = useState<string | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loadingRepo, setLoadingRepo] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [repoError, setRepoError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isPinnedToBottomRef = useRef(true);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);

  const BOTTOM_PIN_THRESHOLD_PX = 64;

  function handleMessagesScroll() {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    const pinned = distanceFromBottom <= BOTTOM_PIN_THRESHOLD_PX;

    isPinnedToBottomRef.current = pinned;
    setShowJumpToBottom(!pinned);
  }

  function scrollToBottom(behavior: ScrollBehavior) {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    container.scrollTo({ top: container.scrollHeight, behavior });
    isPinnedToBottomRef.current = true;
    setShowJumpToBottom(false);
  }

  // Runs on every message update, including each streamed token — while
  // pinned, an instant scrollTop write keeps the view glued to the bottom
  // without stacking up competing "smooth" animations on every token.
  useEffect(() => {
    if (!isPinnedToBottomRef.current) {
      return;
    }

    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  function toggleFileSelection(path: string) {
    setSelectedFile((previous) => (previous === path ? null : path));
  }

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
        setLoadingStage("Cloning repository from GitHub...");

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

      setLoadingStage("Scanning files and indexing code...");

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
      setSelectedFile(null);
      setExpandedDirs(new Set());
      setMessages([]);
      setSources([]);
      setConversationId(null);
      isPinnedToBottomRef.current = true;
      setShowJumpToBottom(false);
    } catch (error) {
      setRepoError(
        error instanceof Error ? error.message : "Could not load that repository."
      );
    } finally {
      setLoadingRepo(false);
      setLoadingStage("");
    }
  }

  function updateLastAssistantMessage(updater: (content: string) => string) {
    setMessages((previous) => {
      const next = [...previous];
      const lastIndex = next.length - 1;
      next[lastIndex] = {
        role: "assistant",
        content: updater(next[lastIndex].content),
      };
      return next;
    });
  }

  async function sendMessage() {
    if (!input.trim() || !repositoryId || sending) {
      return;
    }

    const question = input.trim();
    isPinnedToBottomRef.current = true;
    setShowJumpToBottom(false);
    setMessages((previous) => [
      ...previous,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: question,
          repository_id: repositoryId,
          conversation_id: conversationId,
          file_path: selectedFile,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Chat stream request failed");
      }

      for await (const sseEvent of readSseEvents(response.body)) {
        if (sseEvent.event === "meta") {
          const meta = JSON.parse(sseEvent.data);
          setConversationId(meta.conversation_id ?? null);
          setSources(meta.sources ?? []);
        } else if (sseEvent.event === "token") {
          updateLastAssistantMessage((content) => content + sseEvent.data);
        }
      }
    } catch {
      updateLastAssistantMessage(
        (content) => content || "Something went wrong. Please try again."
      );
    } finally {
      setSending(false);
    }
  }

  async function startNewChat() {
    if (conversationId) {
      fetch(`${API_BASE}/api/chat/${conversationId}`, { method: "DELETE" }).catch(
        () => {}
      );
    }
    setMessages([]);
    setSources([]);
    setConversationId(null);
    isPinnedToBottomRef.current = true;
    setShowJumpToBottom(false);
  }

  function handleInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      sendMessage();
    }
  }

  const { topLevel, groups } = groupFiles(files);
  const fieldClasses =
    "w-full rounded-lg border border-border bg-panel-muted/60 px-2.5 py-1.5 text-sm text-foreground placeholder:text-muted-foreground outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/25";

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      {/* Ambient background glow */}
      <div
        className="pointer-events-none fixed -top-32 -left-32 h-[26rem] w-[26rem] rounded-full opacity-25 blur-[110px]"
        style={{ background: "var(--glow-1)" }}
      />
      <div
        className="pointer-events-none fixed bottom-[-8rem] right-[-6rem] h-[30rem] w-[30rem] rounded-full opacity-20 blur-[130px]"
        style={{ background: "var(--glow-2)" }}
      />

      <div className="relative z-10 flex h-screen flex-col p-3 sm:p-5">
        <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-panel/80 shadow-2xl shadow-black/10 backdrop-blur-xl">
          {/* App header */}
          <header className="flex items-center justify-between border-b border-border px-5 py-3.5">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-cyan-400 font-mono text-sm font-bold text-white shadow-sm shadow-accent/30">
                {"</>"}
              </div>
              <div className="flex items-baseline gap-2.5">
                <h1 className="bg-gradient-to-r from-accent to-cyan-400 bg-clip-text text-lg font-bold tracking-tight text-transparent">
                  Engineering Copilot
                </h1>
                <span className="hidden text-xs text-muted-foreground sm:inline">
                  Repository-aware AI developer assistant
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {repositoryLabel ? (
                <span className="flex items-center gap-2 rounded-full border border-border bg-panel-muted/70 px-3 py-1.5 text-xs">
                  <span className="h-1.5 w-1.5 rounded-full bg-success shadow-[0_0_6px_var(--success)]" />
                  <span className="max-w-[220px] truncate font-medium">
                    {repositoryLabel}
                  </span>
                </span>
              ) : (
                <span className="flex items-center gap-2 rounded-full border border-border bg-panel-muted/70 px-3 py-1.5 text-xs text-muted-foreground">
                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50" />
                  No repository loaded
                </span>
              )}
            </div>
          </header>

          <div className="flex flex-1 overflow-hidden divide-x divide-border">
            {/* Repository / Files panel */}
            <aside className="flex w-72 flex-col overflow-y-auto bg-panel-muted/30 p-4">
              <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Repository
              </h2>

              <div className="mt-3 flex rounded-lg border border-border bg-panel-muted/60 p-1 text-xs">
                <button
                  onClick={() => setSource("local")}
                  disabled={loadingRepo}
                  className={
                    "flex-1 rounded-md px-2 py-1.5 font-medium transition-all disabled:opacity-50 " +
                    (source === "local"
                      ? "bg-gradient-to-r from-accent to-accent-hover text-accent-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  Local Path
                </button>
                <button
                  onClick={() => setSource("github")}
                  disabled={loadingRepo}
                  className={
                    "flex-1 rounded-md px-2 py-1.5 font-medium transition-all disabled:opacity-50 " +
                    (source === "github"
                      ? "bg-gradient-to-r from-accent to-accent-hover text-accent-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground")
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
                    disabled={loadingRepo}
                    className={fieldClasses + " disabled:opacity-50"}
                  />
                ) : (
                  <input
                    type="text"
                    value={repositoryUrl}
                    onChange={(event) => setRepositoryUrl(event.target.value)}
                    placeholder="https://github.com/owner/repo"
                    disabled={loadingRepo}
                    className={fieldClasses + " disabled:opacity-50"}
                  />
                )}

                <button
                  onClick={loadRepository}
                  disabled={loadingRepo}
                  className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-accent to-accent-hover px-2 py-2 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/20 transition hover:brightness-110 disabled:opacity-50"
                >
                  {loadingRepo && (
                    <IconSpinner className="h-3.5 w-3.5 flex-shrink-0 animate-spin" />
                  )}
                  {loadingRepo ? "Working..." : "Load Repository"}
                </button>

                {loadingRepo && (
                  <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <IconSpinner className="h-3 w-3 flex-shrink-0 animate-spin" />
                    {loadingStage}
                  </p>
                )}

                {repoError && (
                  <p className="text-xs text-red-500">{repoError}</p>
                )}

                {repositoryId && !loadingRepo && (
                  <p className="truncate text-xs text-muted-foreground">
                    ID: <span className="font-mono">{repositoryId}</span>
                  </p>
                )}
              </div>

              <h3 className="mt-6 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Files
              </h3>

              <ul className="mt-2 space-y-0.5 font-mono text-xs">
                {loadingRepo && (
                  <li className="flex items-center gap-1.5 px-1.5 py-1 font-sans text-muted-foreground">
                    <IconSpinner className="h-3 w-3 flex-shrink-0 animate-spin" />
                    {loadingStage || "Loading repository..."}
                  </li>
                )}

                {!loadingRepo && topLevel.map((file) => (
                  <li key={file.path}>
                    <button
                      onClick={() => toggleFileSelection(file.path)}
                      title="Click to scope your next question to this file"
                      className={
                        "flex w-full items-center gap-1.5 truncate rounded px-1.5 py-1 text-left transition-colors " +
                        (selectedFile === file.path
                          ? "bg-accent/15 text-accent"
                          : "text-foreground/85 hover:bg-panel-muted")
                      }
                    >
                      <IconFile className="h-3.5 w-3.5 flex-shrink-0" />
                      <span className="truncate">{file.name}</span>
                    </button>
                  </li>
                ))}

                {!loadingRepo && Array.from(groups.entries()).map(([directory, dirFiles]) => {
                  const isOpen = expandedDirs.has(directory);
                  return (
                    <li key={directory}>
                      <button
                        onClick={() => toggleDir(directory)}
                        className="flex w-full items-center gap-1 rounded px-1.5 py-1 text-left font-medium text-foreground/90 hover:bg-panel-muted"
                      >
                        <IconChevron
                          className={
                            "h-3 w-3 flex-shrink-0 transition-transform " +
                            (isOpen ? "rotate-90" : "")
                          }
                        />
                        {directory}/
                      </button>

                      {isOpen && (
                        <ul className="ml-4 mt-0.5 space-y-0.5 border-l border-border pl-2">
                          {dirFiles.map((file) => (
                            <li key={file.path}>
                              <button
                                onClick={() => toggleFileSelection(file.path)}
                                title="Click to scope your next question to this file"
                                className={
                                  "flex w-full items-center gap-1.5 truncate rounded px-1.5 py-1 text-left transition-colors " +
                                  (selectedFile === file.path
                                    ? "bg-accent/15 text-accent"
                                    : "text-foreground/70 hover:bg-panel-muted")
                                }
                              >
                                <IconFile className="h-3.5 w-3.5 flex-shrink-0" />
                                <span className="truncate">{file.name}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  );
                })}

                {!loadingRepo && files.length === 0 && (
                  <li className="px-1.5 py-1 font-sans text-muted-foreground">
                    No repository loaded
                  </li>
                )}
              </ul>
            </aside>

            {/* Chat panel */}
            <main className="relative flex flex-1 flex-col overflow-hidden">
              <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
                <div>
                  <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    AI Chat
                  </h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Ask questions, get answers grounded in your repository&apos;s code.
                  </p>
                </div>

                {messages.length > 0 && (
                  <button
                    onClick={startNewChat}
                    className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-accent/40 hover:text-foreground"
                  >
                    New Chat
                  </button>
                )}
              </div>

              <div
                ref={messagesContainerRef}
                onScroll={handleMessagesScroll}
                className="flex-1 space-y-4 overflow-y-auto p-5"
              >
                {messages.length === 0 && (
                  <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-accent to-cyan-400 text-white shadow-md shadow-accent/25">
                      <IconSparkle className="h-5 w-5" />
                    </div>
                    <p className="text-sm font-medium text-foreground/80">
                      Start a conversation
                    </p>
                    <p className="max-w-xs text-xs text-muted-foreground">
                      Load a repository on the left, then ask a question about it.
                    </p>
                  </div>
                )}

                {messages.map((message, index) => {
                  const isStreamingPlaceholder =
                    sending &&
                    index === messages.length - 1 &&
                    message.role === "assistant" &&
                    message.content === "";

                  return (
                    <div
                      key={index}
                      className={
                        "flex items-start gap-2 " +
                        (message.role === "user" ? "justify-end" : "justify-start")
                      }
                    >
                      {message.role === "assistant" && (
                        <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-cyan-400 text-white">
                          <IconSparkle className="h-3 w-3" />
                        </div>
                      )}

                      <div
                        className={
                          "max-w-[75%] whitespace-pre-wrap px-3.5 py-2.5 text-sm leading-relaxed shadow-sm " +
                          (message.role === "user"
                            ? "rounded-2xl rounded-br-md bg-gradient-to-br from-accent to-accent-hover text-accent-foreground"
                            : "rounded-2xl rounded-bl-md border border-border bg-panel-muted/70 text-foreground")
                        }
                      >
                        {isStreamingPlaceholder ? <ThinkingDots /> : message.content}
                      </div>
                    </div>
                  );
                })}
              </div>

              {showJumpToBottom && (
                <button
                  onClick={() => scrollToBottom("smooth")}
                  aria-label="Scroll to latest message"
                  className="absolute bottom-4 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-panel/90 text-foreground shadow-lg backdrop-blur transition hover:border-accent/40 hover:text-accent"
                >
                  <IconArrowUp className="h-4 w-4 rotate-180" />
                </button>
              )}
            </main>

            {/* Sources panel */}
            <aside className="flex w-80 flex-col overflow-y-auto bg-panel-muted/30 p-4">
              <h2 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <IconSource className="h-3.5 w-3.5" />
                Sources
              </h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Code chunks used for the latest answer.
              </p>

              <div className="mt-3 space-y-2.5">
                {sources.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    Sources for the latest answer will appear here.
                  </p>
                )}

                {sources.map((sourceRef, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-border bg-panel-muted/60 p-3 transition-colors hover:border-accent/40"
                  >
                    <p className="truncate font-mono text-xs font-medium text-foreground/90">
                      {sourceRef.file_path}
                    </p>
                    <div className="mt-2 flex items-center gap-1.5">
                      <span className="rounded-full bg-panel px-2 py-0.5 text-[10px] text-muted-foreground">
                        {sourceRef.language}
                      </span>
                      <span className="rounded-full bg-panel px-2 py-0.5 text-[10px] text-muted-foreground">
                        L{sourceRef.start_line}-{sourceRef.end_line}
                      </span>
                    </div>
                    {sourceRef.score !== null && (
                      <p className="mt-1.5 text-[10px] text-muted-foreground">
                        match score: {sourceRef.score.toFixed(3)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </aside>
          </div>

          {/* Input bar */}
          <div className="border-t border-border">
            {selectedFile && (
              <div className="flex items-center gap-2 px-4 pt-3">
                <span className="flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 text-xs text-accent">
                  <IconFile className="h-3 w-3 flex-shrink-0" />
                  <span className="max-w-[280px] truncate font-mono">
                    {selectedFile.replace(/\\/g, "/")}
                  </span>
                  <button
                    onClick={() => setSelectedFile(null)}
                    aria-label="Clear file scope"
                    className="ml-0.5 flex-shrink-0 text-accent/70 transition-colors hover:text-accent"
                  >
                    <IconClose className="h-3 w-3" />
                  </button>
                </span>
              </div>
            )}

            <div className="flex items-center gap-3 p-4">
              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleInputKeyDown}
                placeholder="Ask about your repository..."
                disabled={!repositoryId}
                className={fieldClasses + " py-2.5"}
              />
              <button
                onClick={sendMessage}
                disabled={!repositoryId || sending}
                aria-label="Send message"
                className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-hover text-accent-foreground shadow-sm shadow-accent/25 transition hover:brightness-110 disabled:opacity-40"
              >
                <IconArrowUp className="h-4.5 w-4.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
