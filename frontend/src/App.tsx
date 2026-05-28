import { useEffect, useRef, useState, type ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";

// Turn "(jane_doe.pdf)" mentions in an answer into links to the served PDF.
function linkifyPdfs(text: string): string {
  return text.replace(/[A-Za-z0-9._-]+\.pdf/g, (file) => `[${file}](/cv/${file})`);
}

// Open every link (cited PDFs included) in a new tab.
const MD_COMPONENTS: Components = {
  a: (props: ComponentPropsWithoutRef<"a">) => (
    <a {...props} target="_blank" rel="noopener noreferrer" />
  ),
};

type Message = {
  role: "user" | "assistant";
  text: string;
  sources?: string[];
  error?: boolean;
};

const SAMPLES = [
  "Who has experience with Python?",
  "Which candidate graduated from UPC?",
  "Summarize the profile of Jane Doe.",
  "Who would be a good fit for a DevOps role?",
];

const TODAY = new Date().toLocaleDateString("en-US", {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
});

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function newChat() {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setInput("");
    setLoading(false);
  }

  async function ask(raw: string) {
    const question = raw.trim();
    if (!question || loading) return;
    // Each question is independent — clear the previous Q&A rather than append.
    setMessages([{ role: "user", text: question }]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`Server responded ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? ""; // keep the trailing partial event
        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data:")) continue;
          const data = JSON.parse(line.slice(5).trim());

          if (data.type === "token") {
            const delta = data.text as string;
            // Append to the in-progress answer, or start one on the first token.
            // Decide from prev state so the updater stays pure (no closure flag).
            setMessages((m) => {
              const last = m[m.length - 1];
              if (last?.role === "assistant") {
                const copy = [...m];
                copy[copy.length - 1] = { ...last, text: last.text + delta };
                return copy;
              }
              return [...m, { role: "assistant", text: delta }];
            });
          } else if (data.type === "sources") {
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") {
                copy[copy.length - 1] = { ...last, sources: data.sources };
              }
              return copy;
            });
          } else if (data.type === "error") {
            throw new Error(data.message);
          }
        }
      }
    } catch (e) {
      if (controller.signal.aborted) return; // reset mid-stream — drop silently
      const msg = e instanceof Error ? e.message : "Request failed";
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          error: true,
          text: `${msg}. Make sure the backend is running on port 8000.`,
        },
      ]);
    } finally {
      if (abortRef.current === controller) {
        setLoading(false);
        abortRef.current = null;
      }
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="paper flex h-full flex-col">
      {/* ── Masthead ─────────────────────────────────────────── */}
      <header className="masthead shrink-0">
        <div className="mx-auto w-full max-w-[44rem] px-6 pt-5">
          <div className="flex items-end justify-between gap-4">
            <div className="rise rise-1">
              <p className="kicker kicker--accent mb-1.5">
                Vol. I &middot; The Candidate Dossier
              </p>
              <h1 className="masthead-title">
                The CV <em>Screener</em>
              </h1>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-3 rise rise-2">
              <p className="dateline hidden sm:block">{TODAY}</p>
              <button
                className="btn-new"
                onClick={newChat}
                disabled={empty && !loading}
                title="Clear the conversation and start over"
              >
                <span>&#10022;</span>New Inquiry
              </button>
            </div>
          </div>
          <p className="kicker mt-3 mb-3">
            A grounded reading of 28 candidate CVs &mdash; every answer drawn
            strictly from their pages
          </p>
        </div>
        <hr className="rule-double" />
      </header>

      {/* ── Body ─────────────────────────────────────────────── */}
      <main className="mx-auto flex w-full max-w-[44rem] flex-1 flex-col overflow-hidden px-6">
        <div className="flex-1 overflow-y-auto py-8">
          {empty ? (
            <div className="pt-6">
              <p className="lede rise rise-2">
                Pose a question and the screener answers like a researcher with
                the files open &mdash; citing the candidates whose words it drew
                from, and nothing it cannot find on the page.
              </p>

              <p className="kicker mt-12 mb-1 rise rise-3">
                Suggested Inquiries
              </p>
              <div className="rise rise-4">
                {SAMPLES.map((s, i) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="inquiry-row"
                  >
                    <span className="inquiry-num">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="inquiry-text">{s}</span>
                    <span className="inquiry-arrow">&rarr;</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div>
              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="qa rise rise-1">
                    <div className="qa-mark qa-mark--q">Q.</div>
                    <div className="q-text">{m.text}</div>
                  </div>
                ) : (
                  <div key={i} className="qa rise rise-1">
                    <div className="qa-mark qa-mark--a">A.</div>
                    <div>
                      <div className={`a-body${m.error ? " is-error" : ""}`}>
                        <ReactMarkdown components={MD_COMPONENTS}>
                          {m.error ? m.text : linkifyPdfs(m.text)}
                        </ReactMarkdown>
                      </div>
                      {m.sources && m.sources.length > 0 && (
                        <div className="sources">
                          <span className="sources-label">Sources cited</span>
                          {m.sources.map((s) => (
                            <a
                              key={s}
                              className="source-chip"
                              href={`/cv/${encodeURIComponent(s)}`}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {s}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ),
              )}

              {loading && messages[messages.length - 1]?.role === "user" && (
                <div className="qa">
                  <div className="qa-mark qa-mark--a">A.</div>
                  <p className="consulting">
                    Consulting the files
                    <span className="dots">
                      <span>.</span>
                      <span>.</span>
                      <span>.</span>
                    </span>
                  </p>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {/* ── Composer ───────────────────────────────────────── */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="composer shrink-0"
        >
          <div className="mx-auto w-full max-w-[44rem]">
            <p className="kicker pt-4 pb-1">Pose a Question</p>
            <div className="composer-field pb-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Who has shipped production ML?"
                className="composer-input"
                aria-label="Ask about the candidates"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="btn-ask"
              >
                Ask
              </button>
            </div>
            <div className="h-5" />
          </div>
        </form>
      </main>
    </div>
  );
}
