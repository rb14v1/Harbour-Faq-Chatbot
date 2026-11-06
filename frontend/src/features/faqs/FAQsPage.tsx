import { useEffect, useState, type FormEvent } from "react";

import { createFAQ, deleteFAQ, listFAQs, updateFAQ } from "../../api/faqs";
import { extractErrorMessage } from "../../api/client";
import type { FAQEntry } from "../../types";

export function FAQsPage() {
  const [faqs, setFaqs] = useState<FAQEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const response = await listFAQs();
      setFaqs(response.data.results);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function startEdit(faq: FAQEntry) {
    setEditingId(faq.id);
    setQuestion(faq.question);
    setAnswer(faq.answer);
  }

  function cancelEdit() {
    setEditingId(null);
    setQuestion("");
    setAnswer("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (editingId) {
        await updateFAQ(editingId, { question, answer });
      } else {
        await createFAQ({ question, answer });
      }
      cancelEdit();
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this FAQ entry?")) return;
    setError(null);
    try {
      await deleteFAQ(id);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <div className="faqs-page">
      <h1>FAQ Entries</h1>
      <p className="hint">
        Each entry's embedding (used by the Ask page to find relevant answers) is
        computed automatically whenever you create or edit it.
      </p>

      {error && <div className="form-error">{error}</div>}

      <form className="faq-form" onSubmit={handleSubmit}>
        <h2>{editingId ? "Edit FAQ entry" : "Add FAQ entry"}</h2>
        <label>
          Question
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} required rows={2} />
        </label>
        <label>
          Answer
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} required rows={3} />
        </label>
        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : editingId ? "Save changes" : "Add entry"}
          </button>
          {editingId && (
            <button type="button" className="secondary" onClick={cancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {loading ? (
        <p>Loading...</p>
      ) : faqs.length === 0 ? (
        <p>No FAQ entries yet. Add one above.</p>
      ) : (
        <ul className="faq-list">
          {faqs.map((faq) => (
            <li key={faq.id} className="faq-card">
              <div className="faq-card-question">{faq.question}</div>
              <div className="faq-card-answer">{faq.answer}</div>
              <div className="faq-card-actions">
                <button className="secondary" onClick={() => startEdit(faq)}>Edit</button>
                <button className="danger" onClick={() => handleDelete(faq.id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
