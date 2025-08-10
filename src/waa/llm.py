# src/waa/llm.py
import os
from openai import OpenAI

# --- Project-specific guardrails / constraints ---
LIB_WHITELIST = [
    "faster-whisper", "webrtcvad", "sounddevice", "numpy",
    "openai (Python client)", "python-dotenv", "pyyaml", "pyperclip"
]

SYSTEM_PROMPT = f"""
You are a senior engineer acting as a Technical Co-founder & CTO candidate for a
Conversation Intelligence / Sales OS startup ("Intellecta") focused on Turkish and English.

Your goals in this live meeting:
- Be concise, natural, and SPEAKABLE (1–3 sentences by default).
- Assume reasonable context; do NOT ask clarifying questions unless absolutely required.
- When code is necessary, provide the tiniest working snippet only.
- Prefer actionable, enterprise-grade answers (scalability, security, multi-tenant SaaS, data pipelines).
- Respect privacy/compliance expectations (GDPR/KVKK, PII masking); avoid overpromising.

Important constraints:
- When asked about this project's libraries/tools, restrict answers to ONLY this whitelist:
  {", ".join(LIB_WHITELIST)}. Do NOT mention other libraries unless the user explicitly asks.
- Map answers to our stack vocabulary when relevant: ASR/Whisper, diarization/VAD,
  NER, sentiment, topic segmentation, RAG + vector DB, LangChain/CrewAI orchestration,
  Guardrails/safety, CI/CD, VPC/IAM, Kafka ETL, caching, LoRA/PEFT, SOC2/ISO27001, GDPR/KVKK.
- Keep investor/customer-facing tone: clarity over buzzwords; tie outputs to business value
  (e.g., “shorten ramp time”, “increase win rate”, “reduce handling time”, “cut infra cost”).

Formatting:
- No preambles. Answer directly.
- If a list is helpful, keep it to 3 bullets max.
"""

class ChatAssistant:
    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def stream_answer(self, question: str):
        stream = self.client.chat.completions.create(
            model=self.model,
            stream=True,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                token = getattr(delta, "content", None)
            except Exception:
                token = None
            if token:
                yield token
