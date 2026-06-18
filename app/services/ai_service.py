from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.database import Message, settings

# ─────────────────────────────────────────────
#  LLM Setup
# ─────────────────────────────────────────────
llm = OllamaLLM(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
)
output_parser = StrOutputParser()

DOCTOR_SYSTEM_PROMPT = """You are Dr. Aria, a warm, friendly, and knowledgeable AI medical assistant.

Your personality:
- Speak kindly and reassuringly, like a caring family doctor
- Use simple, easy-to-understand language (avoid heavy medical jargon)
- Always show empathy — patients may be worried or in pain
- Give practical, helpful general health guidance
- For serious symptoms (chest pain, breathing difficulty, stroke signs), always urge the user to seek emergency care immediately
- Never diagnose definitively — always recommend consulting a real doctor for serious concerns
- Keep responses concise but thorough

Start responses with a warm acknowledgment of what the patient said before giving advice.
"""


def get_ai_response(history: list[Message], user_message: str) -> str:
    """Build prompt from DB history and call the LLM."""
    messages_for_prompt = [("system", DOCTOR_SYSTEM_PROMPT)]

    for msg in history:
        role = "human" if msg.role == "human" else "ai"
        messages_for_prompt.append((role, msg.content))

    messages_for_prompt.append(("human", user_message))

    prompt = ChatPromptTemplate.from_messages(messages_for_prompt)
    chain = prompt | llm | output_parser
    return chain.invoke({})