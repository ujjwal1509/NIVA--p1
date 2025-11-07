# app/symptom_chain.py
import os
import json
from datetime import datetime
from typing import Dict, Any

from langchain.output_parsers import StructuredOutputParser
from langchain import PromptTemplate

# Try to use LangChain's Ollama wrapper; else call Ollama HTTP
try:
    from langchain.llms import Ollama

    _HAS_LANGCHAIN_OLLAMA = True
except Exception:
    _HAS_LANGCHAIN_OLLAMA = False

import requests

MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

# JSON schema for StructuredOutputParser (match schemas.py)
json_schema = {
    "type": "object",
    "properties": {
        "presenting_complaint": {"type": "string"},
        "symptoms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "onset_relative": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "severity": {"type": "string"},
                    "associated_symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name"],
            },
        },
        "urgency": {"type": "string"},
        "recommended_next_action": {"type": "string"},
        "evidence_snippets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
            },
        },
    },
    "required": ["presenting_complaint", "symptoms", "urgency"],
}
parser = StructuredOutputParser.from_dict(json_schema)

prompt_template_text = """
You are a concise medical triage assistant. Ask short, relevant clinical questions to gather symptom details.
Do not provide a definitive diagnosis. At the end produce ONLY valid JSON that matches the schema instructions below.

{format_instructions}

Conversation so far:
{chat_history}
"""

prompt = PromptTemplate(
    input_variables=["chat_history", "format_instructions"],
    template=prompt_template_text,
)

# instantiate LLM wrapper if available
llm = None
if _HAS_LANGCHAIN_OLLAMA:
    llm = Ollama(model=MODEL_NAME)


def _call_ollama_http(prompt_text: str) -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt_text,
        "max_tokens": 800,
        "temperature": 0.0,
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "output" in data:
        if isinstance(data["output"], list) and len(data["output"]) > 0:
            return "".join(str(chunk.get("content", "")) for chunk in data["output"])
        return str(data["output"])
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0].get("message", {}).get("content", "")
    return json.dumps(data)


def _llm_predict(prompt_text: str) -> str:
    if _HAS_LANGCHAIN_OLLAMA and llm is not None:
        return llm.predict(prompt_text)
    else:
        return _call_ollama_http(prompt_text)


def run_extraction(chat_history: str) -> Dict[str, Any]:
    format_instructions = parser.get_format_instructions()
    filled_prompt = prompt.format(
        chat_history=chat_history, format_instructions=format_instructions
    )

    raw = _llm_predict(filled_prompt)

    try:
        parsed = parser.parse(raw)
    except Exception:
        repair_prompt = (
            "The previous output did not match the required JSON schema. "
            "Please output ONLY the JSON matching the format below and nothing else:\n\n"
            f"{format_instructions}\n\n"
            f"Previous output:\n{raw}\n\n"
        )
        raw2 = _llm_predict(repair_prompt)
        parsed = parser.parse(raw2)

    parsed["collected_at"] = datetime.utcnow().isoformat()
    parsed["model_version"] = MODEL_NAME
    return parsed
