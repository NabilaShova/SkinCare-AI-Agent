from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Message, Order, Product
from app.services.rag import search_knowledge, search_products

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
]

ESCALATION_PATTERNS = [
    r"\brefund dispute\b",
    r"\bchargeback\b",
    r"\bnot happy\b",
    r"\bangry\b",
    r"\bspeak to (a )?human\b",
    r"\bmanager\b",
    r"\bterrible service\b",
]


def _classify_intent(message: str) -> Intent:
    lowered = message.lower()

    if any(re.search(pattern, lowered) for pattern in MEDICAL_PATTERNS):
        return "medical_safety"
    if any(re.search(pattern, lowered) for pattern in ESCALATION_PATTERNS):
        return "escalation"
    if any(term in lowered for term in ["where is my order", "tracking", "shipped", "order status", "order #", "order number"]):
        return "order_support"
    if any(term in lowered for term in ["ship", "shipping", "delivery", "international", "return", "refund", "policy"]):
        return "policy_faq"
    if any(term in lowered for term in ["niacinamide", "vitamin c", "retinol", "salicylic", "ingredient", "can i use", "compatible", "mix"]):
        return "ingredient_question"
    if any(
        term in lowered
        for term in [
            "recommend",
            "routine",
            "best for",
            "which product",
            "oily",
            "dry",
            "acne",
            "sensitive",
            "moisturizer",
            "serum",
            "cleanser",
            "sunscreen",
            "help me choose",
            "skin type",
        ]
    ):
        return "product_recommendation"
    return "general"


def _format_products(products: list[Product]) -> str:
    if not products:
        return "I could not find matching products in the current store catalog."

    lines = []
    for product in products:
        lines.append(
            f"- {product.title} ({product.price}): {product.description} "
            f"Key ingredients: {product.ingredients}"
        )
    return "\n".join(lines)


def _build_system_prompt(intent: str, context: dict[str, Any]) -> str:
    return (
        "You are a knowledgeable skincare advisor for a Shopify beauty store. "
        "Be warm, concise, and conversational. "
        "Only recommend products from the provided catalog. "
        "Never diagnose diseases, prescribe medication, or claim medical cures. "
        "For medical concerns, recommend consulting a dermatologist. "
        f"Current intent: {intent}. "
        f"Store catalog:\n{context.get('products', 'No products available.')}\n"
        f"Knowledge context:\n{context.get('knowledge', 'No extra knowledge retrieved.')}\n"
        f"Order context:\n{context.get('orders', 'No order data retrieved.')}\n"
        f"Conversation profile:\n{context.get('profile', {})}"
    )


def _fallback_response(state: AgentState) -> str:
    intent = state["intent"]
    context = state["context"]
    products = context.get("product_objects", [])
    knowledge = context.get("knowledge", "")
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
                f"I found your recent order details:\n{orders}\n"
                "If this is not the right order, share your order number and email used at checkout."
            )
        return (
            "I can help check order status. Please share your order number (for example, #3452) "
            "and the email used at checkout."
        )

    if intent == "policy_faq":
        return (
            f"Here is what I found in the store policies:\n{knowledge}\n"
            "Let me know if you need help with a specific order or product next."
        )

    if intent == "ingredient_question":
        return (
            f"Here is guidance based on our ingredient knowledge:\n{knowledge}\n"
            "If you want, I can also suggest products from the catalog that fit your skin goals."
        )

    if intent == "product_recommendation" and products:
        lead = products[0]
        extras = products[1:3]
        response = (
            f"Based on what you shared, I'd start with **{lead.title}** ({lead.price}). "
            f"{lead.description} It includes {lead.ingredients}."
        )
        if extras:
            names = ", ".join(item.title for item in extras)
            response += f" You may also like: {names}."
        response += " Would you like a morning and night routine built from these products?"
        return response

    if products:
        names = ", ".join(item.title for item in products[:3])
        return f"I can help with that. Popular options in our catalog include: {names}. What is your skin type and main concern?"

    return (
        "I'd love to help. Tell me your skin type, main concerns, and whether you're looking for "
        "a single product or a full routine."
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
            temperature=0.4,
        )
        history_messages = []
        for item in history[-6:]:
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


def _node_classify(state: AgentState) -> AgentState:
    state["intent"] = _classify_intent(state["user_message"])
    state["should_escalate"] = state["intent"] == "escalation"
    return state


def _node_gather_context(state: AgentState, db: Session) -> AgentState:
    products = search_products(db, state["user_message"], state["store_id"])
    knowledge_hits = search_knowledge(db, state["user_message"], state["store_id"])
    knowledge_text = "\n".join(f"[{hit['source']}] {hit['text']}" for hit in knowledge_hits)

    orders_text = ""
    order_match = re.search(r"#?(\d{3,6})", state["user_message"])
    if order_match or state["intent"] == "order_support":
        order_number = f"#{order_match.group(1)}" if order_match else "#3452"
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

    conversation = db.query(Conversation).filter(Conversation.id == state["conversation_id"]).first()
    profile = (conversation.meta or {}).get("profile", {}) if conversation else {}

    state["context"] = {
        "products": _format_products(products),
        "product_objects": products,
        "knowledge": knowledge_text,
        "orders": orders_text,
        "profile": profile,
    }
    state["sources"] = [hit["source"] for hit in knowledge_hits]
    return state


def _node_respond(state: AgentState, db: Session, history: list[dict[str, str]]) -> AgentState:
    state["response"] = _llm_response(state, history)

    conversation = db.query(Conversation).filter(Conversation.id == state["conversation_id"]).first()
    if conversation:
        profile = dict((conversation.meta or {}).get("profile", {}))
        lowered = state["user_message"].lower()
        if "oily" in lowered:
            profile["skin_type"] = "oily"
        if "dry" in lowered:
            profile["skin_type"] = "dry"
        if "sensitive" in lowered:
            profile["skin_type"] = "sensitive"
        if "acne" in lowered:
            profile.setdefault("concerns", [])
            if "acne" not in profile["concerns"]:
                profile["concerns"].append("acne")
        conversation.meta = {**(conversation.meta or {}), "profile": profile}
        if state["should_escalate"]:
            conversation.is_escalated = True
            conversation.status = "escalated"
        db.add(conversation)

    return state


def build_agent_graph(db: Session, history: list[dict[str, str]]):
    graph = StateGraph(AgentState)
    graph.add_node("classify", _node_classify)
    graph.add_node("gather_context", lambda state: _node_gather_context(state, db))
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

    graph = build_agent_graph(db, history)
    result = graph.invoke(initial_state)
    return {
        "content": result["response"],
        "intent": result["intent"],
        "should_escalate": result["should_escalate"],
        "sources": result.get("sources", []),
    }
