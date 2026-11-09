from mlops_triage.rag.rank import cosine_similarity, top_k_by_vector


def test_cosine_similarity_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == 1.0


def test_top_k_returns_highest_scores():
    records = [
        {"id": "a", "embedding": [1.0, 0.0]},
        {"id": "b", "embedding": [0.0, 1.0]},
        {"id": "c", "embedding": [0.9, 0.1]},
    ]
    hits = top_k_by_vector([1.0, 0.0], records, k=2)
    assert hits[0]["id"] == "a"
    assert hits[1]["id"] == "c"
    assert hits[0]["embedding"] is None
