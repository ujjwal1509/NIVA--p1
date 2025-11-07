# scripts/seed_vector_db.py
import json

chunks = [
    {
        "id": "c1",
        "text": "If patient has chest pain ask about radiation, exertion, diaphoresis",
        "tags": ["cardiology", "red_flag"],
    },
    {
        "id": "c2",
        "text": "If cough with fever ask about sputum color, breathlessness, duration",
        "tags": ["pulmonology"],
    },
]
with open("scripts/knowledge_chunks.json", "w") as f:
    json.dump(chunks, f, indent=2)
print("seeded knowledge_chunks.json")
