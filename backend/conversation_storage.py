import os
import json
import base64
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# Firebase Firestoreのインポート（エラー時はメモリモード）
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

class LineStyleConversationStorage:
    def __init__(self):
        self.JST = timezone(timedelta(hours=9))
        self.db = None
        self.backend = "memory"
        self.firebase_initialized = False
        self.user_messages = {}  # メモリフォールバック用
        
        # 即座にメモリモードで開始（ブロッキングを避ける）
        self._init_memory()
        
        # Firebaseは非同期で初期化を試行
        if FIREBASE_AVAILABLE:
            # バックグラウンドでFirebase初期化を開始
            asyncio.create_task(self._async_init_firebase())
    
    async def _async_init_firebase(self):
        """Firebase初期化を非同期で実行"""
        try:
            # Firebase Admin SDKが既に初期化されているかチェック
            try:
                firebase_admin.get_app()
                self.db = firestore.client()
                self.backend = "firebase"
                self.firebase_initialized = True
                return
            except ValueError:
                # まだ初期化されていない場合
                pass
            
            # タイムアウト付きでFirebase初期化を実行
            await asyncio.wait_for(self._try_firebase_init(), timeout=10.0)
            
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            pass
    
    async def _try_firebase_init(self):
        """Firebase初期化を実際に試行"""
        # 方法1: Base64エンコードされたFirebaseサービスアカウントキー（推奨）
        firebase_base64_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON_BASE64')
        if firebase_base64_json:
            try:
                # Base64デコード
                decoded_json = base64.b64decode(firebase_base64_json).decode('utf-8')
                credentials_dict = json.loads(decoded_json)
                
                # Firebase Admin SDK初期化
                cred = credentials.Certificate(credentials_dict)
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.backend = "firebase"
                self.firebase_initialized = True
                return
            except Exception as e:
                pass
        
        # 方法2: 通常のJSON文字列（フォールバック）
        firebase_service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if firebase_service_account_json:
            try:
                credentials_dict = json.loads(firebase_service_account_json)
                cred = credentials.Certificate(credentials_dict)
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.backend = "firebase"
                self.firebase_initialized = True
                return
            except Exception as e:
                pass
        
        # 方法3: ファイルパス方式
        firebase_key_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
        if firebase_key_path and os.path.exists(firebase_key_path):
            try:
                cred = credentials.Certificate(firebase_key_path)
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.backend = "firebase"
                self.firebase_initialized = True
                return
            except Exception as e:
                pass
        
        # 方法4: デフォルト認証
        try:
            firebase_admin.initialize_app()
            self.db = firestore.client()
            self.backend = "firebase"
            self.firebase_initialized = True
            return
        except Exception as e:
            pass
        
        # すべて失敗
        raise Exception("すべてのFirebase初期化方法が失敗しました")
    
    def _init_memory(self):
        """メモリモードで初期化"""
        self.user_messages = {}
        self.backend = "memory"
    
    def _get_jst_now(self) -> datetime:
        return datetime.now(self.JST)
    
    async def _ensure_firebase_ready(self):
        """Firebase準備完了を確認（必要に応じて待機）"""
        if self.firebase_initialized:
            return True
        
        # Firebase初期化が完了するまで最大5秒待機
        for _ in range(50):  # 0.1秒 × 50回 = 5秒
            if self.firebase_initialized:
                return True
            await asyncio.sleep(0.1)
        
        return False
    
    # === Firebase Firestore Methods ===
    async def _firebase_get_messages(self, user_id: str) -> List[Dict]:
        """ユーザーの全メッセージを取得"""
        try:
            if not await self._ensure_firebase_ready():
                return await self._memory_get_messages(user_id)
            
            doc_ref = self.db.collection('user_conversations').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                messages = data.get('messages', [])
                return messages
            else:
                return []
        except Exception as e:
            return await self._memory_get_messages(user_id)
    
    async def _firebase_save_messages(self, user_id: str, messages: List[Dict]) -> bool:
        """ユーザーの全メッセージを保存"""
        try:
            if not await self._ensure_firebase_ready():
                return await self._memory_save_messages(user_id, messages)
            
            doc_ref = self.db.collection('user_conversations').document(user_id)
            
            doc_ref.set({
                'user_id': user_id,
                'messages': messages,
                'message_count': len(messages),
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_message_at': firestore.SERVER_TIMESTAMP if messages else None
            }, merge=True)
            
            return True
        except Exception as e:
            return await self._memory_save_messages(user_id, messages)
    
    async def _firebase_add_message(self, user_id: str, message: Dict) -> bool:
        """新しいメッセージを追加"""
        try:
            if not await self._ensure_firebase_ready():
                return await self._memory_add_message(user_id, message)
            
            doc_ref = self.db.collection('user_conversations').document(user_id)
            
            # Firebase Firestoreのトランザクション
            @firestore.transactional
            def add_message_transaction(transaction, doc_ref, message):
                doc = doc_ref.get(transaction=transaction)
                
                if doc.exists:
                    data = doc.to_dict()
                    messages = data.get('messages', [])
                else:
                    messages = []
                
                messages.append(message)
                
                transaction.set(doc_ref, {
                    'user_id': user_id,
                    'messages': messages,
                    'message_count': len(messages),
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'last_message_at': firestore.SERVER_TIMESTAMP
                }, merge=True)
            
            transaction = self.db.transaction()
            add_message_transaction(transaction, doc_ref, message)
            
            return True
        except Exception as e:
            return await self._memory_add_message(user_id, message)
    
    async def _firebase_clear_messages(self, user_id: str) -> bool:
        """ユーザーの全メッセージをクリア"""
        try:
            if not await self._ensure_firebase_ready():
                return await self._memory_clear_messages(user_id)
            
            doc_ref = self.db.collection('user_conversations').document(user_id)
            doc_ref.delete()
            return True
        except Exception as e:
            return await self._memory_clear_messages(user_id)
    
    # === Memory Methods ===
    async def _memory_get_messages(self, user_id: str) -> List[Dict]:
        """ユーザーの全メッセージを取得"""
        messages = self.user_messages.get(user_id, [])
        return messages
    
    async def _memory_save_messages(self, user_id: str, messages: List[Dict]) -> bool:
        """ユーザーの全メッセージを保存"""
        self.user_messages[user_id] = messages
        return True
    
    async def _memory_add_message(self, user_id: str, message: Dict) -> bool:
        """新しいメッセージを追加"""
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        
        self.user_messages[user_id].append(message)
        return True
    
    async def _memory_clear_messages(self, user_id: str) -> bool:
        """ユーザーの全メッセージをクリア"""
        if user_id in self.user_messages:
            del self.user_messages[user_id]
        return True
    
    # === Public Interface ===
    async def get_user_messages(self, user_id: str) -> List[Dict]:
        """ユーザーの全メッセージを取得（LINEスタイル）"""
        if self.backend == "firebase" or self.firebase_initialized:
            return await self._firebase_get_messages(user_id)
        else:
            return await self._memory_get_messages(user_id)
    
    async def save_user_messages(self, user_id: str, messages: List[Dict]) -> bool:
        """ユーザーの全メッセージを保存"""
        if self.backend == "firebase" or self.firebase_initialized:
            return await self._firebase_save_messages(user_id, messages)
        else:
            return await self._memory_save_messages(user_id, messages)
    
    async def add_user_message(self, user_id: str, message: Dict) -> bool:
        """新しいメッセージを追加"""
        if self.backend == "firebase" or self.firebase_initialized:
            return await self._firebase_add_message(user_id, message)
        else:
            return await self._memory_add_message(user_id, message)
    
    async def clear_user_messages(self, user_id: str) -> bool:
        """ユーザーの全メッセージをクリア（新規会話開始）"""
        if self.backend == "firebase" or self.firebase_initialized:
            return await self._firebase_clear_messages(user_id)
        else:
            return await self._memory_clear_messages(user_id)
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """ユーザーの統計情報を取得"""
        messages = await self.get_user_messages(user_id)
        
        total_messages = len(messages)
        user_messages = len([m for m in messages if m.get('type') == 'user'])
        bot_messages = len([m for m in messages if m.get('type') == 'bot'])
        
        # 最初と最後のメッセージ時刻
        first_message_time = None
        last_message_time = None
        
        if messages:
            first_message_time = messages[0].get('timestamp')
            last_message_time = messages[-1].get('timestamp')
        
        return {
            'total_messages': total_messages,
            'user_messages': user_messages,
            'bot_messages': bot_messages,
            'first_message_time': first_message_time,
            'last_message_time': last_message_time,
            'backend': self.backend,
            'firebase_initialized': self.firebase_initialized
        }

# シングルトンインスタンス
line_conversation_storage = LineStyleConversationStorage()