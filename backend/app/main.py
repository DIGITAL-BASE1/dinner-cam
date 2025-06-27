from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Request as HTTPRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import sys
import shutil
import json
import asyncio
import re
from typing import AsyncGenerator, Dict, Any, Optional
from functools import wraps

# 環境変数読み込み
from dotenv import load_dotenv
load_dotenv()

from agents.vision_agent import extract_ingredients_from_image
from agents.recipe_agent import recipe_agent
from agents.generate_image_agent import image_agent
from agents.nutrition_agent import nutrition_agent
from agents.chat_agent import chat_agent
from orchestrator.handler import orchestrator

# 認証関連
from auth import google_auth, GoogleLoginRequest, get_current_user

# レート制限
from rate_limiter import rate_limiter

# LINEスタイル会話永続化
from conversation_storage import line_conversation_storage

# プロファイル管理
from services.profile_storage import profile_storage
from models.user_profile import UserProfileUpdate, RecipeFeedback, CookingSession





UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatMessage(BaseModel):
    message: str
    has_image: bool = False

class RecipeRequest(BaseModel):
    ingredients: list[str] = []
    dish_name: str = ""
    preferences: dict = {}
    with_images: bool = False
    with_nutrition: bool = True

class AdminUserRequest(BaseModel):
    user_id: str

# LINEスタイル会話関連のモデル
class ConversationMessage(BaseModel):
    id: str  # 文字列形式のユニークID
    type: str  # 'user' or 'bot'
    content: str
    timestamp: str
    image: Optional[str] = None
    recipe: Optional[str] = None
    nutritionData: Optional[Dict] = None
    stepImage: Optional[Dict] = None

class SaveMessageRequest(BaseModel):
    message: ConversationMessage

app = FastAPI(
    title="DinnerCam AI Agents API",
    description="AI-powered cooking assistant with LINE-style conversation persistence",
    version="1.0.0"
)

# CORS設定を強化
# 基本のオリジンリスト
origins = [
    "http://localhost:3000",  # React開発サーバー
    "http://localhost:5173",  # Vite開発サーバー (default)
    "http://localhost:5174",  # Vite開発サーバー (あなたの環境)
    "http://localhost:4173",  # Vite preview
    "https://dinnercam-project.web.app",  # Firebase Hosting
    "https://dinnercam-project.firebaseapp.com",
    "https://dinnercam-frontend-170801045044.asia-northeast1.run.app",  # Cloud Run Frontend
    "https://dinnercam-frontend-xqwv5teiaq-an.a.run.app",  # 動的Cloud Run Frontend URL
]

# Cloud Run の動的URLパターンに対応
def is_allowed_origin(origin: str) -> bool:
    """オリジンが許可されているかチェック"""
    if origin in origins:
        return True
    
    # Cloud Run の動的URLパターンをチェック
    patterns = [
        r"^https://dinnercam-frontend-[a-zA-Z0-9-]+\.asia-northeast1\.run\.app$",
        r"^https://dinnercam-frontend-[a-zA-Z0-9-]+\.a\.run\.app$",
        r"^https://[a-zA-Z0-9-]+-[a-zA-Z0-9-]+\.a\.run\.app$"  # 一般的なCloud Run URL
    ]
    
    for pattern in patterns:
        if re.match(pattern, origin):
            return True
    
    return False

# 環境変数で追加のオリジンを許可（本番で動的に追加可能）
additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS", "").split(",")
origins.extend([origin.strip() for origin in additional_origins if origin.strip()])

# CORS設定を動的オリジンチェックに対応
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://(dinnercam-frontend-[a-zA-Z0-9-]+\.(asia-northeast1\.run\.app|a\.run\.app)|dinnercam-project\.(web\.app|firebaseapp\.com)|localhost:[3456789][0-9]{3})$|^http://localhost:[3456789][0-9]{3}$",
    allow_origins=origins,  # フォールバックとして明示的リストも維持
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    expose_headers=["*"],
)

# セキュリティヘッダーミドルウェア追加
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    # COOP/COEPヘッダーを設定（Google OAuth対応）
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "unsafe-none"
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    
    # Permissions Policyを設定（identity-credentials-get対応）
    response.headers["Permissions-Policy"] = "identity-credentials-get=*, publickey-credentials-get=*"
    
    # その他のセキュリティヘッダー
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    
    return response

# レート制限デコレーター
def require_rate_limit(check_image_generation: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="認証が必要です")
            
            user_id = current_user['id']
            
            with_images = False
            if check_image_generation:
                payload = kwargs.get('payload')
                if payload:
                    with_images = getattr(payload, 'with_images', False)
            
            can_proceed, remaining = await rate_limiter.check_limits(user_id, with_images)
            
            if not can_proceed:
                if remaining['total_remaining'] <= 0:
                    message = f"1日の利用制限（{remaining['total_limit']}回）に達しました。明日の0時（JST）にリセットされます。⏰"
                elif with_images and remaining['image_generation_remaining'] <= 0:
                    message = f"画像生成の1日制限（{remaining['image_generation_limit']}回）に達しました。明日の0時（JST）にリセットされます。🖼️"
                else:
                    message = "利用制限に達しました。"
                
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": message,
                        "remaining": remaining,
                        "reset_time": "明日の0時（JST）"
                    }
                )
            
            result = await func(*args, **kwargs)
            await rate_limiter.increment_count(user_id, with_images)
            return result
        return wrapper
    return decorator

# 管理者権限デコレーター
def require_admin():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="認証が必要です")
            
            user_id = current_user['id']
            is_admin = await rate_limiter.is_admin(user_id)
            
            if not is_admin:
                raise HTTPException(
                    status_code=403, 
                    detail="管理者権限が必要です。アクセスが拒否されました。"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 認証エンドポイント
@app.post("/auth/google")
async def authenticate_google(request: GoogleLoginRequest):
    """Google OAuth認証エンドポイント - CORS対応済み"""
    try:
        result = await google_auth(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"認証に失敗しました: {str(e)}"
        )

# === LINEスタイル会話永続化エンドポイント ===

@app.get("/conversations/messages")
async def get_user_messages(current_user: dict = Depends(get_current_user)):
    """ユーザーの全メッセージを取得（LINEスタイル）"""
    try:
        user_id = current_user['id']
        messages = await line_conversation_storage.get_user_messages(user_id)
        
        return {
            "messages": messages,
            "message_count": len(messages),
            "backend": line_conversation_storage.backend
        }
    except Exception as e:
        return {
            "messages": [],
            "message_count": 0,
            "backend": line_conversation_storage.backend,
            "error": str(e)
        }

@app.post("/conversations/messages")
async def save_user_message(
    request: SaveMessageRequest, 
    current_user: dict = Depends(get_current_user)
):
    """新しいメッセージを保存"""
    try:
        user_id = current_user['id']
        
        # メッセージを辞書形式に変換
        message_dict = {
            "id": request.message.id,
            "type": request.message.type,
            "content": request.message.content,
            "timestamp": request.message.timestamp,
            "image": request.message.image,
            "recipe": request.message.recipe,
            "nutritionData": request.message.nutritionData,
            "stepImage": request.message.stepImage
        }
        
        success = await line_conversation_storage.add_user_message(user_id, message_dict)
        
        if success:
            return {
                "success": True,
                "message": "メッセージを保存しました",
                "backend": line_conversation_storage.backend
            }
        else:
            return {
                "success": False,
                "message": "メッセージの保存に失敗しました",
                "backend": line_conversation_storage.backend
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"メッセージの保存に失敗しました: {str(e)}"
        )

@app.delete("/conversations/messages")
async def clear_user_messages(current_user: dict = Depends(get_current_user)):
    """ユーザーの全メッセージをクリア（新規会話開始）"""
    try:
        user_id = current_user['id']
        success = await line_conversation_storage.clear_user_messages(user_id)
        
        if success:
            return {
                "success": True,
                "message": "会話履歴をクリアしました",
                "backend": line_conversation_storage.backend
            }
        else:
            return {
                "success": False,
                "message": "会話履歴のクリアに失敗しました",
                "backend": line_conversation_storage.backend
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"会話履歴のクリアに失敗しました: {str(e)}"
        )

@app.get("/conversations/stats")
async def get_user_conversation_stats(current_user: dict = Depends(get_current_user)):
    """ユーザーの会話統計情報を取得"""
    try:
        user_id = current_user['id']
        stats = await line_conversation_storage.get_user_stats(user_id)
        
        return {
            **stats,
            "user_email": current_user['email'],
            "user_name": current_user['name']
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"会話統計の取得に失敗しました: {str(e)}"
        )

# プロファイル自動更新用のヘルパー関数
async def update_profile_from_conversation(user_id: str, profile_info: Dict[str, Any]):
    """会話から抽出したプロファイル情報でユーザープロファイルを更新"""
    try:
        # 現在のプロファイルを取得
        current_profile = await profile_storage.get_user_profile(user_id)
        if not current_profile:
            print(f"[WARN] ユーザー {user_id} のプロファイルが見つかりません")
            return
        
        # 更新データを構築
        update_data = {}
        
        # 既存の値と比較して新しい情報のみ追加
        if profile_info.get("dietary_restrictions"):
            existing = set(current_profile.dietary_restrictions or [])
            new_restrictions = set(profile_info["dietary_restrictions"])
            if not new_restrictions.issubset(existing):
                update_data["dietary_restrictions"] = list(existing | new_restrictions)
        
        if profile_info.get("allergies"):
            existing = set(current_profile.allergies or [])
            new_allergies = set(profile_info["allergies"])
            if not new_allergies.issubset(existing):
                update_data["allergies"] = list(existing | new_allergies)
        
        if profile_info.get("cooking_skill_level") and profile_info["cooking_skill_level"] != current_profile.cooking_skill_level:
            update_data["cooking_skill_level"] = profile_info["cooking_skill_level"]
        
        if profile_info.get("available_cooking_time") and profile_info["available_cooking_time"] != current_profile.available_cooking_time:
            update_data["available_cooking_time"] = profile_info["available_cooking_time"]
        
        if profile_info.get("preferred_cuisines"):
            existing = set(current_profile.preferred_cuisines or [])
            new_cuisines = set(profile_info["preferred_cuisines"])
            if not new_cuisines.issubset(existing):
                update_data["preferred_cuisines"] = list(existing | new_cuisines)
        
        if profile_info.get("family_size") and profile_info["family_size"] != current_profile.family_size:
            update_data["family_size"] = profile_info["family_size"]
        
        if profile_info.get("health_goals"):
            existing = set(current_profile.health_goals or [])
            new_goals = set(profile_info["health_goals"])
            if not new_goals.issubset(existing):
                update_data["health_goals"] = list(existing | new_goals)
        
        if profile_info.get("disliked_ingredients"):
            existing = set(current_profile.disliked_ingredients or [])
            new_dislikes = set(profile_info["disliked_ingredients"])
            if not new_dislikes.issubset(existing):
                update_data["disliked_ingredients"] = list(existing | new_dislikes)
        
        # 更新がある場合のみプロファイルを更新
        if update_data:
            from models.user_profile import UserProfileUpdate
            profile_update = UserProfileUpdate(**update_data)
            await profile_storage.update_user_profile(user_id, profile_update)
            print(f"[INFO] ユーザー {user_id} のプロファイルを自動更新: {list(update_data.keys())}")
        
    except Exception as e:
        print(f"[ERROR] プロファイル自動更新エラー: {e}")

# メインAPIエンドポイント
@app.post("/chat")
@require_rate_limit()
async def chat_endpoint(payload: ChatMessage, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user['id']
        intent_result = chat_agent.analyze_user_intent(payload.message, payload.has_image)
        response = chat_agent.generate_response(intent_result)
        chat_agent.add_to_context(payload.message, response)
        
        # プロファイル情報を自動更新（非同期処理）
        profile_info = intent_result.get("profile_info", {})
        if profile_info and profile_info.get("confidence", 0) > 0.7:
            # バックグラウンドで実行（レスポンスをブロックしない）
            import asyncio
            asyncio.create_task(update_profile_from_conversation(user_id, profile_info))
        
        return {
            "response": response,
            "intent": intent_result["intent"].value,
            "confidence": intent_result["confidence"],
            "response_type": intent_result["response_type"],
            "extracted_data": intent_result["extracted_data"],
# デバッグ用: プロファイル情報も返す（一時的）
        }
    except Exception as e:
        return {
            "response": "申し訳ございません。エラーが発生しました。もう一度お試しください。🙏",
            "intent": "error",
            "confidence": 0.0,
            "response_type": "error_response",
            "extracted_data": {}
        }

@app.post("/analyze")
@require_rate_limit()
async def analyze(image: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    image_path = os.path.join(UPLOAD_DIR, image.filename)
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    ingredients = extract_ingredients_from_image(image_path)
    
    try:
        os.remove(image_path)
    except:
        pass
    
    return {"ingredients": ingredients}

async def generate_recipe_stream(
    ingredients: list[str], 
    dish_name: str = "", 
    preferences: dict = {}, 
    with_images: bool = False, 
    with_nutrition: bool = True,
    user_preferences: dict = None
) -> AsyncGenerator[str, None]:
    try:
        # レシピ生成（プロファイル対応）
        if dish_name:
            recipe = recipe_agent.generate_recipe_from_dish_name(dish_name, preferences, user_preferences)
        else:
            recipe = recipe_agent.generate_recipe_from_ingredients(ingredients, user_preferences)
        recipe_data = json.dumps({'type': 'recipe', 'content': recipe}, ensure_ascii=False, separators=(',', ':'))
        yield f"data: {recipe_data}\n\n"
        
        # 栄養分析
        if with_nutrition:
            analysis_target = ingredients if ingredients else [dish_name] if dish_name else ["一般的な料理"]
            nutrition_data = nutrition_agent.analyze_recipe_nutrition(recipe, analysis_target)
            nutrition_json = json.dumps({'type': 'nutrition', 'content': nutrition_data}, ensure_ascii=False, separators=(',', ':'))
            yield f"data: {nutrition_json}\n\n"
        
        if not with_images:
            complete_data = json.dumps({'type': 'complete'}, ensure_ascii=False, separators=(',', ':'))
            yield f"data: {complete_data}\n\n"
            return
        
        # 手順画像生成
        steps_text = recipe_agent.extract_steps_from_text(recipe)
        
        for i, step in enumerate(steps_text):
            try:
                generating_data = json.dumps({
                    'type': 'generating_image', 
                    'step_index': i, 
                    'step_text': step
                }, ensure_ascii=False, separators=(',', ':'))
                yield f"data: {generating_data}\n\n"
                
                image_url = await image_agent.generate_single_image_async(step)
                
                image_data = json.dumps({
                    'type': 'image', 
                    'step_index': i, 
                    'step_text': step, 
                    'image_url': image_url
                }, ensure_ascii=False, separators=(',', ':'))
                yield f"data: {image_data}\n\n"
                
            except Exception as e:
                error_data = json.dumps({
                    'type': 'image_error', 
                    'step_index': i, 
                    'step_text': step, 
                    'error': str(e)
                }, ensure_ascii=False, separators=(',', ':'))
                yield f"data: {error_data}\n\n"
        
        complete_data = json.dumps({'type': 'complete'}, ensure_ascii=False, separators=(',', ':'))
        yield f"data: {complete_data}\n\n"
        
    except Exception as e:
        error_data = json.dumps({
            'type': 'error', 
            'message': str(e)
        }, ensure_ascii=False, separators=(',', ':'))
        yield f"data: {error_data}\n\n"

@app.post("/recipe/stream")
@require_rate_limit(check_image_generation=True)
async def recipe_stream_endpoint(
    payload: RecipeRequest, 
    current_user: dict = Depends(get_current_user)
):
    try:
        # ユーザープロファイルを取得
        user_id = current_user['id']
        user_preferences = await profile_storage.get_user_preferences_summary(user_id)
        
        return StreamingResponse(
            generate_recipe_stream(
                payload.ingredients, 
                payload.dish_name, 
                payload.preferences, 
                payload.with_images, 
                payload.with_nutrition,
                user_preferences
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        raise

# ユーザー向けエンドポイント
@app.get("/rate-limits")
async def get_rate_limits(current_user: dict = Depends(get_current_user)):
    user_id = current_user['id']
    status = await rate_limiter.get_user_status(user_id)
    return status

@app.post("/reset-my-limits")
async def reset_my_limits(current_user: dict = Depends(get_current_user)):
    user_id = current_user['id']
    success = await rate_limiter.reset_user_limits(user_id)
    
    if success:
        return {
            "message": "制限をリセットしました",
            "reset_time": rate_limiter._get_jst_now().isoformat(),
            "note": "この機能は緊急時のみご利用ください"
        }
    else:
        return {
            "message": "リセットできませんでした",
            "reset_time": rate_limiter._get_jst_now().isoformat()
        }

@app.get("/next-reset")
async def get_next_reset_time(current_user: dict = Depends(get_current_user)):
    return rate_limiter.get_next_reset_time()

# 管理者向けエンドポイント
@app.get("/admin/stats")
@require_admin()
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    stats = await rate_limiter.get_all_stats()
    reset_info = rate_limiter.get_next_reset_time()
    
    return {
        **stats,
        'reset_info': reset_info
    }

@app.post("/admin/reset-user/{user_id}")
@require_admin()
async def reset_user_limits(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    success = await rate_limiter.reset_user_limits(user_id)
    
    if success:
        return {
            "message": f"ユーザー {user_id} の制限をリセットしました",
            "user_id": user_id,
            "reset_time": rate_limiter._get_jst_now().isoformat(),
            "reset_by": current_user['email']
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"ユーザー {user_id} が見つかりません"
        )

@app.post("/admin/reset-all")
@require_admin()
async def reset_all_limits(current_user: dict = Depends(get_current_user)):
    reset_count = await rate_limiter.reset_all_limits()
    
    return {
        "message": f"{reset_count}人のユーザーの制限をリセットしました",
        "reset_count": reset_count,
        "reset_time": rate_limiter._get_jst_now().isoformat(),
        "reset_by": current_user['email']
    }

@app.post("/admin/add-admin")
@require_admin()
async def add_admin_user(
    request: AdminUserRequest,
    current_user: dict = Depends(get_current_user)
):
    success = await rate_limiter.add_admin(request.user_id, current_user['id'])
    
    if success:
        return {
            "message": f"ユーザー {request.user_id} を管理者に追加しました",
            "user_id": request.user_id,
            "added_by": current_user['email'],
            "added_at": rate_limiter._get_jst_now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="管理者の追加に失敗しました"
        )

@app.delete("/admin/remove-admin/{user_id}")
@require_admin()
async def remove_admin_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    if user_id == current_user['id']:
        raise HTTPException(
            status_code=400,
            detail="自分自身の管理者権限は削除できません"
        )
    
    success = await rate_limiter.remove_admin(user_id)
    
    if success:
        return {
            "message": f"ユーザー {user_id} の管理者権限を削除しました",
            "user_id": user_id,
            "removed_by": current_user['email'],
            "removed_at": rate_limiter._get_jst_now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="管理者ユーザーが見つかりません"
        )

@app.get("/admin/check")
async def check_admin_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user['id']
    is_admin = await rate_limiter.is_admin(user_id)
    
    return {
        "user_id": user_id,
        "email": current_user['email'],
        "is_admin": is_admin
    }

# ===== プロファイル管理API =====

@app.get("/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """ユーザープロファイルを取得"""
    user_id = current_user['id']
    profile = await profile_storage.get_or_create_profile(user_id, current_user)
    return profile.model_dump()

@app.put("/profile")
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """ユーザープロファイルを更新"""
    user_id = current_user['id']
    updated_profile = await profile_storage.update_user_profile(user_id, profile_update)
    
    if updated_profile:
        return {
            "message": "プロファイルを更新しました",
            "profile": updated_profile.model_dump()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="プロファイルの更新に失敗しました"
        )

@app.get("/profile/preferences")
async def get_user_preferences(current_user: dict = Depends(get_current_user)):
    """ユーザーの嗜好サマリーを取得（エージェント用）"""
    user_id = current_user['id']
    preferences = await profile_storage.get_user_preferences_summary(user_id)
    return preferences

@app.post("/profile/feedback")
async def add_recipe_feedback(
    feedback: RecipeFeedback,
    current_user: dict = Depends(get_current_user)
):
    """レシピフィードバックを追加"""
    user_id = current_user['id']
    success = await profile_storage.add_recipe_feedback(user_id, feedback)
    
    if success:
        return {"message": "フィードバックを追加しました"}
    else:
        raise HTTPException(
            status_code=500,
            detail="フィードバックの追加に失敗しました"
        )

@app.post("/profile/cooking-session")
async def add_cooking_session(
    session: CookingSession,
    current_user: dict = Depends(get_current_user)
):
    """調理セッションを記録"""
    user_id = current_user['id']
    success = await profile_storage.add_cooking_session(user_id, session)
    
    if success:
        return {"message": "調理セッションを記録しました"}
    else:
        raise HTTPException(
            status_code=500,
            detail="調理セッションの記録に失敗しました"
        )

@app.get("/profile/feedback")
async def get_recent_feedback(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """最近のフィードバックを取得"""
    user_id = current_user['id']
    feedback_list = await profile_storage.get_recent_feedback(user_id, limit)
    return {"feedback": feedback_list}

@app.get("/profile/stats")
async def get_cooking_stats(current_user: dict = Depends(get_current_user)):
    """調理統計を取得"""
    user_id = current_user['id']
    stats = await profile_storage.get_cooking_stats(user_id)
    return stats


# レガシーエンドポイント
@app.post("/recipe")
async def recipe_endpoint(payload: RecipeRequest):
    recipe = recipe_agent.generate_recipe_from_ingredients(payload.ingredients)
    result = {"recipe": recipe}
    
    if payload.with_nutrition:
        nutrition_data = nutrition_agent.analyze_recipe_nutrition(recipe, payload.ingredients)
        result["nutrition"] = nutrition_data

    if not payload.with_images:
        return result

    steps_text = recipe_agent.extract_steps_from_text(recipe)
    image_urls = image_agent.generate_images_for_steps(steps_text)

    steps = [
        {"text": step, "image": image}
        for step, image in zip(steps_text, image_urls)
    ]

    result["steps"] = steps
    return result

@app.post("/agent")
async def agent_handler(prompt: dict):
    result = orchestrator.run_agent(prompt["message"])
    return {"result": result}

@app.post("/agent/complete")
async def agent_complete_recipe(payload: RecipeRequest):
    result = await orchestrator.generate_complete_recipe_async(
        payload.ingredients, 
        payload.with_images
    )
    return result

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "DinnerCam AI Agents",
        "version": "1.0.0",
        "timestamp": rate_limiter._get_jst_now().isoformat(),
        "rate_limiter_backend": rate_limiter.backend,
        "conversation_storage_backend": line_conversation_storage.backend
    }

@app.get("/cors/debug")
async def cors_debug_endpoint(request: HTTPRequest):
    """CORS設定のデバッグ情報を返す"""
    origin = request.headers.get("origin")
    
    return {
        "cors_debug": {
            "origin": origin,
            "is_allowed": is_allowed_origin(origin) if origin else False,
            "allowed_origins": origins,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers)
        }
    }

@app.get("/")
async def root():
    return {
        "message": "DinnerCam AI Agents API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "rate_limiter": rate_limiter.backend,
        "conversation_storage": line_conversation_storage.backend,
        "features": [
            "LINE-style conversation persistence",
            "Rate limiting with Firestore",
            "AI recipe generation",
            "Image analysis",
            "Nutrition analysis"
        ]
    }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8080)