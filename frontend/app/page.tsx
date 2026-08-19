"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const STORAGE_KEYS = {
  source: "copilot:source",
  repositoryPath: "copilot:repositoryPath",
  repositoryUrl: "copilot:repositoryUrl",
  repositoryLabel: "copilot:repositoryLabel",
  conversationId: "copilot:conversationId",
} as const;

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
  toolCalls?: string[];
}

interface RepositoryCatalogEntry {
  repository_id: string;
  source_type: RepositorySource;
  path_or_url: string;
  label: string;
  last_ingested_at: string;
}

interface ConversationCatalogEntry {
  conversation_id: string;
  title: string | null;
  updated_at: string;
}

function describeToolCall(name: string, args: Record<string, unknown>): string {
  switch (name) {
    case "search_code":
      return `Searching code for "${args.query ?? ""}"`;
    case "get_file_content":
      return `Reading ${String(args.file_path ?? "").replace(/\\/g, "/")}`;
    case "list_repository_files":
      return args.directory_prefix
        ? `Listing files under "${args.directory_prefix}"`
        : "Listing repository files";
    default:
      return `Running ${name}`;
  }
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

// Mirrors backend/app/services/code_service.py's extension -> language map,
// so a file's sidebar icon and its source-card dot always agree on language.
const EXTENSION_LANGUAGE: Record<string, string> = {
  py: "python",
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",
  java: "java",
  cpp: "cpp",
  c: "c",
  cs: "csharp",
  go: "go",
  rs: "rust",
  html: "html",
  css: "css",
  json: "json",
  md: "markdown",
};

const LANGUAGE_TEXT_COLOR: Record<string, string> = {
  python: "text-blue-500",
  javascript: "text-amber-500",
  typescript: "text-cyan-500",
  java: "text-rose-500",
  cpp: "text-indigo-500",
  c: "text-indigo-400",
  csharp: "text-emerald-500",
  go: "text-teal-500",
  rust: "text-orange-500",
  html: "text-pink-500",
  css: "text-violet-500",
  json: "text-slate-400",
  markdown: "text-orange-400",
};

const LANGUAGE_DOT_COLOR: Record<string, string> = {
  python: "bg-blue-500",
  javascript: "bg-amber-500",
  typescript: "bg-cyan-500",
  java: "bg-rose-500",
  cpp: "bg-indigo-500",
  c: "bg-indigo-400",
  csharp: "bg-emerald-500",
  go: "bg-teal-500",
  rust: "bg-orange-500",
  html: "bg-pink-500",
  css: "bg-violet-500",
  json: "bg-slate-400",
  markdown: "bg-orange-400",
};

function languageColorClass(language: string) {
  return LANGUAGE_TEXT_COLOR[language] ?? "text-muted-foreground";
}

function languageDotClass(language: string) {
  return LANGUAGE_DOT_COLOR[language] ?? "bg-muted-foreground/50";
}

function fileColorClass(path: string) {
  const extension = path.split(".").pop()?.toLowerCase() ?? "";
  const language = EXTENSION_LANGUAGE[extension];
  return language ? languageColorClass(language) : "text-muted-foreground";
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

function IconBug({ className }: { className?: string }) {
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
      <rect x="7" y="8" width="10" height="11" rx="4" />
      <path d="M9 8V6a3 3 0 1 1 6 0v2" />
      <path d="M12 11v6" />
      <path d="M4 12h3" />
      <path d="M17 12h3" />
      <path d="M5 18l2-2" />
      <path d="M19 18l-2-2" />
    </svg>
  );
}

function IconSun({ className }: { className?: string }) {
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
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function IconMoon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a.6.6 0 0 0-.74-.74A9.5 9.5 0 1 0 21.24 15.24a.6.6 0 0 0-.74-.74z" />
    </svg>
  );
}

function IconWrench({ className }: { className?: string }) {
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
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
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

const MARKDOWN_COMPONENTS: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => (
    <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0">{children}</ol>
  ),
  li: ({ children }) => <li>{children}</li>,
  h1: ({ children }) => (
    <h1 className="mb-2 mt-1 text-base font-semibold first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-1.5 mt-1 text-[15px] font-semibold first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-1.5 mt-1 text-sm font-semibold first:mt-0">{children}</h3>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-accent underline underline-offset-2 hover:text-accent-hover"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mb-2 border-l-2 border-border pl-3 text-muted-foreground last:mb-0">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-border" />,
  table: ({ children }) => (
    <div className="mb-2 overflow-x-auto last:mb-0">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border bg-panel px-2 py-1 text-left font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
  pre: ({ children }) => (
    <pre className="mb-2 overflow-x-auto rounded-lg border border-border bg-panel px-3 py-2.5 text-xs last:mb-0">
      {children}
    </pre>
  ),
  code: ({ className, children }) => {
    // Fenced code blocks are multi-line; inline `code` spans never contain a
    // newline — cheap, dependency-free way to tell them apart since
    // react-markdown no longer passes an `inline` flag.
    const isBlock = String(children).includes("\n");

    if (isBlock) {
      return <code className={"font-mono " + (className ?? "")}>{children}</code>;
    }

    return (
      <code className="rounded bg-panel px-1 py-0.5 font-mono text-[13px]">
        {children}
      </code>
    );
  },
};

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
      {content}
    </ReactMarkdown>
  );
}

type Theme = "light" | "dark";

export default function Home() {
  const [theme, setTheme] = useState<Theme>("light");
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

  const [recentRepositories, setRecentRepositories] = useState<RepositoryCatalogEntry[]>([]);
  const [conversationHistory, setConversationHistory] = useState<ConversationCatalogEntry[]>([]);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
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

  useEffect(() => {
    const stored = window.localStorage.getItem("theme");

    if (stored === "light" || stored === "dark") {
      setTheme(stored);
      return;
    }

    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(prefersDark ? "dark" : "light");
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("theme", theme);
  }, [theme]);

  // Resume the last loaded repository (and its conversation, if any) after a
  // refresh, by re-running the same clone/scan/ingest pipeline the "Load
  // Repository" button uses rather than trying to shortcut past it.
  useEffect(() => {
    const savedSource = window.localStorage.getItem(STORAGE_KEYS.source);
    const savedPath = window.localStorage.getItem(STORAGE_KEYS.repositoryPath);
    const savedUrl = window.localStorage.getItem(STORAGE_KEYS.repositoryUrl);
    const savedConversationId = window.localStorage.getItem(
      STORAGE_KEYS.conversationId
    );

    const resumedSource: RepositorySource = savedSource === "github" ? "github" : "local";
    const resumedInput = resumedSource === "github" ? savedUrl : savedPath;

    setSource(resumedSource);
    if (savedPath) setRepositoryPath(savedPath);
    if (savedUrl) setRepositoryUrl(savedUrl);

    loadRecentRepositories();

    if (resumedInput) {
      resumeRepository(resumedSource, resumedInput, savedConversationId);
    }
    // Runs once on mount to hydrate from localStorage.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.source, source);
  }, [source]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.repositoryPath, repositoryPath);
  }, [repositoryPath]);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEYS.repositoryUrl, repositoryUrl);
  }, [repositoryUrl]);

  useEffect(() => {
    if (repositoryLabel) {
      window.localStorage.setItem(STORAGE_KEYS.repositoryLabel, repositoryLabel);
    }
  }, [repositoryLabel]);

  useEffect(() => {
    if (conversationId) {
      window.localStorage.setItem(STORAGE_KEYS.conversationId, conversationId);
    } else {
      window.localStorage.removeItem(STORAGE_KEYS.conversationId);
    }
  }, [conversationId]);

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

  // Shared by the "Load Repository" button and by resume-on-refresh: both
  // need to re-run clone/scan/ingest (all idempotent) but only the button
  // press should reset the active chat.
  async function performLoad(sourceType: RepositorySource, inputValue: string) {
    let localPath = inputValue.trim();

    if (sourceType === "github") {
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
        )}&source_type=${sourceType}&origin=${encodeURIComponent(inputValue.trim())}`,
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
    setRepositoryLabel(inputValue.trim());
    setFiles(scanData.files ?? []);
    setSelectedFile(null);
    setExpandedDirs(new Set());

    loadRecentRepositories();
    loadConversationHistory(ingestData.repository_id);

    return ingestData.repository_id as string;
  }

  async function loadRecentRepositories() {
    try {
      const response = await fetch(`${API_BASE}/api/repositories`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      setRecentRepositories(data.repositories ?? []);
    } catch {
      // Non-critical: the sidebar list just stays empty/stale.
    }
  }

  async function loadConversationHistory(forRepositoryId: string) {
    try {
      const response = await fetch(
        `${API_BASE}/api/repositories/${forRepositoryId}/conversations`
      );
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      setConversationHistory(data.conversations ?? []);
    } catch {
      // Non-critical: the sidebar list just stays empty/stale.
    }
  }

  async function loadRepository() {
    const inputValue = source === "local" ? repositoryPath : repositoryUrl;

    if (!inputValue.trim() || loadingRepo) {
      return;
    }

    setLoadingRepo(true);
    setRepoError(null);

    try {
      await performLoad(source, inputValue);
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

  async function resumeRepository(
    sourceType: RepositorySource,
    inputValue: string,
    savedConversationId: string | null
  ) {
    if (!inputValue.trim() || loadingRepo) {
      return;
    }

    setLoadingRepo(true);
    setRepoError(null);

    try {
      const loadedRepositoryId = await performLoad(sourceType, inputValue);

      if (savedConversationId) {
        const historyResponse = await fetch(
          `${API_BASE}/api/chat/${savedConversationId}?repository_id=${encodeURIComponent(
            loadedRepositoryId
          )}`
        );

        if (historyResponse.ok) {
          const historyData = await historyResponse.json();
          const turns = (historyData.turns ?? []) as ChatMessage[];

          if (turns.length > 0) {
            setMessages(turns);
            setConversationId(savedConversationId);
          }
        }
      }
    } catch (error) {
      setRepoError(
        error instanceof Error ? error.message : "Could not resume that repository."
      );
    } finally {
      setLoadingRepo(false);
      setLoadingStage("");
    }
  }

  async function selectRecentRepository(entry: RepositoryCatalogEntry) {
    if (loadingRepo) {
      return;
    }

    setSource(entry.source_type);
    if (entry.source_type === "github") {
      setRepositoryUrl(entry.path_or_url);
    } else {
      setRepositoryPath(entry.path_or_url);
    }

    setLoadingRepo(true);
    setRepoError(null);

    try {
      await performLoad(entry.source_type, entry.path_or_url);
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

  async function openConversation(entry: ConversationCatalogEntry) {
    if (!repositoryId || sending || entry.conversation_id === conversationId) {
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/chat/${entry.conversation_id}?repository_id=${encodeURIComponent(
          repositoryId
        )}`
      );

      if (!response.ok) {
        throw new Error("Failed to load that conversation.");
      }

      const data = await response.json();
      setMessages((data.turns ?? []) as ChatMessage[]);
      setSources([]);
      setConversationId(entry.conversation_id);
      isPinnedToBottomRef.current = true;
      setShowJumpToBottom(false);
    } catch (error) {
      setRepoError(
        error instanceof Error ? error.message : "Could not load that conversation."
      );
    }
  }

  function updateLastAssistantMessage(updater: (content: string) => string) {
    setMessages((previous) => {
      const next = [...previous];
      const lastIndex = next.length - 1;
      next[lastIndex] = {
        ...next[lastIndex],
        role: "assistant",
        content: updater(next[lastIndex].content),
      };
      return next;
    });
  }

  function appendToolCall(description: string) {
    setMessages((previous) => {
      const next = [...previous];
      const lastIndex = next.length - 1;
      next[lastIndex] = {
        ...next[lastIndex],
        role: "assistant",
        toolCalls: [...(next[lastIndex].toolCalls ?? []), description],
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
        } else if (sseEvent.event === "tool_call") {
          const call = JSON.parse(sseEvent.data);
          appendToolCall(describeToolCall(call.name, call.args ?? {}));
        } else if (sseEvent.event === "error") {
          updateLastAssistantMessage((content) => content || sseEvent.data);
        }
      }
    } catch (error) {
      console.error("Chat stream failed:", error);
      updateLastAssistantMessage(
        (content) => content || "Something went wrong. Please try again."
      );
    } finally {
      setSending(false);
      if (repositoryId) {
        loadConversationHistory(repositoryId);
      }
    }
  }

  async function explainFile() {
    if (!selectedFile || !repositoryId || sending) {
      return;
    }

    const fileLabel = selectedFile.replace(/\\/g, "/");
    isPinnedToBottomRef.current = true;
    setShowJumpToBottom(false);
    setMessages((previous) => [
      ...previous,
      { role: "user", content: `Explain ${fileLabel}` },
      { role: "assistant", content: "" },
    ]);
    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat/explain/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_id: repositoryId,
          file_path: selectedFile,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Explain stream request failed");
      }

      for await (const sseEvent of readSseEvents(response.body)) {
        if (sseEvent.event === "meta") {
          const meta = JSON.parse(sseEvent.data);
          setConversationId(meta.conversation_id ?? null);
          setSources(meta.sources ?? []);
        } else if (sseEvent.event === "token") {
          updateLastAssistantMessage((content) => content + sseEvent.data);
        } else if (sseEvent.event === "error") {
          updateLastAssistantMessage((content) => content || sseEvent.data);
        }
      }
    } catch (error) {
      console.error("Chat stream failed:", error);
      updateLastAssistantMessage(
        (content) => content || "Something went wrong. Please try again."
      );
    } finally {
      setSending(false);
      if (repositoryId) {
        loadConversationHistory(repositoryId);
      }
    }
  }

  async function debugError() {
    if (!input.trim() || !repositoryId || sending) {
      return;
    }

    const errorText = input.trim();
    isPinnedToBottomRef.current = true;
    setShowJumpToBottom(false);
    setMessages((previous) => [
      ...previous,
      { role: "user", content: errorText },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat/debug/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_id: repositoryId,
          error_text: errorText,
          file_path: selectedFile,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Debug stream request failed");
      }

      for await (const sseEvent of readSseEvents(response.body)) {
        if (sseEvent.event === "meta") {
          const meta = JSON.parse(sseEvent.data);
          setConversationId(meta.conversation_id ?? null);
          setSources(meta.sources ?? []);
        } else if (sseEvent.event === "token") {
          updateLastAssistantMessage((content) => content + sseEvent.data);
        } else if (sseEvent.event === "error") {
          updateLastAssistantMessage((content) => content || sseEvent.data);
        }
      }
    } catch (error) {
      console.error("Chat stream failed:", error);
      updateLastAssistantMessage(
        (content) => content || "Something went wrong. Please try again."
      );
    } finally {
      setSending(false);
      if (repositoryId) {
        loadConversationHistory(repositoryId);
      }
    }
  }

  async function startNewChat() {
    if (conversationId) {
      fetch(`${API_BASE}/api/chat/${conversationId}`, { method: "DELETE" })
        .then(() => {
          if (repositoryId) {
            loadConversationHistory(repositoryId);
          }
        })
        .catch(() => {});
    }
    setMessages([]);
    setSources([]);
    setConversationId(null);
    isPinnedToBottomRef.current = true;
    setShowJumpToBottom(false);
  }

  function handleInputKeyDown(
    event: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>
  ) {
    if (debugMode) {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        debugError();
      }
      return;
    }

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
            <aside className="flex w-72 flex-col overflow-hidden bg-panel-muted/30">
            <div className="flex-1 overflow-y-auto p-4">
              <h2 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-tint-repo" />
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
                  className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-button-from to-button-to px-2 py-2 text-sm font-medium text-button-foreground shadow-sm shadow-accent/20 transition hover:brightness-105 disabled:opacity-50"
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

              {recentRepositories.length > 0 && (
                <>
                  <h3 className="mt-6 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Recent Repositories
                  </h3>
                  <ul className="mt-2 max-h-40 space-y-0.5 overflow-y-auto text-xs">
                    {recentRepositories.map((entry) => (
                      <li key={entry.repository_id}>
                        <button
                          onClick={() => selectRecentRepository(entry)}
                          disabled={loadingRepo}
                          title={entry.path_or_url}
                          className={
                            "flex w-full items-center gap-1.5 truncate rounded px-1.5 py-1 text-left transition-colors disabled:opacity-50 " +
                            (entry.repository_id === repositoryId
                              ? "bg-accent/15 text-accent"
                              : "text-foreground/85 hover:bg-panel-muted")
                          }
                        >
                          <span className="rounded-full bg-panel px-1.5 py-0.5 text-[9px] uppercase text-muted-foreground">
                            {entry.source_type}
                          </span>
                          <span className="truncate">{entry.label}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {repositoryId && conversationHistory.length > 0 && (
                <>
                  <h3 className="mt-6 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    History
                  </h3>
                  <ul className="mt-2 max-h-40 space-y-0.5 overflow-y-auto text-xs">
                    {conversationHistory.map((entry) => (
                      <li key={entry.conversation_id}>
                        <button
                          onClick={() => openConversation(entry)}
                          disabled={sending}
                          title={entry.title ?? "Untitled conversation"}
                          className={
                            "flex w-full items-center truncate rounded px-1.5 py-1 text-left transition-colors disabled:opacity-50 " +
                            (entry.conversation_id === conversationId
                              ? "bg-accent/15 text-accent"
                              : "text-foreground/85 hover:bg-panel-muted")
                          }
                        >
                          <span className="truncate">{entry.title ?? "Untitled conversation"}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}

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
                      <IconFile
                        className={"h-3.5 w-3.5 flex-shrink-0 " + fileColorClass(file.path)}
                      />
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
                                <IconFile
                                  className={"h-3.5 w-3.5 flex-shrink-0 " + fileColorClass(file.path)}
                                />
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
            </div>

            <div className="border-t border-border p-3">
              <div className="flex rounded-lg border border-border bg-panel-muted/60 p-1 text-xs">
                <button
                  onClick={() => setTheme("light")}
                  className={
                    "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 font-medium transition-all " +
                    (theme === "light"
                      ? "bg-gradient-to-r from-button-from to-button-to text-button-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  <IconSun className="h-3.5 w-3.5" />
                  Light
                </button>
                <button
                  onClick={() => setTheme("dark")}
                  className={
                    "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 font-medium transition-all " +
                    (theme === "dark"
                      ? "bg-gradient-to-r from-button-from to-button-to text-button-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground")
                  }
                >
                  <IconMoon className="h-3.5 w-3.5" />
                  Dark
                </button>
              </div>
            </div>
            </aside>

            {/* Chat panel */}
            <main className="relative flex flex-1 flex-col overflow-hidden">
              <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
                <div>
                  <h2 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    <span className="h-1.5 w-1.5 rounded-full bg-tint-chat" />
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

                      <div className="flex max-w-[75%] flex-col gap-1.5">
                        {!!message.toolCalls?.length && (
                          <div className="flex flex-col gap-1 border-l-2 border-border pl-2.5">
                            {message.toolCalls.map((call, callIndex) => {
                              const isActive =
                                isStreamingPlaceholder && callIndex === message.toolCalls!.length - 1;

                              return (
                                <div
                                  key={callIndex}
                                  className="flex items-center gap-1.5 text-xs text-muted-foreground"
                                >
                                  {isActive ? (
                                    <IconSpinner className="h-3 w-3 flex-shrink-0 animate-spin" />
                                  ) : (
                                    <IconWrench className="h-3 w-3 flex-shrink-0 opacity-60" />
                                  )}
                                  <span className="font-mono">{call}</span>
                                </div>
                              );
                            })}
                          </div>
                        )}

                        <div
                          className={
                            "px-3.5 py-2.5 text-sm leading-relaxed shadow-sm " +
                            (message.role === "user"
                              ? "whitespace-pre-wrap rounded-2xl rounded-br-md bg-gradient-to-br from-accent to-accent-hover text-accent-foreground"
                              : "rounded-2xl rounded-bl-md border border-border bg-panel-muted/70 text-foreground")
                          }
                        >
                          {isStreamingPlaceholder ? (
                            <ThinkingDots />
                          ) : message.role === "assistant" ? (
                            <MarkdownMessage content={message.content} />
                          ) : (
                            message.content
                          )}
                        </div>
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
                <IconSource className="h-3.5 w-3.5 text-tint-sources" />
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
                    <div className="flex items-center gap-1.5">
                      <span
                        className={
                          "h-1.5 w-1.5 flex-shrink-0 rounded-full " +
                          languageDotClass(sourceRef.language)
                        }
                      />
                      <p className="truncate font-mono text-xs font-medium text-foreground/90">
                        {sourceRef.file_path}
                      </p>
                    </div>
                    <div className="mt-2 flex items-center gap-1.5">
                      <span
                        className={
                          "rounded-full bg-panel px-2 py-0.5 text-[10px] font-medium " +
                          languageColorClass(sourceRef.language)
                        }
                      >
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

                <button
                  onClick={explainFile}
                  disabled={sending}
                  className="rounded-full border border-transparent bg-chip-teal-bg px-2.5 py-1 text-xs font-medium text-chip-teal-foreground transition-colors hover:brightness-105 disabled:opacity-50"
                >
                  Explain this file
                </button>
              </div>
            )}

            <div className="flex items-end gap-3 p-4">
              <button
                onClick={() => setDebugMode((previous) => !previous)}
                disabled={sending}
                aria-pressed={debugMode}
                aria-label="Toggle debug mode"
                title="Debug mode: paste an error or stack trace for root-cause analysis"
                className={
                  "flex flex-shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-2.5 text-sm font-medium transition disabled:opacity-50 " +
                  (debugMode
                    ? "border-transparent bg-chip-amber-bg text-chip-amber-foreground"
                    : "border-chip-amber-foreground/30 text-chip-amber-foreground hover:border-chip-amber-foreground/60 hover:bg-chip-amber-bg")
                }
              >
                <IconBug className="h-4 w-4 flex-shrink-0" />
                Debug
              </button>

              {debugMode ? (
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Paste an error message or stack trace... (Ctrl+Enter to submit)"
                  disabled={!repositoryId}
                  rows={3}
                  className={fieldClasses + " resize-none py-2.5 font-mono"}
                />
              ) : (
                <input
                  type="text"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Ask about your repository..."
                  disabled={!repositoryId}
                  className={fieldClasses + " py-2.5"}
                />
              )}
              <button
                onClick={debugMode ? debugError : sendMessage}
                disabled={!repositoryId || sending}
                aria-label={debugMode ? "Submit error for debugging" : "Send message"}
                className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-button-from to-button-to text-button-foreground shadow-sm shadow-accent/25 transition hover:brightness-105 disabled:opacity-40"
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
