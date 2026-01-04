"""
Unified Google OAuth Service
Manages OAuth2 authentication for both Gmail and Calendar APIs.
Users authorize once and get access to both services.
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from nexus.modules.database import database
from nexus.modules.crypto import encrypt, decrypt

logger = logging.getLogger("nexus.google_oauth")

# Combined Scopes for Gmail + Calendar + User Info
SCOPES = [
    # Gmail API
    'https://www.googleapis.com/auth/gmail.send',
    # Calendar API
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    # User Info
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# OAuth2 Configuration (from environment or Google Cloud Console)
CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")  # Reuse Gmail OAuth credentials
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/google/oauth/callback")


class GoogleOAuthService:
    """
    Unified OAuth service for Google services (Gmail + Calendar).
    Users authorize once and get access to both Gmail and Calendar APIs.
    """
    
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.redirect_uri = REDIRECT_URI
        
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials not configured (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET)")
    
    def get_authorization_url(self, user_id: str, state: Optional[str] = None) -> Optional[str]:
        """
        Generate OAuth2 authorization URL for Google services (Gmail + Calendar).
        
        Args:
            user_id: User identifier
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL or None if credentials not configured
        """
        if not self.client_id or not self.client_secret:
            return None
        
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=SCOPES
            )
            flow.redirect_uri = self.redirect_uri
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state or user_id,
                prompt='consent'  # Force consent to get refresh token
            )
            
            return authorization_url
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            return None
    
    async def get_user_info(self, credentials: Credentials) -> Optional[Dict[str, Any]]:
        """
        Fetch user information from Google's userinfo endpoint.
        
        Args:
            credentials: Google OAuth credentials object
        
        Returns:
            Dictionary with user info (sub, email, name, picture, etc.) or None
        """
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                'sub': user_info.get('id'),  # Google user ID (auth_id)
                'email': user_info.get('email'),
                'email_verified': user_info.get('verified_email', False),
                'name': user_info.get('name'),
                'given_name': user_info.get('given_name'),
                'family_name': user_info.get('family_name'),
                'picture': user_info.get('picture'),
                'locale': user_info.get('locale')
            }
        except Exception as e:
            logger.error(f"Failed to fetch user info from Google: {e}")
            return None
    
    async def store_credentials(self, user_id: str, credentials: Credentials, email: Optional[str] = None) -> bool:
        """
        Store OAuth credentials (encrypted) in database.
        Stores credentials with all scopes (Gmail + Calendar).
        
        Args:
            user_id: User identifier (can be user ID integer or auth_id string)
            credentials: Google OAuth credentials object
            email: User email address (if not provided, will try to fetch from token)
        
        Returns:
            True if stored successfully
        """
        try:
            # Get email if not provided
            if not email:
                try:
                    user_info = await self.get_user_info(credentials)
                    if user_info:
                        email = user_info.get('email', '')
                except Exception:
                    email = ''
            
            if not email:
                logger.warning(f"Could not determine email for user {user_id}")
                return False
            
            # Convert credentials to dict for storage
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri or 'https://oauth2.googleapis.com/token',
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            # Encrypt sensitive fields
            encrypted_refresh_token = encrypt(creds_dict['refresh_token']) if creds_dict['refresh_token'] else None
            encrypted_token = encrypt(creds_dict['token']) if creds_dict['token'] else None
            
            if not encrypted_refresh_token:
                logger.error("No refresh token available - cannot store credentials")
                return False
            
            # Store in database (reuse gmail_oauth_tokens table - it stores all Google OAuth tokens)
            query = """
                INSERT INTO gmail_oauth_tokens 
                (user_id, email, encrypted_token, encrypted_refresh_token, token_uri, client_id, scopes, created_at, updated_at)
                VALUES (:user_id, :email, :token, :refresh_token, :token_uri, :client_id, :scopes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, email) 
                DO UPDATE SET 
                    encrypted_token = EXCLUDED.encrypted_token,
                    encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                    token_uri = EXCLUDED.token_uri,
                    client_id = EXCLUDED.client_id,
                    scopes = EXCLUDED.scopes,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await database.execute(query, {
                'user_id': user_id,
                'email': email,
                'token': encrypted_token,
                'refresh_token': encrypted_refresh_token,
                'token_uri': creds_dict['token_uri'],
                'client_id': creds_dict['client_id'],
                'scopes': json.dumps(creds_dict['scopes'])
            })
            
            logger.info(f"Stored Google OAuth credentials (Gmail + Calendar) for user {user_id}, email {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to store Google OAuth credentials: {e}")
            return False
    
    async def get_credentials(self, user_id: str, email: Optional[str] = None) -> Optional[Credentials]:
        """
        Retrieve and build OAuth credentials for user.
        Returns credentials with all scopes (Gmail + Calendar).
        
        Args:
            user_id: User identifier
            email: Optional email filter (if user has multiple accounts)
        
        Returns:
            Credentials object or None if not found/expired
        """
        try:
            if email:
                query = """
                    SELECT encrypted_token, encrypted_refresh_token, token_uri, client_id, scopes
                    FROM gmail_oauth_tokens
                    WHERE user_id = :user_id AND email = :email
                    ORDER BY updated_at DESC
                    LIMIT 1
                """
                params = {'user_id': user_id, 'email': email}
            else:
                query = """
                    SELECT encrypted_token, encrypted_refresh_token, token_uri, client_id, scopes
                    FROM gmail_oauth_tokens
                    WHERE user_id = :user_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                """
                params = {'user_id': user_id}
            
            row = await database.fetch_one(query, params)
            if not row:
                return None
            
            # Decrypt tokens
            token = decrypt(row['encrypted_token']) if row['encrypted_token'] else None
            refresh_token = decrypt(row['encrypted_refresh_token']) if row['encrypted_refresh_token'] else None
            
            if not refresh_token:
                logger.warning(f"No refresh token found for user {user_id}")
                return None
            
            # Parse scopes
            scopes_str = row['scopes']
            if isinstance(scopes_str, str):
                try:
                    scopes_list = json.loads(scopes_str)
                except json.JSONDecodeError:
                    scopes_list = SCOPES  # Fallback to default scopes
            else:
                scopes_list = scopes_str or SCOPES
            
            # Build credentials object
            creds_dict = {
                'token': token,
                'refresh_token': refresh_token,
                'token_uri': row['token_uri'] or 'https://oauth2.googleapis.com/token',
                'client_id': row['client_id'] or self.client_id,
                'client_secret': self.client_secret,
                'scopes': scopes_list
            }
            
            credentials = Credentials.from_authorized_user_info(creds_dict, SCOPES)
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                # Update stored token
                await self.store_credentials(user_id, credentials, email)
            
            return credentials
        except Exception as e:
            logger.error(f"Failed to retrieve Google OAuth credentials: {e}")
            return None
    
    async def get_gmail_service(self, user_id: str, email: Optional[str] = None):
        """
        Get Gmail API service instance for user.
        
        Args:
            user_id: User identifier
            email: Optional email filter
        
        Returns:
            Gmail service instance or None
        """
        credentials = await self.get_credentials(user_id, email)
        if not credentials:
            return None
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            return service
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return None
    
    async def get_calendar_service(self, user_id: str, email: Optional[str] = None):
        """
        Get Google Calendar API service instance for user.
        
        Args:
            user_id: User identifier
            email: Optional email filter
        
        Returns:
            Calendar service instance or None
        """
        credentials = await self.get_credentials(user_id, email)
        if not credentials:
            return None
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            return service
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            return None
    
    async def list_user_accounts(self, user_id: str) -> list:
        """
        List all Google accounts connected for user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of email addresses with account info
        """
        try:
            query = """
                SELECT email, updated_at, scopes
                FROM gmail_oauth_tokens
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
            """
            rows = await database.fetch_all(query, {'user_id': user_id})
            return [
                {
                    'email': row['email'],
                    'updated_at': row['updated_at'],
                    'has_gmail': 'gmail' in (row['scopes'] or ''),
                    'has_calendar': 'calendar' in (row['scopes'] or '')
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list user accounts: {e}")
            return []


# Singleton instance
google_oauth_service = GoogleOAuthService()

