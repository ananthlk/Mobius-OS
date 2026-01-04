"""
Gmail OAuth API Endpoints
Handles OAuth2 flow for Gmail API access.
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional
from nexus.modules.gmail_oauth import gmail_oauth_service
from nexus.modules.database import database
from nexus.modules.user_manager import user_manager

logger = logging.getLogger("nexus.gmail_endpoints")

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    user_id: Optional[str] = None  # Can be extracted from state or session


@router.get("/oauth/authorize")
async def get_authorization_url(
    user_id: str = Query(..., description="User identifier"),
    state: Optional[str] = None
):
    """
    Generate OAuth2 authorization URL for Gmail access.
    User should be redirected to this URL to authorize Gmail access.
    """
    try:
        auth_url = gmail_oauth_service.get_authorization_url(user_id, state)
        
        if not auth_url:
            raise HTTPException(
                status_code=500,
                detail="Gmail OAuth not configured. Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables."
            )
        
        return {
            "authorization_url": auth_url,
            "user_id": user_id,
            "message": "Redirect user to authorization_url to complete OAuth flow"
        }
    except Exception as e:
        logger.error(f"Failed to generate authorization URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter (should contain user_id)"),
    error: Optional[str] = Query(None, description="OAuth error if authorization denied")
):
    """
    Handle OAuth2 callback from Google.
    Exchanges authorization code for tokens and stores them.
    """
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth authorization denied: {error}"
        )
    
    try:
        from google_auth_oauthlib.flow import Flow
        from google.oauth2.credentials import Credentials
        import os
        
        client_id = os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        redirect_uri = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/gmail/oauth/callback")
        
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=500,
                detail="Gmail OAuth not configured"
            )
        
        # Create flow and exchange code for tokens
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        flow.redirect_uri = redirect_uri
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Get user information from Google
        user_info = await gmail_oauth_service.get_user_info(credentials)
        if not user_info:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve user information from Google"
            )
        
        # Extract user information
        google_auth_id = user_info.get('sub')  # Google user ID
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')
        locale = user_info.get('locale')
        
        if not google_auth_id or not email:
            raise HTTPException(
                status_code=500,
                detail="Missing required user information from Google"
            )
        
        # Find or create user in the system
        existing_user = await user_manager.get_user_by_auth_id(google_auth_id)
        
        if existing_user:
            # User exists - update with latest info
            user_id = existing_user['id']
            updates = {}
            if name and name != existing_user.get('name'):
                updates['name'] = name
            if email and email != existing_user.get('email'):
                updates['email'] = email
            
            if updates:
                await user_manager.update_user(user_id, updates, {"user_id": "system"})
            
            # Store Google profile info in user profile metadata
            await user_manager.update_user_profile(
                user_id,
                metadata={
                    'google_picture': picture,
                    'google_locale': locale,
                    'google_email_verified': user_info.get('email_verified', False)
                }
            )
        else:
            # Create new user
            user_id = await user_manager.create_user(
                auth_id=google_auth_id,
                email=email,
                name=name,
                role="user",
                user_context={"user_id": "system"}
            )
            
            # Store Google profile info in user profile metadata
            await user_manager.update_user_profile(
                user_id,
                metadata={
                    'google_picture': picture,
                    'google_locale': locale,
                    'google_email_verified': user_info.get('email_verified', False),
                    'created_via_oauth': True
                }
            )
        
        # Store Gmail OAuth credentials (use user_id as integer)
        success = await gmail_oauth_service.store_credentials(str(user_id), credentials, email)
        
        if not success:
            logger.warning(f"Failed to store Gmail OAuth credentials for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "auth_id": google_auth_id,
            "email": email,
            "name": name,
            "picture": picture,
            "locale": locale,
            "user_created": existing_user is None,
            "message": "Gmail OAuth authorization successful. User account created/updated."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.get("/accounts")
async def list_user_accounts(
    user_id: str = Query(..., description="User identifier")
):
    """
    List all Gmail accounts connected for a user.
    """
    try:
        accounts = await gmail_oauth_service.list_user_emails(user_id)
        return {
            "user_id": user_id,
            "accounts": accounts,
            "count": len(accounts)
        }
    except Exception as e:
        logger.error(f"Failed to list user accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{email}")
async def disconnect_account(
    email: str,
    user_id: str = Query(..., description="User identifier")
):
    """
    Disconnect a Gmail account (remove stored tokens).
    """
    try:
        query = """
            DELETE FROM gmail_oauth_tokens
            WHERE user_id = :user_id AND email = :email
        """
        await database.execute(query, {
            'user_id': user_id,
            'email': email
        })
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "message": "Gmail account disconnected"
        }
    except Exception as e:
        logger.error(f"Failed to disconnect account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

