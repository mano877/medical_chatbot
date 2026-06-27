from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.database.database import Message, settings

# ─────────────────────────────────────────────
#  LLM Setup
# ─────────────────────────────────────────────
llm = OllamaLLM(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
)
output_parser = StrOutputParser()
DOCTOR_SYSTEM_PROMPT = """You are Dr. Aria, a warm, friendly, and knowledgeable AI medical assistant.

## Your Rules:

1. **Check uploaded documents first**: If the patient has uploaded medical documents, always check them first for relevant information.

2. **If answer IS found in documents**: Answer based on the document content and mention the source:
   "Based on your uploaded documents..."

3. **If answer is NOT found in documents**: Answer from your general medical knowledge but ALWAYS add a disclaimer:
   "I couldn't find this in your uploaded documents, but based on my general medical knowledge [answer here]. Please verify this with your doctor."

4. **Never give dangerous advice**: For serious symptoms (chest pain, difficulty breathing, stroke signs) always urge emergency care immediately.

5. **Never diagnose definitively**: Always recommend consulting a real doctor for serious concerns.

6. **Be empathetic**: Speak kindly and reassuringly like a caring family doctor.

7. **Keep responses concise**: 3-5 paragraphs maximum.

Context from uploaded documents:
{{context}}

Start responses with a warm acknowledgment of what the patient said before giving advice.
"""


def get_ai_response(
    history: list[Message],
    user_message: str,
    rag_context: str | None = None,
) -> str:
    """Build prompt from DB history and call the LLM.

    If *rag_context* is provided, it is injected into the system prompt so
    Dr. Aria can answer based on uploaded medical documents.
    """
    system_prompt = DOCTOR_SYSTEM_PROMPT

    if rag_context:
        system_prompt += f"""

────────────────────────────────────────
REFERENCE DOCUMENTS (uploaded by the patient)
────────────────────────────────────────
The patient has uploaded medical documents that may be relevant.
Use the following excerpts to inform your response when appropriate.
If the information does not apply to the patient's current question,
simply answer from your general medical knowledge.

{rag_context}
"""

    messages_for_prompt = [("system", system_prompt)]

    for msg in history:
        role = "human" if msg.role == "human" else "ai"
        messages_for_prompt.append((role, msg.content))

    messages_for_prompt.append(("human", user_message))

    prompt = ChatPromptTemplate.from_messages(messages_for_prompt)
    chain = prompt | llm | output_parser
    return chain.invoke({})