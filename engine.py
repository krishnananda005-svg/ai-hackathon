import json
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---- Settings you will tune ----
THRESHOLD = 0.20        # at or above -> answer
WEAK_THRESHOLD = 0.12   # between WEAK and THRESHOLD -> maybe ambiguous, else fallback
AMBIGUITY_GAP = 0.04

# Words that mean the student is asking WHERE something is
LOCATION_WORDS = ("where", "location", "located", "which floor", "how to reach", "directions")

# Spelling variants / shorthand -> the form used in the knowledge base
SYNONYMS = {
    "center": "centre", "centers": "centres",
    "audi": "auditorium",
    "wi-fi": "wifi",
    "xray": "x-ray",
}

# ---- Load the knowledge base ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "knowledge_base.json")
GAPS_PATH = os.path.join(BASE_DIR, "known_gaps.json")

with open(KB_PATH, encoding="utf-8") as f:
    kb = json.load(f)

# Topics the KB mentions but does not locate. "where is <topic>" falls back to staff.
try:
    with open(GAPS_PATH, encoding="utf-8") as f:
        known_gaps = [g.lower() for g in json.load(f)]
except FileNotFoundError:
    known_gaps = []


def normalize(text):
    """Lowercase and unify spellings so queries and KB text match."""
    text = text.lower()
    for old, new in SYNONYMS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


def build_text(e):
    """Text that represents one entry in the search index."""
    keywords = " ".join(e.get("keywords", []))
    questions = " ".join(e.get("sample_questions", []))
    # Title and keywords are repeated so they weigh more than the body text.
    return f'{e["title"]} {e["title"]} {keywords} {keywords} {questions} {e["category"]} {e["content"]}'


docs = [build_text(e) for e in kb]
vectorizer = TfidfVectorizer(preprocessor=normalize, stop_words="english",
                             ngram_range=(1, 2), sublinear_tf=True)
matrix = vectorizer.fit_transform(docs)


def search(query):
    """Return dict: id, answer, title, source, source_url, verified, score, status, suggestions.
    status is one of: 'ok', 'ambiguous', 'no_match'."""
    empty = {"id": None, "answer": None, "title": None, "source": None,
             "source_url": "", "verified": None, "score": 0.0,
             "status": "no_match", "suggestions": []}

    # Empty or too-short queries fall back immediately
    if not query or len(query.strip()) < 3:
        return empty

    # Known gap: a "where is ..." question about something the KB doesn't locate
    q = normalize(query)
    if any(g in q for g in known_gaps) and any(w in q for w in LOCATION_WORDS):
        return empty

    sims = cosine_similarity(vectorizer.transform([query]), matrix)[0]
    ranked = sims.argsort()[::-1]
    best_i, second_i = ranked[0], ranked[1]
    best = float(sims[best_i])
    top3 = [kb[i] for i in ranked[:3] if sims[i] >= WEAK_THRESHOLD]
    suggestions = [e["title"] for e in top3]

    # Far too weak -> fallback to staff
    if best < WEAK_THRESHOLD:
        return {**empty, "score": best}

    # Weak match: vague question if the top matches span different categories
    if best < THRESHOLD:
        categories = {e["category"] for e in top3}
        if len(categories) >= 2:
            return {**empty, "score": best, "status": "ambiguous",
                    "suggestions": suggestions}
        return {**empty, "score": best}

    # Confident match
    status = "ok"
    gap = best - float(sims[second_i])
    if gap < AMBIGUITY_GAP and kb[best_i]["category"] != kb[second_i]["category"]:
        status = "ambiguous"

    e = kb[best_i]
    return {
        "id": e["id"],
        "answer": e["content"],
        "title": e["title"],
        "source": e["source"],
        "source_url": e.get("source_url", ""),
        "verified": e.get("verified", False),
        "score": best,
        "status": status,
        "suggestions": suggestions,
    }