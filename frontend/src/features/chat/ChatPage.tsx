import { useEffect, useState, type FormEvent } from "react";

import { askQuestion, listChatLogs } from "../../api/chat";
import { extractErrorMessage } from "../../api/client";
import type { AskResponse, ChatLog } from "../../types";

const STUB_MARKER = "[STUB AI RESPONSE";

export function ChatPage() {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  const [history, setHistory] = useState<ChatLog[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  async function refreshHistory() {
    setHistoryLoading(true);
    try {
      const response = await listChatLogs();
      setHistory(response.data.results);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    refreshHistory();
  }, []);

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setError(null);
    setAsking(true);
    try {
      const response = await askQuestion(question);
      setResult(response.data);
      setQuestion("");
      await refreshHistory();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setAsking(false);
    }
  }

  const isStub = result?.answer.startsWith(STUB_MARKER) ?? false;

  return (
    <div className="chat-page">
      <h1>Ask a question</h1>

      <form className="ask-form" onSubmit={handleAsk}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. How do I cancel my subscription?"
          required
        />
        <button type="submit" disabled={asking}>{asking ? "Asking..." : "Ask"}</button>
      </form>

      {error && <div className="form-error">{error}</div>}

      {result && (
        <div className="answer-block">
          {isStub && (
            <div className="stub-banner">
              Running in stub mode — set OPENAI_API_KEY on the backend for real AI-generated answers.
            </div>
          )}
          <h2>Answer</h2>
          <p className="answer-text">{result.answer}</p>

          <h3>Matched FAQ entries</h3>
          {result.matched_faqs.length === 0 ? (
            <p>No matching FAQ entries found. Add some on the FAQ Entries page.</p>
          ) : (
            <ul className="matched-faq-list">
              {result.matched_faqs.map((faq) => (
                <li key={faq.id} className="matched-faq-card">
                  <div className="matched-faq-score">score: {faq.score.toFixed(3)}</div>
                  <div className="faq-card-question">{faq.question}</div>
                  <div className="faq-card-answer">{faq.answer}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <h2>Chat history</h2>
      {historyLoading ? (
        <p>Loading...</p>
      ) : history.length === 0 ? (
        <p>No questions asked yet.</p>
      ) : (
        <ul className="chat-history-list">
          {history.map((log) => (
            <li key={log.id} className="chat-history-item">
              <div className="chat-history-question">Q: {log.question_asked}</div>
              <div className="chat-history-answer">A: {log.generated_answer}</div>
              <div className="chat-history-meta">
                {new Date(log.created_at).toLocaleString()} · {log.matched_faq_ids.length} matched FAQ(s)
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
