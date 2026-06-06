from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Message, Order, Product
from app.services.rag import (
    build_retrieval_query,
    detect_policy_topic,
    filter_policy_hits,
    format_knowledge_context,
    search_knowledge,
    search_products,
)

Intent = Literal[
    "product_recommendation",
    "ingredient_question",
    "order_support",
    "policy_faq",
    "medical_safety",
    "escalation",
    "general",
]


class AgentState(TypedDict):
    store_id: int
    conversation_id: int
    user_message: str
    intent: str
    context: dict[str, Any]
    response: str
    should_escalate: bool
    sources: list[str]


MEDICAL_PATTERNS = [
    r"\binfection\b",
    r"\ballergic reaction\b",
    r"\bdermatitis\b",
    r"\bprescribe\b",
    r"\bdiagnos",
    r"\bsevere acne\b",
    r"\brash\b",
    r"\bswelling\b",
    r"\bpsoriasis\b",
    r"\beczema\b",
    r"\bhives\b",
]

ESCALATION_PATTERNS = [
    r"\brefund dispute\b",
    r"\bchargeback\b",
    r"\bnot happy\b",
    r"\bangry\b",
    r"\bspeak to (a )?human\b",
    r"\bmanager\b",
    r"\bterrible service\b",
    r"\bunacceptable\b",
    r"\blawyer\b",
]

INTENT_TEMPERATURES = {
    "product_recommendation": 0.45,
    "ingredient_question": 0.15,
    "order_support": 0.1,
    "policy_faq": 0.1,
    "medical_safety": 0.0,
    "escalation": 0.2,
    "general": 0.3,
}

PROFILE_CONCERNS = [
    "acne",
    "hyperpigmentation",
    "dark spots",
    "fine lines",
    "wrinkles",
    "redness",
    "dehydration",
    "uneven skin tone",
    "enlarged pores",
]

SKIN_TYPES = ["oily", "dry", "combination", "sensitive", "normal"]


def _classify_intent_rules(message: str) -> Intent:
    lowered = message.lower()

    if any(re.search(pattern, lowered) for pattern in MEDICAL_PATTERNS):
        return "medical_safety"
    if any(re.search(pattern, lowered) for pattern in ESCALATION_PATTERNS):
        return "escalation"
    if any(term in lowered for term in ["where is my order", "tracking", "shipped", "order status", "order #", "order number"]):
        return "order_support"
    if any(term in lowered for term in ["ship", "shipping", "delivery", "international", "return", "refund", "policy"]):
        return "policy_faq"
    if any(term in lowered for term in ["niacinamide", "vitamin c", "retinol", "salicylic", "ingredient", "can i use", "compatible", "mix", "layer"]):
        return "ingredient_question"
    if any(
        term in lowered
        for term in [
            "recommend",
            "routine",
            "best for",
            "which product",
            "help me choose",
            "skin type",
            "what should i buy",
            "complete routine",
            "morning routine",
            "night routine",
        ]
    ) or any(term in lowered for term in SKIN_TYPES + PROFILE_CONCERNS):
        return "product_recommendation"
    return "general"


def _classify_intent_llm(message: str, history: list[dict[str, str]], profile: dict[str, Any]) -> Intent | None:
    if not settings.OPENAI_API_KEY:
        return None

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_INTENT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        recent = "\n".join(f"{item['role']}: {item['content']}" for item in history[-4:])
        prompt = (
            "Classify the latest customer message into exactly one intent:\n"
            "product_recommendation, ingredient_question, order_support, policy_faq, "
            "medical_safety, escalation, general.\n"
            f"Customer profile: {json.dumps(profile)}\n"
            f"Recent conversation:\n{recent}\n"
            f"Latest message: {message}\n"
            "Return only the intent label."
        )
        result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=message)])
        content = str(getattr(result, "content", "")).strip().lower()
        valid = {
            "product_recommendation",
            "ingredient_question",
            "order_support",
            "policy_faq",
            "medical_safety",
            "escalation",
            "general",
        }
        if content in valid:
            return content  # type: ignore[return-value]
    except Exception:
        return None
    return None


def _classify_intent(message: str, history: list[dict[str, str]], profile: dict[str, Any]) -> Intent:
    llm_intent = _classify_intent_llm(message, history, profile)
    if llm_intent:
        return llm_intent
    return _classify_intent_rules(message)


def _format_products(products: list[Product]) -> str:
    if not products:
        return "No matching products found in the current store catalog."

    lines = []
    for index, product in enumerate(products, start=1):
        lines.append(
            f"{index}. {product.title} ({product.price})\n"
            f"   Description: {product.description}\n"
            f"   Ingredients: {product.ingredients}\n"
            f"   Collections: {', '.join(product.collections or [])}"
        )
    return "\n".join(lines)


def _intent_instructions(intent: str) -> str:
    instructions = {
        "product_recommendation": (
            "Act as a beauty advisor. Ask one focused follow-up question only if key profile details are missing. "
            "Recommend 1-3 products from the catalog, explain why each fits, and mention how/when to use them. "
            "If enough context exists, offer a concise morning and/or night routine using only catalog products."
        ),
        "ingredient_question": (
            "Answer ingredient compatibility and usage questions using the knowledge context first. "
            "Be precise about timing, layering order, and sensitivity considerations. "
            "Do not invent ingredient interactions that are not supported by the provided context."
        ),
        "order_support": (
            "Use only the order context provided. If order details are missing, ask for order number and checkout email. "
            "Never guess tracking numbers or delivery dates."
        ),
        "policy_faq": (
            "Answer only the specific policy topic asked (shipping, returns, or store FAQ). "
            "Use short bullet points in plain language. Do not mix unrelated policies in one answer. "
            "If the policy context does not contain the answer, say what you do know and offer to escalate."
        ),
        "medical_safety": (
            "Do not diagnose or prescribe. Acknowledge the concern empathetically and clearly recommend seeing a dermatologist. "
            "You may share only high-level, non-medical skincare safety guidance."
        ),
        "escalation": (
            "Acknowledge frustration, explain that a human specialist will take over, and avoid making promises about refunds or outcomes."
        ),
        "general": (
            "Be helpful and guide the customer toward product discovery, ingredient help, order support, or policy questions."
        ),
    }
    return instructions.get(intent, instructions["general"])


def _build_system_prompt(intent: str, context: dict[str, Any]) -> str:
    return (
        "You are an expert skincare advisor and customer support assistant for a Shopify beauty store.\n"
        "Rules:\n"
        "- Use ONLY the store catalog, knowledge context, order context, and customer profile provided below.\n"
        "- Never invent products, prices, order statuses, tracking numbers, or policies.\n"
        "- If required data is missing, ask a short clarifying question.\n"
        "- Never diagnose diseases, prescribe medication, or claim medical cures.\n"
        "- Keep responses conversational, clear, and under 180 words unless building a routine.\n"
        "- Never show raw document filenames, chunk markers, or unedited policy excerpts to the customer.\n"
        "- Summarize policies in plain language with short bullet points when helpful.\n"
        f"Active intent: {intent}\n"
        f"Intent instructions: {_intent_instructions(intent)}\n"
        f"Customer profile: {json.dumps(context.get('profile', {}))}\n"
        f"Store catalog:\n{context.get('products', 'No products available.')}\n"
        f"Knowledge context:\n{context.get('knowledge', 'No knowledge retrieved.')}\n"
        f"Order context:\n{context.get('orders', 'No order data retrieved.')}"
    )


POLICY_TOPIC_ANSWERS: dict[str, dict[str, Any]] = {
    "shipping": {
        "lead": "Yes, we offer international shipping.",
        "bullets": [
            "We ship to most international destinations.",
            "International delivery typically takes 7-14 business days.",
            "Customers are responsible for customs duties, import taxes, and local fees.",
            "Tracking is provided when the carrier supports it in the destination country.",
        ],
    },
    "returns": {
        "lead": "Here is our return and refund policy:",
        "bullets": [
            "Unopened and unused products may be returned within 30 days of delivery.",
            "Opened products may be returned only if defective, damaged on arrival, or the wrong item was shipped.",
            "Refunds are processed within 5-7 business days after we receive and inspect the return.",
            "To start a return, contact support with your order number.",
        ],
    },
    "general": {
        "lead": "Here is what I can share from our store policies:",
        "bullets": [
            "Orders over $50 qualify for free standard shipping in the US.",
            "Unopened products may be returned within 30 days of delivery.",
            "All products are cruelty-free and dermatologist-tested.",
        ],
    },
}


def _is_policy_header(point: str) -> bool:
    lowered = point.lower()
    if "glow beauty" in lowered:
        return True
    if re.search(r"\b(policy|shipping|returns?|refund|tracking|restrictions)\.?$", lowered):
        return True
    if re.search(r"\((united states|us)\)", lowered):
        return True
    return len(point.split()) <= 4


def _extract_knowledge_points(text: str, query_terms: set[str], limit: int = 4) -> list[str]:
    points: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if line.startswith("- "):
            point = line[2:].strip()
        elif line.startswith("• "):
            point = line[2:].strip()
        else:
            continue
        point = point.strip(" .")
        if len(point) < 18 or _is_policy_header(point):
            continue
        points.append(point if point.endswith(".") else f"{point}.")

    if not points:
        cleaned = re.sub(r"\s+", " ", text).strip()
        for part in re.split(r"\s*-\s+", cleaned):
            point = part.strip(" .")
            if len(point) < 18 or _is_policy_header(point):
                continue
            points.append(point if point.endswith(".") else f"{point}.")

    ranked = sorted(
        points,
        key=lambda point: sum(1 for term in query_terms if term in point.lower()),
        reverse=True,
    )
    unique: list[str] = []
    seen: set[str] = set()
    for point in ranked:
        key = point[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
        if len(unique) >= limit:
            break
    return unique


def _policy_fallback_answer(message: str, knowledge_hits: list[dict[str, Any]]) -> str:
    topic = detect_policy_topic(message)
    template = POLICY_TOPIC_ANSWERS.get(topic, POLICY_TOPIC_ANSWERS["general"])
    scoped_hits = filter_policy_hits(knowledge_hits, topic)

    query_terms = set(re.findall(r"[a-z0-9]{3,}", message.lower()))
    points: list[str] = []
    for hit in scoped_hits[:2]:
        points.extend(_extract_knowledge_points(hit.get("text", ""), query_terms, limit=4))

    if len(points) < 2:
        points = list(template["bullets"])

    body = "\n".join(f"- {point}" for point in points[:4])
    return f"{template['lead']}\n{body}\n\nLet me know if you want help with a product or order next."


def _ingredient_fallback_answer(message: str, knowledge_hits: list[dict[str, Any]]) -> str:
    if not knowledge_hits:
        return (
            "I can help with ingredient questions once the store knowledge base is loaded. "
            "Tell me which ingredients or products you are comparing."
        )

    query_terms = set(re.findall(r"[a-z0-9]{3,}", message.lower()))
    points = _extract_knowledge_points(knowledge_hits[0].get("text", ""), query_terms, limit=4)
    body = "\n".join(f"- {point}" for point in points)
    return f"Here is guidance based on our ingredient knowledge:\n{body}\n\nI can also suggest suitable products if you'd like."


def _fallback_response(state: AgentState) -> str:
    intent = state["intent"]
    context = state["context"]
    products = context.get("product_objects", [])
    knowledge_hits = context.get("knowledge_hits", [])
    orders = context.get("orders", "")

    if intent == "medical_safety":
        return (
            "Your concern may require professional evaluation. I can share general skincare guidance, "
            "but I cannot diagnose conditions or prescribe treatment. Please consult a dermatologist "
            "for personalized medical advice."
        )

    if intent == "escalation":
        return (
            "I understand this needs extra attention. I'm flagging this conversation for a human specialist "
            "who can review your case and follow up shortly."
        )

    if intent == "order_support":
        if orders:
            return (
                f"I found your order details:\n{orders}\n"
                "If this is not the right order, share your order number and the email used at checkout."
            )
        return (
            "I can help check order status. Please share your order number (for example, #3452) "
            "and the email used at checkout."
        )

    if intent == "policy_faq":
        return _policy_fallback_answer(state["user_message"], knowledge_hits)

    if intent == "ingredient_question":
        return _ingredient_fallback_answer(state["user_message"], knowledge_hits)

    if intent == "product_recommendation" and products:
        lead = products[0]
        extras = products[1:3]
        response = (
            f"Based on what you shared, I'd start with {lead.title} ({lead.price}). "
            f"{lead.description} Key ingredients: {lead.ingredients}."
        )
        if extras:
            names = ", ".join(item.title for item in extras)
            response += f" Strong alternatives from your store: {names}."
        response += " Would you like me to build a morning and night routine from these?"
        return response

    if products:
        names = ", ".join(item.title for item in products[:3])
        return f"I can help with that. Relevant options in your store include: {names}. What is your skin type and main concern?"

    return (
        "I'd love to help. Tell me your skin type, main concerns, and whether you want a single product or a full routine."
    )


def _llm_response(state: AgentState, history: list[dict[str, str]]) -> str:
    if not settings.OPENAI_API_KEY:
        return _fallback_response(state)

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_CHAT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=INTENT_TEMPERATURES.get(state["intent"], settings.OPENAI_TEMPERATURE),
        )
        history_messages = []
        for item in history[-settings.CHAT_HISTORY_LIMIT :]:
            if item["role"] == "user":
                history_messages.append(HumanMessage(content=item["content"]))
            else:
                history_messages.append(AIMessage(content=item["content"]))

        messages = [
            SystemMessage(content=_build_system_prompt(state["intent"], state["context"])),
            *history_messages,
            HumanMessage(content=state["user_message"]),
        ]
        result = llm.invoke(messages)
        content = getattr(result, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass

    return _fallback_response(state)


def _extract_profile(message: str, existing: dict[str, Any]) -> dict[str, Any]:
    profile = dict(existing)
    lowered = message.lower()

    for skin_type in SKIN_TYPES:
        if skin_type in lowered:
            profile["skin_type"] = skin_type

    concerns = list(profile.get("concerns", []))
    for concern in PROFILE_CONCERNS:
        if concern in lowered and concern not in concerns:
            concerns.append(concern)
    if concerns:
        profile["concerns"] = concerns

    if any(term in lowered for term in ["fragrance-free", "fragrance free", "no fragrance"]):
        profile["preferences"] = "fragrance-free"
    if any(term in lowered for term in ["budget", "affordable", "cheaper", "low cost"]):
        profile["budget"] = "budget-friendly"
    if any(term in lowered for term in ["premium", "luxury", "high-end"]):
        profile["budget"] = "premium"

    return profile


def _node_classify(state: AgentState, history: list[dict[str, str]], profile: dict[str, Any]) -> AgentState:
    state["intent"] = _classify_intent(state["user_message"], history, profile)
    state["should_escalate"] = state["intent"] == "escalation"
    return state


def _node_gather_context(
    state: AgentState,
    db: Session,
    history: list[dict[str, str]],
    profile: dict[str, Any],
) -> AgentState:
    retrieval_query = build_retrieval_query(state["user_message"], profile=profile, history=history)
    products = search_products(db, retrieval_query, state["store_id"], profile=profile)
    policy_topic = detect_policy_topic(state["user_message"]) if state["intent"] == "policy_faq" else None
    knowledge_hits = search_knowledge(
        db,
        retrieval_query,
        state["store_id"],
        intent=state["intent"],
        policy_topic=policy_topic,
    )
    document_hits = [hit for hit in knowledge_hits if hit.get("type") != "product"]
    if policy_topic:
        document_hits = filter_policy_hits(document_hits, policy_topic)
    knowledge_text = format_knowledge_context(document_hits)

    orders_text = ""
    order_match = re.search(r"#?(\d{3,6})", state["user_message"])
    if order_match:
        order_number = f"#{order_match.group(1)}"
        order = (
            db.query(Order)
            .filter(Order.store_id == state["store_id"], Order.shopify_order_id == order_number)
            .first()
        )
        if order:
            orders_text = (
                f"Order {order.shopify_order_id} status: {order.status}. "
                f"Tracking number: {order.tracking_number or 'not available yet'}."
            )
        else:
            orders_text = f"No order found for {order_number}. Ask the customer to verify the order number and checkout email."
    elif state["intent"] == "order_support":
        orders_text = "No order number provided yet. Ask for order number and checkout email before stating any order status."

    state["context"] = {
        "products": _format_products(products),
        "product_objects": products,
        "knowledge": knowledge_text,
        "knowledge_hits": document_hits,
        "policy_topic": policy_topic,
        "orders": orders_text,
        "profile": profile,
    }
    state["sources"] = [hit["source"] for hit in knowledge_hits]
    return state


def _node_respond(state: AgentState, db: Session, history: list[dict[str, str]]) -> AgentState:
    state["response"] = _llm_response(state, history)

    conversation = db.query(Conversation).filter(Conversation.id == state["conversation_id"]).first()
    if conversation:
        profile = _extract_profile(state["user_message"], (conversation.meta or {}).get("profile", {}))
        conversation.meta = {**(conversation.meta or {}), "profile": profile, "last_intent": state["intent"]}
        if state["should_escalate"]:
            conversation.is_escalated = True
            conversation.status = "escalated"
        db.add(conversation)

    return state


def build_agent_graph(db: Session, history: list[dict[str, str]], profile: dict[str, Any]):
    graph = StateGraph(AgentState)
    graph.add_node("classify", lambda state: _node_classify(state, history, profile))
    graph.add_node("gather_context", lambda state: _node_gather_context(state, db, history, profile))
    graph.add_node("respond", lambda state: _node_respond(state, db, history))
    graph.set_entry_point("classify")
    graph.add_edge("classify", "gather_context")
    graph.add_edge("gather_context", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def generate_agent_reply(
    db: Session,
    *,
    store_id: int,
    conversation_id: int,
    user_message: str,
) -> dict[str, Any]:
    history = [
        {"role": message.role, "content": message.content}
        for message in (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
    ]

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    profile = (conversation.meta or {}).get("profile", {}) if conversation else {}

    initial_state: AgentState = {
        "store_id": store_id,
        "conversation_id": conversation_id,
        "user_message": user_message,
        "intent": "general",
        "context": {},
        "response": "",
        "should_escalate": False,
        "sources": [],
    }

    graph = build_agent_graph(db, history, profile)
    result = graph.invoke(initial_state)
    return {
        "content": result["response"],
        "intent": result["intent"],
        "should_escalate": result["should_escalate"],
        "sources": result.get("sources", []),
    }
