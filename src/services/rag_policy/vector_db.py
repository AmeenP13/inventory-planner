from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class LightweightPolicySearch:
    def __init__(self):
        self.policies_dir = Path(__file__).resolve().parent / "policies"
        self.documents = []
        self.filenames = []

        if self.policies_dir.exists():
            for file in self.policies_dir.glob("*.txt"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            self.documents.append(content)
                            self.filenames.append(file.name)
                except Exception:
                    pass

        if not self.documents:
            # Fallback default policies if directory is empty
            self.documents = [
                "Safety Stock Policy\n\n1. The standard safety stock is 10 days of average sales...",
                "Emergency Restock Policy\n\nTrigger immediate order if stock drops below 2 days...",
            ]
            self.filenames = ["safety_stock_policy.txt", "emergency_policy.txt"]

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

    def similarity_search(self, query: str, k: int = 1):
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get indices sorted by similarity score ascending
        top_indices = similarities.argsort()[-k:][::-1]

        results = []
        for idx in top_indices:
            results.append(
                Document(
                    self.documents[idx],
                    {"source": self.filenames[idx]}
                )
            )
        return results


_LIGHTWEIGHT_STORE = None


def get_vector_db():
    global _LIGHTWEIGHT_STORE
    if _LIGHTWEIGHT_STORE is None:
        _LIGHTWEIGHT_STORE = LightweightPolicySearch()
    return _LIGHTWEIGHT_STORE
