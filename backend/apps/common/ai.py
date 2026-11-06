"""
Embedding + chat-completion dual path: real OpenAI calls when OPENAI_API_KEY
is configured, otherwise deterministic, zero-cost, zero-network stubs.

*** IMPORTANT: the stub embedding is NOT semantically meaningful. ***
It is a reproducible pseudo-random vector derived from a SHA-256 hash of the
input text, so the same text always produces the same vector (useful for
testing determinism, migrations, and ranking plumbing) - but it has no
relationship whatsoever to the text's actual meaning. Similarity search run
against stub embeddings will NOT return semantically relevant results; it's
only useful for verifying that the embed -> store -> search -> answer
pipeline is wired correctly end to end. Real semantic search quality
requires setting OPENAI_API_KEY so get_embedding() calls the real OpenAI
embeddings API.

Same stub-by-default pattern applies to generate_answer(): without a key it
returns a templated string rather than a real generated answer.
"""
import hashlib
import math
import random

from django.conf import settings


def _stub_embedding(text: str, dimensions: int) -> list[float]:
    """Deterministic, reproducible, NOT semantically meaningful vector."""
    seed = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rng = random.Random(seed)
    vector = [rng.uniform(-1.0, 1.0) for _ in range(dimensions)]
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def get_embedding(text: str) -> list[float]:
    """
    Return an embedding vector for `text`.

    Real path (OPENAI_API_KEY set): calls OpenAI's embeddings API using
    OPENAI_EMBEDDING_MODEL (default text-embedding-3-large), requesting
    EMBEDDING_DIMENSIONS via the API's `dimensions` param.

    Stub path (no key): deterministic pseudo-random vector, see module
    docstring - NOT semantically meaningful, just reproducible so the
    pipeline is fully testable without a key or network access.
    """
    dimensions = getattr(settings, "EMBEDDING_DIMENSIONS", 1536)
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""

    if not api_key:
        return _stub_embedding(text, dimensions)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    response = client.embeddings.create(
        model=model,
        input=text,
        dimensions=dimensions,
    )
    return response.data[0].embedding


def generate_answer(question: str, context_snippets: list[str]) -> str:
    """
    Return a generated answer to `question`, grounded in `context_snippets`
    (typically "question: answer" strings from the top-matching FAQ
    entries).

    Real path (OPENAI_API_KEY set): calls OpenAI's chat completions API
    using OPENAI_CHAT_MODEL (default "gpt-5.6-sol", wired through exactly as
    configured - unverifiable without a real key/model in this environment).

    Stub path (no key): deterministic templated string naming how many
    context snippets were found and quoting the top match, so callers and
    tests can assert on it without any network access.
    """
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""

    if not api_key:
        top_match = context_snippets[0][:200] if context_snippets else "none"
        return (
            f"[STUB AI RESPONSE — set OPENAI_API_KEY for real output] "
            f"Found {len(context_snippets)} related FAQ(s). Top match: {top_match}"
        )

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-5.6-sol")

    context_block = "\n".join(f"- {snippet}" for snippet in context_snippets) or "(no matching FAQs found)"
    messages = [
        {
            "role": "system",
            "content": (
                "You are an FAQ assistant. Answer the user's question using "
                "only the context FAQ entries below. If the context does not "
                "contain a relevant answer, say so rather than guessing."
            ),
        },
        {
            "role": "user",
            "content": f"Context FAQs:\n{context_block}\n\nQuestion: {question}",
        },
    ]
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content
