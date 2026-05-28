import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

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

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function ask(raw: string) {
    const question = raw.trim();
    if (!question || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.answer, sources: data.sources },
      ]);
    } catch (e) {
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
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 font-bold text-white">
            CV
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800">AI CV Screener</h1>
            <p className="text-xs text-slate-500">
              Ask questions about 28 candidate CVs — answers are grounded in their content.
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden px-5">
        <div className="flex-1 space-y-4 overflow-y-auto py-6">
          {messages.length === 0 && (
            <div className="mt-10 text-center">
              <h2 className="text-xl font-semibold text-slate-700">
                Screen candidates by asking a question
              </h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
                Try one of these, or type your own below.
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {SAMPLES.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm text-slate-700 transition hover:border-indigo-400 hover:bg-indigo-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-white">
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-start">
                <div
                  className={`max-w-[85%] rounded-2xl rounded-bl-sm border px-4 py-3 ${
                    m.error
                      ? "border-red-200 bg-red-50 text-red-700"
                      : "border-slate-200 bg-white text-slate-800"
                  }`}
                >
                  <div className="md text-sm leading-relaxed">
                    <ReactMarkdown>{m.text}</ReactMarkdown>
                  </div>
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-3 border-t border-slate-100 pt-2">
                      <p className="mb-1.5 text-xs font-medium text-slate-400">
                        Sources
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {m.sources.map((s) => (
                          <span
                            key={s}
                            className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ),
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-400">
                Searching the CVs…
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="mb-5 flex gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the candidates…"
            className="flex-1 bg-transparent px-3 py-2 text-slate-800 outline-none placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-indigo-600 px-5 py-2 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Ask
          </button>
        </form>
      </main>
    </div>
  );
}
