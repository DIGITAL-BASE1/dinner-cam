import os
import jwt
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
import json

# 環境変数
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7日間

# セキュリティスキーム
security = HTTPBearer()

class GoogleLoginRequest(BaseModel):
    credential: str

class User(BaseModel):
    id: str
    email: str
    name: str
    picture: str

class AuthResponse(BaseModel):
    user: User
    token: str
    message: str

async def verify_google_token(credential: str) -> dict:
    """Googleトークンを検証してユーザー情報を取得"""
    try:
        # Google IDトークンを検証
        idinfo = id_token.verify_oauth2_token(
            credential, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        # 発行者の確認
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # ユーザー情報を抽出
        user_info = {
            'id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo['name'],
            'picture': idinfo.get('picture', '')
        }

        return user_info

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )

def create_jwt_token(user_info: dict) -> str:
    """JWTトークンを作成"""
    payload = {
        'sub': user_info['id'],
        'email': user_info['email'],
        'name': user_info['name'],
        'picture': user_info['picture'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow(),
        'iss': 'dinnercam-backend'
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    """JWTトークンを検証"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """認証が必要なエンドポイントで現在のユーザーを取得"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    user_payload = verify_jwt_token(token)
    
    return {
        'id': user_payload['sub'],
        'email': user_payload['email'],
        'name': user_payload['name'],
        'picture': user_payload['picture']
    }

# 認証エンドポイント
async def google_auth(request: GoogleLoginRequest) -> AuthResponse:
    """Google認証エンドポイント"""
    
    # Google Client IDが設定されているかチェック
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Client ID not configured"
        )
    
    try:
        # Googleトークンを検証
        user_info = await verify_google_token(request.credential)
        
        # JWTトークンを作成
        jwt_token = create_jwt_token(user_info)
        
        # ユーザー情報を返す
        user = User(**user_info)
        
        return AuthResponse(
            user=user,
            token=jwt_token,
            message="Authentication successful"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# オプション: 認証不要なエンドポイント用のユーザー情報取得
async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """認証がオプションなエンドポイントでユーザー情報を取得"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None