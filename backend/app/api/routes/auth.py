from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.core.config import settings

router = APIRouter()

@router.get('/start')
def start_shopify_oauth():
    return RedirectResponse(
        url=f'https://{settings.SHOPIFY_APP_URL}/admin/oauth/authorize?client_id={settings.SHOPIFY_API_KEY}&scope={settings.SHOPIFY_SCOPES}&redirect_uri={settings.SHOPIFY_APP_URL}/api/auth/callback&response_type=code'
    )

@router.get('/callback')
def oauth_callback(request: Request):
    code = request.query_params.get('code')
    shop = request.query_params.get('shop')
    return {'status': 'callback received', 'shop': shop, 'code': code}
