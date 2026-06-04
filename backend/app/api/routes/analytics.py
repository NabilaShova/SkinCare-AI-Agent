from fastapi import APIRouter
from typing import Any

router = APIRouter()

@router.get('/')
def get_analytics() -> Any:
    return {
        'metrics': [
            {'label': 'Conversation volume', 'value': '3,842', 'change': '+12%'},
            {'label': 'Resolved', 'value': '2,979', 'change': '+9%'},
            {'label': 'Escalation rate', 'value': '6.2%', 'change': '-1.5%'},
            {'label': 'AI response time', 'value': '1.9s', 'change': '-20%'}
        ],
        'trend_items': [
            {'label': 'Most asked question', 'value': 'Can I use Niacinamide with Vitamin C?'},
            {'label': 'Top recommended product', 'value': 'Oil-Free Hydrating Serum'},
            {'label': 'Top customer concern', 'value': 'Acne and oily skin'},
            {'label': 'Resolution rate', 'value': '87.3%'}
        ],
        'performance': [
            {'label': 'Product recommendation lift', 'percent': 72},
            {'label': 'Customer satisfaction', 'percent': 93},
            {'label': 'Human takeover accuracy', 'percent': 88}
        ]
    }
