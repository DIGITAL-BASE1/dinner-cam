import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from google.cloud import firestore
from models.user_profile import UserProfile, UserProfileUpdate, RecipeFeedback, CookingSession
import os

class ProfileStorageService:
    def __init__(self):
        self.db = firestore.Client()
        self.profiles_collection = "user_profiles"
        self.feedback_collection = "recipe_feedback"
        self.sessions_collection = "cooking_sessions"
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """ユーザープロファイルを取得"""
        try:
            doc_ref = self.db.collection(self.profiles_collection).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # datetimeフィールドの変換
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = data['created_at'].replace(tzinfo=None)
                if 'updated_at' in data and data['updated_at']:
                    data['updated_at'] = data['updated_at'].replace(tzinfo=None)
                
                return UserProfile(**data)
            return None
        except Exception as e:
            print(f"[ERROR] プロファイル取得エラー (user_id: {user_id}): {e}")
            return None
    
    async def create_user_profile(self, user_id: str, profile_data: Dict[str, Any] = None) -> UserProfile:
        """新規ユーザープロファイルを作成"""
        try:
            # デフォルトプロファイルを作成
            default_profile = UserProfile(user_id=user_id)
            
            # 追加データがあれば適用
            if profile_data:
                profile_dict = default_profile.dict()
                profile_dict.update(profile_data)
                profile = UserProfile(**profile_dict)
            else:
                profile = default_profile
            
            # Firestoreに保存
            doc_ref = self.db.collection(self.profiles_collection).document(user_id)
            profile_dict = profile.dict()
            
            # datetime オブジェクトをタイムスタンプに変換
            for key, value in profile_dict.items():
                if isinstance(value, datetime):
                    profile_dict[key] = value
            
            doc_ref.set(profile_dict)
            
            print(f"[INFO] 新規プロファイル作成完了: {user_id}")
            return profile
            
        except Exception as e:
            print(f"[ERROR] プロファイル作成エラー (user_id: {user_id}): {e}")
            raise
    
    async def update_user_profile(self, user_id: str, updates: UserProfileUpdate) -> Optional[UserProfile]:
        """ユーザープロファイルを更新"""
        try:
            doc_ref = self.db.collection(self.profiles_collection).document(user_id)
            
            # 更新データを準備
            update_data = {}
            for field, value in updates.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            
            # 更新時刻を追加
            update_data['updated_at'] = datetime.utcnow()
            update_data['version'] = firestore.Increment(1)
            
            # Firestoreを更新
            doc_ref.update(update_data)
            
            # 更新後のプロファイルを取得
            updated_profile = await self.get_user_profile(user_id)
            print(f"[INFO] プロファイル更新完了: {user_id}")
            return updated_profile
            
        except Exception as e:
            print(f"[ERROR] プロファイル更新エラー (user_id: {user_id}): {e}")
            return None
    
    async def get_or_create_profile(self, user_id: str, user_info: Dict[str, Any] = None) -> UserProfile:
        """プロファイルを取得、なければ作成"""
        profile = await self.get_user_profile(user_id)
        
        if profile is None:
            # 初回ログイン時の基本情報を設定
            initial_data = {}
            if user_info:
                if 'name' in user_info:
                    initial_data['display_name'] = user_info['name']
            
            profile = await self.create_user_profile(user_id, initial_data)
        
        return profile
    
    async def add_recipe_feedback(self, user_id: str, feedback: RecipeFeedback) -> bool:
        """レシピフィードバックを追加"""
        try:
            # フィードバックをサブコレクションに保存
            feedback_ref = (self.db.collection(self.profiles_collection)
                          .document(user_id)
                          .collection(self.feedback_collection)
                          .document())
            
            feedback_dict = feedback.dict()
            # datetime オブジェクトをタイムスタンプに変換
            if 'created_at' in feedback_dict:
                feedback_dict['created_at'] = feedback_dict['created_at']
            
            feedback_ref.set(feedback_dict)
            
            # メインプロファイルのフィードバック履歴も更新
            profile_ref = self.db.collection(self.profiles_collection).document(user_id)
            profile_ref.update({
                f'recipe_feedback.{feedback.recipe_id}': {
                    'rating': feedback.rating,
                    'last_feedback': feedback_dict['created_at'],
                    'feedback_count': firestore.Increment(1)
                },
                'updated_at': datetime.utcnow()
            })
            
            print(f"[INFO] レシピフィードバック追加: {user_id} -> {feedback.recipe_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] フィードバック追加エラー: {e}")
            return False
    
    async def add_cooking_session(self, user_id: str, session: CookingSession) -> bool:
        """調理セッションを記録"""
        try:
            # セッションをサブコレクションに保存
            session_ref = (self.db.collection(self.profiles_collection)
                          .document(user_id)
                          .collection(self.sessions_collection)
                          .document(session.session_id))
            
            session_dict = session.dict()
            # datetime オブジェクトをタイムスタンプに変換
            if 'created_at' in session_dict:
                session_dict['created_at'] = session_dict['created_at']
            
            session_ref.set(session_dict)
            
            # メインプロファイルの調理履歴も更新
            profile_ref = self.db.collection(self.profiles_collection).document(user_id)
            
            # 最近の調理履歴を追加（最新10件を保持）
            current_profile = await self.get_user_profile(user_id)
            if current_profile:
                cooking_history = current_profile.cooking_history.copy()
                cooking_history.append({
                    'session_id': session.session_id,
                    'recipe_name': session.recipe_name,
                    'date': session_dict['created_at'],
                    'success_rating': session.success_rating
                })
                
                # 最新10件のみ保持
                if len(cooking_history) > 10:
                    cooking_history = cooking_history[-10:]
                
                profile_ref.update({
                    'cooking_history': cooking_history,
                    'updated_at': datetime.utcnow()
                })
            
            print(f"[INFO] 調理セッション記録: {user_id} -> {session.session_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] セッション記録エラー: {e}")
            return False
    
    async def get_user_preferences_summary(self, user_id: str) -> Dict[str, Any]:
        """ユーザーの嗜好サマリーを取得（エージェント用）"""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return {}
            
            return {
                'dietary_restrictions': profile.dietary_restrictions,
                'allergies': profile.allergies,
                'disliked_ingredients': profile.disliked_ingredients,
                'preferred_cuisines': profile.preferred_cuisines,
                'favorite_ingredients': profile.favorite_ingredients,
                'spice_tolerance': profile.spice_tolerance,
                'sweetness_preference': profile.sweetness_preference,
                'cooking_skill_level': profile.cooking_skill_level,
                'available_cooking_time': profile.available_cooking_time,
                'health_goals': profile.health_goals,
                'daily_calorie_target': profile.daily_calorie_target,
                'family_size': profile.family_size,
                'kitchen_equipment': profile.kitchen_equipment
            }
            
        except Exception as e:
            print(f"[ERROR] 嗜好サマリー取得エラー: {e}")
            return {}
    
    async def get_recent_feedback(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """最近のフィードバックを取得"""
        try:
            feedback_ref = (self.db.collection(self.profiles_collection)
                          .document(user_id)
                          .collection(self.feedback_collection)
                          .order_by('created_at', direction=firestore.Query.DESCENDING)
                          .limit(limit))
            
            docs = feedback_ref.stream()
            feedback_list = []
            
            for doc in docs:
                data = doc.to_dict()
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'], 'isoformat') else str(data['created_at'])
                feedback_list.append(data)
            
            return feedback_list
            
        except Exception as e:
            print(f"[ERROR] フィードバック取得エラー: {e}")
            return []
    
    async def get_cooking_stats(self, user_id: str) -> Dict[str, Any]:
        """調理統計を取得"""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return {}
            
            # 基本統計
            stats = {
                'total_recipes_tried': len(profile.cooking_history),
                'average_success_rating': 0,
                'favorite_cuisines': [],
                'most_used_ingredients': [],
                'cooking_frequency': 0
            }
            
            # 成功率の計算
            if profile.cooking_history:
                success_ratings = [h.get('success_rating', 0) for h in profile.cooking_history if h.get('success_rating')]
                if success_ratings:
                    stats['average_success_rating'] = sum(success_ratings) / len(success_ratings)
            
            # フィードバックから好みを抽出
            if profile.recipe_feedback:
                high_rated_recipes = [recipe_id for recipe_id, feedback in profile.recipe_feedback.items() 
                                    if feedback.get('rating', 0) >= 4]
                stats['high_rated_recipes_count'] = len(high_rated_recipes)
            
            return stats
            
        except Exception as e:
            print(f"[ERROR] 統計取得エラー: {e}")
            return {}

# シングルトンインスタンス
profile_storage = ProfileStorageService()