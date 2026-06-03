"""Token budget management — tiktoken counting + conversation summarization."""
import tiktoken
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from loguru import logger

_encoder = tiktoken.get_encoding("cl100k_base")

TARGET_TOKENS = 6000
SUMMARY_TRIGGER = 5000


def count_tokens(messages: list) -> int:
    total = 0
    for msg in messages:
        total += 4
        if hasattr(msg, "content") and msg.content:
            if isinstance(msg.content, str):
                total += len(_encoder.encode(msg.content))
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and "text" in block:
                        total += len(_encoder.encode(block["text"]))
    total += 2
    return total


def _summarize_block(messages: list, llm) -> str:
    if not messages:
        return ""
    text = "\n".join([
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content[:300]}"
        for m in messages if hasattr(m, "content") and m.content
    ])[:3000]
    if not text.strip():
        return ""
    prompt = SystemMessage(content=(
        "Resumí esta conversación en español, máximo 200 palabras. Conservá: "
        "1) Decisiones tomadas, 2) Datos importantes, 3) Tareas pendientes, 4) Preferencias del usuario."
    ))
    try:
        resp = llm.invoke([prompt, HumanMessage(content=text)])
        return resp.content[:500]
    except Exception as e:
        logger.warning(f"Summarization falló: {e}")
        return ""


def manage_context(messages: list, llm, persona: str = "profesional") -> list:
    """Trim + optionally summarize to stay within token budget."""
    token_count = count_tokens(messages)
    if token_count < TARGET_TOKENS:
        return messages

    system = [m for m in messages if isinstance(m, SystemMessage)]
    other = [m for m in messages if not isinstance(m, SystemMessage)]

    if token_count > SUMMARY_TRIGGER and len(other) > 6:
        split = max(len(other) * 4 // 10, 4)
        to_summarize = other[:split]
        to_keep = other[split:]
        summary_text = _summarize_block(to_summarize, llm)
        if summary_text:
            summary_msg = SystemMessage(content=f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}")
            messages = system + [summary_msg] + to_keep
            logger.info(f"Conversación resumida: {len(to_summarize)} msgs → {len(summary_text)} chars")
            return messages

    budget_per_msg = TARGET_TOKENS // max(len(other), 1)
    result = list(system)
    for msg in reversed(other):
        if count_tokens(result + [msg]) < TARGET_TOKENS:
            result.append(msg)
        else:
            break

    trimmed = list(system) + list(reversed(result[len(system):]))
    logger.info(f"Mensajes recortados: {len(other)} → {len(trimmed) - len(system)} ({TARGET_TOKENS} tokens)")
    return trimmed
