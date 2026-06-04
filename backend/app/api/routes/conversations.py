from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db

router = APIRouter()

class ConversationSummary(BaseModel):
    id: int
    title: str
    customer: str
    preview: str
    last_activity: str
    status: str
    is_escalated: bool

class MessagePayload(BaseModel):
    conversation_id: int
    role: str
    content: str

class MessageItem(BaseModel):
    role: str
    content: str

class ConversationDetail(BaseModel):
    id: int
    title: str
    customer: str
    status: str
    is_escalated: bool
    messages: List[MessageItem]

conversation_store = [
    {
        'id': 1,
        'title': 'Order status inquiry',
        'customer': 'Ava',
        'preview': 'Where is my cleanser order?',
        'last_activity': '2m ago',
        'status': 'open',
        'is_escalated': False,
        'messages': [
            {'role': 'user', 'content': 'Where is my order #3452? I need it before the weekend.'},
            {'role': 'assistant', 'content': 'I see your order is currently in transit and expected to arrive by Friday. Your tracking number is TRACK12345.'}
        ]
    },
    {
        'id': 2,
        'title': 'Ingredient compatibility',
        'customer': 'Mia',
        'preview': 'Can I use Niacinamide with Vitamin C?',
        'last_activity': '12m ago',
        'status': 'open',
        'is_escalated': False,
        'messages': [
            {'role': 'user', 'content': 'Can I use Niacinamide with Vitamin C? My skin is sensitive.'},
            {'role': 'assistant', 'content': 'Yes, you can use both, but it is best to layer Vitamin C in the morning and Niacinamide at night to reduce sensitivity.'}
        ]
    },
    {
        'id': 3,
        'title': 'Product recommendation',
        'customer': 'Zoey',
        'preview': 'Best moisturizer for oily skin?',
        'last_activity': '35m ago',
        'status': 'open',
        'is_escalated': False,
        'messages': [
            {'role': 'user', 'content': 'I have oily, acne-prone skin. Which moisturizer should I use?'},
            {'role': 'assistant', 'content': 'I recommend the lightweight oil-free hydrator from your catalog. It balances moisture without clogging pores.'}
        ]
    }
]

@router.get('/', response_model=List[ConversationSummary])
def list_conversations(store_id: Optional[int] = None) -> Any:
    return [ConversationSummary(**conv) for conv in conversation_store]

@router.get('/{conversation_id}', response_model=ConversationDetail)
def get_conversation(conversation_id: int) -> Any:
    conversation = next((conv for conv in conversation_store if conv['id'] == conversation_id), None)
    if not conversation:
        raise HTTPException(status_code=404, detail='Conversation not found')
    return ConversationDetail(**conversation)

@router.post('/message')
def send_message(payload: MessagePayload) -> Any:
    conversation = next((conv for conv in conversation_store if conv['id'] == payload.conversation_id), None)
    if not conversation:
        raise HTTPException(status_code=404, detail='Conversation not found')

    conversation['messages'].append({'role': payload.role, 'content': payload.content})
    assistant_reply = {
        'role': 'assistant',
        'content': 'I’m checking your store data and order details now. I will confirm the shipping status and product guidance shortly.'
    }
    conversation['messages'].append(assistant_reply)

    return {
        'conversation_id': payload.conversation_id,
        'assistant_reply': assistant_reply,
        'messages': conversation['messages']
    }

@router.post('/escalate')
def escalate_conversation(conversation_id: int, reason: str, db: Session = Depends(get_db)) -> Any:
    conversation = next((conv for conv in conversation_store if conv['id'] == conversation_id), None)
    if not conversation:
        raise HTTPException(status_code=404, detail='Conversation not found')
    conversation['status'] = 'escalated'
    return {'conversation_id': conversation_id, 'escalated': True, 'reason': reason}
