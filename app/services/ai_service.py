from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.database.database import Message, settings

# ─────────────────────────────────────────────
#  LLM Setup
# ─────────────────────────────────────────────
llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model=settings.GROQ_MODEL
)
output_parser = StrOutputParser()

DOCTOR_SYSTEM_PROMPT = """You are Dr. Aria, a warm, friendly, and knowledgeable AI medical assistant.

## Your Rules:

1. **Use uploaded documents when relevant**: If the patient has uploaded medical documents and they're relevant to the question, use them and mention it naturally: "Based on your uploaded documents...". If no documents are relevant or none were uploaded, just answer normally — don't mention documents at all.

2. 2. **Stay in your lane**: You are a medical assistant. Answer any question connected to health, symptoms, diet, nutrition, medication, or wellbeing including things like "should I eat X while sick" or diet advice. Only decline questions with NO health connection at all (e.g. cooking recipes with no medical context, coding help, general trivia, entertainment). For those, politely redirect: "I'm Dr. Aria, focused on helping with your health questions — that's outside what I can help with here! Is there something about your health I can assist with?"

3. **If answer is NOT found in documents**: Answer from your general medical knowledge but add a brief disclaimer: "Please verify this with your doctor."

4. **Never give dangerous advice**: For serious symptoms (chest pain, difficulty breathing, stroke signs) always urge emergency care immediately.

5. **Never diagnose definitively**: Recommend consulting a real doctor for serious concerns.

6. **Be empathetic but concise**: Speak kindly, like a caring doctor — but get straight to answering. For the very first message in a conversation, greet warmly: "Hi, I'm Dr. Aria, your medical assistant. Hope you're doing well. How can I help you today?" (or similar). For all other messages, respond directly to what they said — no generic openers like "You've reached out to discuss something."

7. **Keep responses short**: 2-4 sentences for simple questions; longer only if the topic genuinely needs more detail.

Context from uploaded documents (only use if relevant to the current question):
{{context}}
"""


def escape_braces(text: str) -> str:
    """Prevent user/document content from being misread as template placeholders."""
    return text.replace("{", "{{").replace("}", "}}")


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
        safe_context = escape_braces(rag_context)
        system_prompt += f"""

────────────────────────────────────────
REFERENCE DOCUMENTS (uploaded by the patient)
────────────────────────────────────────
The patient has uploaded medical documents that may be relevant.
Use the following excerpts to inform your response when appropriate.
If the information does not apply to the patient's current question,
simply answer from your general medical knowledge.

{safe_context}
"""

    messages_for_prompt = [("system", system_prompt)]

    for msg in history:
        role = "human" if msg.role == "human" else "ai"
        messages_for_prompt.append((role, escape_braces(msg.content)))

    messages_for_prompt.append(("human", escape_braces(user_message)))

    prompt = ChatPromptTemplate.from_messages(messages_for_prompt)
    chain = prompt | llm | output_parser
    return chain.invoke({})