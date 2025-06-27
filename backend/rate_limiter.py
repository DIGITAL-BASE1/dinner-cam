import os
import json
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Tuple, List
from collections import defaultdict

# Firestoreのインポート（エラー時はメモリモード）
try:
    from google.cloud import firestore
    from google.oauth2 import service_account
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False

class RateLimiter:
    def __init__(self):
        self.DAILY_TOTAL_LIMIT = 10
        self.DAILY_IMAGE_GENERATION_LIMIT = 3
        self.JST = timezone(timedelta(hours=9))
        
        if FIRESTORE_AVAILABLE and os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY'):
            self._init_firestore()
        else:
            self._init_memory()
    
    def _init_firestore(self):
        try:
            service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
            credentials_dict = json.loads(service_account_info)
            credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            self.db = firestore.Client(credentials=credentials, project=credentials_dict['project_id'])
            self.backend = "firestore"
            self._init_admin_users_firestore()
        except Exception as e:
            self._init_memory()
    
    def _init_memory(self):
        self.daily_counts = defaultdict(lambda: {
            'date': None,
            'total_requests': 0,
            'image_generation_requests': 0
        })
        self.admin_users = set()
        admin_ids = os.getenv('ADMIN_USER_IDS', '').split(',')
        for admin_id in admin_ids:
            if admin_id.strip():
                self.admin_users.add(admin_id.strip())
        self.backend = "memory"
    
    def _init_admin_users_firestore(self):
        try:
            admin_ids = os.getenv('ADMIN_USER_IDS', '').split(',')
            for admin_id in admin_ids:
                admin_id = admin_id.strip()
                if admin_id:
                    doc_ref = self.db.collection('admin_users').document(admin_id)
                    doc_ref.set({
                        'user_id': admin_id,
                        'is_admin': True,
                        'created_at': firestore.SERVER_TIMESTAMP
                    }, merge=True)
        except Exception as e:
            pass
    
    def _get_today_key(self) -> str:
        return datetime.now(self.JST).date().isoformat()
    
    def _get_jst_now(self) -> datetime:
        return datetime.now(self.JST)
    
    # === Firestore Methods ===
    async def _firestore_check_limits(self, user_id: str, with_images: bool) -> Tuple[bool, Dict]:
        try:
            doc_id = f"{user_id}_{self._get_today_key()}"
            doc = self.db.collection('rate_limits').document(doc_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                total_requests = data.get('total_requests', 0)
                image_requests = data.get('image_generation_requests', 0)
            else:
                total_requests = 0
                image_requests = 0
            
            total_ok = total_requests < self.DAILY_TOTAL_LIMIT
            image_ok = True
            if with_images:
                image_ok = image_requests < self.DAILY_IMAGE_GENERATION_LIMIT
            
            remaining = {
                'total_remaining': max(0, self.DAILY_TOTAL_LIMIT - total_requests),
                'image_generation_remaining': max(0, self.DAILY_IMAGE_GENERATION_LIMIT - image_requests),
                'total_limit': self.DAILY_TOTAL_LIMIT,
                'image_generation_limit': self.DAILY_IMAGE_GENERATION_LIMIT
            }
            
            return total_ok and image_ok, remaining
        except Exception as e:
            remaining = {
                'total_remaining': self.DAILY_TOTAL_LIMIT,
                'image_generation_remaining': self.DAILY_IMAGE_GENERATION_LIMIT,
                'total_limit': self.DAILY_TOTAL_LIMIT,
                'image_generation_limit': self.DAILY_IMAGE_GENERATION_LIMIT
            }
            return True, remaining
    
    async def _firestore_increment_count(self, user_id: str, with_images: bool):
        try:
            doc_id = f"{user_id}_{self._get_today_key()}"
            doc_ref = self.db.collection('rate_limits').document(doc_id)
            
            @firestore.transactional
            def update_counts(transaction, doc_ref):
                doc = doc_ref.get(transaction=transaction)
                if doc.exists:
                    data = doc.to_dict()
                    total_requests = data.get('total_requests', 0) + 1
                    image_requests = data.get('image_generation_requests', 0)
                    if with_images:
                        image_requests += 1
                else:
                    total_requests = 1
                    image_requests = 1 if with_images else 0
                
                transaction.set(doc_ref, {
                    'user_id': user_id,
                    'date': self._get_today_key(),
                    'total_requests': total_requests,
                    'image_generation_requests': image_requests,
                    'last_request_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }, merge=True)
            
            transaction = self.db.transaction()
            update_counts(transaction, doc_ref)
        except Exception as e:
            pass
    
    async def _firestore_get_user_status(self, user_id: str) -> Dict:
        try:
            doc_id = f"{user_id}_{self._get_today_key()}"
            doc = self.db.collection('rate_limits').document(doc_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                total_used = data.get('total_requests', 0)
                image_used = data.get('image_generation_requests', 0)
            else:
                total_used = 0
                image_used = 0
            
            return {
                'date': self._get_today_key(),
                'total_used': total_used,
                'total_remaining': max(0, self.DAILY_TOTAL_LIMIT - total_used),
                'image_generation_used': image_used,
                'image_generation_remaining': max(0, self.DAILY_IMAGE_GENERATION_LIMIT - image_used),
                'limits': {
                    'total': self.DAILY_TOTAL_LIMIT,
                    'image_generation': self.DAILY_IMAGE_GENERATION_LIMIT
                },
                'jst_time': self._get_jst_now().isoformat(),
                'backend': 'firestore'
            }
        except Exception as e:
            return await self._memory_get_user_status(user_id)
    
    async def _firestore_is_admin(self, user_id: str) -> bool:
        try:
            doc = self.db.collection('admin_users').document(user_id).get()
            return doc.exists and doc.to_dict().get('is_admin', False)
        except Exception as e:
            return False
    
    async def _firestore_reset_user_limits(self, user_id: str) -> bool:
        try:
            doc_id = f"{user_id}_{self._get_today_key()}"
            self.db.collection('rate_limits').document(doc_id).set({
                'user_id': user_id,
                'date': self._get_today_key(),
                'total_requests': 0,
                'image_generation_requests': 0,
                'reset_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            return False
    
    async def _firestore_get_all_stats(self) -> Dict:
        try:
            today = self._get_today_key()
            docs = self.db.collection('rate_limits').where('date', '==', today).stream()
            
            total_users = 0
            total_requests_today = 0
            image_requests_today = 0
            users = []
            
            for doc in docs:
                data = doc.to_dict()
                total_users += 1
                total_requests_today += data.get('total_requests', 0)
                image_requests_today += data.get('image_generation_requests', 0)
                users.append({
                    'user_id': data.get('user_id', 'unknown'),
                    'total_requests': data.get('total_requests', 0),
                    'image_requests': data.get('image_generation_requests', 0),
                    'last_request_at': data.get('last_request_at')
                })
            
            return {
                'date': today,
                'jst_time': self._get_jst_now().isoformat(),
                'total_users': total_users,
                'total_requests_today': total_requests_today,
                'image_requests_today': image_requests_today,
                'users': sorted(users, key=lambda x: x['total_requests'], reverse=True),
                'backend': 'firestore'
            }
        except Exception as e:
            return await self._memory_get_all_stats()
    
    # === Memory Methods ===
    def _reset_if_new_day(self, user_id: str):
        today = self._get_today_key()
        user_data = self.daily_counts[user_id]
        if user_data['date'] != today:
            self.daily_counts[user_id] = {
                'date': today,
                'total_requests': 0,
                'image_generation_requests': 0
            }
    
    async def _memory_check_limits(self, user_id: str, with_images: bool) -> Tuple[bool, Dict]:
        self._reset_if_new_day(user_id)
        user_data = self.daily_counts[user_id]
        
        total_ok = user_data['total_requests'] < self.DAILY_TOTAL_LIMIT
        image_ok = True
        if with_images:
            image_ok = user_data['image_generation_requests'] < self.DAILY_IMAGE_GENERATION_LIMIT
        
        remaining = {
            'total_remaining': max(0, self.DAILY_TOTAL_LIMIT - user_data['total_requests']),
            'image_generation_remaining': max(0, self.DAILY_IMAGE_GENERATION_LIMIT - user_data['image_generation_requests']),
            'total_limit': self.DAILY_TOTAL_LIMIT,
            'image_generation_limit': self.DAILY_IMAGE_GENERATION_LIMIT
        }
        
        return total_ok and image_ok, remaining
    
    async def _memory_increment_count(self, user_id: str, with_images: bool):
        self._reset_if_new_day(user_id)
        user_data = self.daily_counts[user_id]
        user_data['total_requests'] += 1
        if with_images:
            user_data['image_generation_requests'] += 1
    
    async def _memory_get_user_status(self, user_id: str) -> Dict:
        self._reset_if_new_day(user_id)
        user_data = self.daily_counts[user_id]
        
        return {
            'date': self._get_today_key(),
            'total_used': user_data['total_requests'],
            'total_remaining': max(0, self.DAILY_TOTAL_LIMIT - user_data['total_requests']),
            'image_generation_used': user_data['image_generation_requests'],
            'image_generation_remaining': max(0, self.DAILY_IMAGE_GENERATION_LIMIT - user_data['image_generation_requests']),
            'limits': {
                'total': self.DAILY_TOTAL_LIMIT,
                'image_generation': self.DAILY_IMAGE_GENERATION_LIMIT
            },
            'jst_time': self._get_jst_now().isoformat(),
            'backend': 'memory'
        }
    
    async def _memory_is_admin(self, user_id: str) -> bool:
        return user_id in self.admin_users
    
    async def _memory_reset_user_limits(self, user_id: str) -> bool:
        today = self._get_today_key()
        self.daily_counts[user_id] = {
            'date': today,
            'total_requests': 0,
            'image_generation_requests': 0
        }
        return True
    
    async def _memory_get_all_stats(self) -> Dict:
        today = self._get_today_key()
        total_users = 0
        total_requests_today = 0
        image_requests_today = 0
        users = []
        
        for user_id, data in self.daily_counts.items():
            if data['date'] == today:
                total_users += 1
                total_requests_today += data['total_requests']
                image_requests_today += data['image_generation_requests']
                users.append({
                    'user_id': user_id,
                    'total_requests': data['total_requests'],
                    'image_requests': data['image_generation_requests'],
                    'last_request_at': None
                })
        
        return {
            'date': today,
            'jst_time': self._get_jst_now().isoformat(),
            'total_users': total_users,
            'total_requests_today': total_requests_today,
            'image_requests_today': image_requests_today,
            'users': sorted(users, key=lambda x: x['total_requests'], reverse=True),
            'backend': 'memory'
        }
    
    # === Public Interface ===
    async def check_limits(self, user_id: str, with_images: bool = False) -> Tuple[bool, Dict]:
        if self.backend == "firestore":
            return await self._firestore_check_limits(user_id, with_images)
        else:
            return await self._memory_check_limits(user_id, with_images)
    
    async def increment_count(self, user_id: str, with_images: bool = False):
        if self.backend == "firestore":
            await self._firestore_increment_count(user_id, with_images)
        else:
            await self._memory_increment_count(user_id, with_images)
    
    async def get_user_status(self, user_id: str) -> Dict:
        if self.backend == "firestore":
            return await self._firestore_get_user_status(user_id)
        else:
            return await self._memory_get_user_status(user_id)
    
    async def is_admin(self, user_id: str) -> bool:
        if self.backend == "firestore":
            return await self._firestore_is_admin(user_id)
        else:
            return await self._memory_is_admin(user_id)
    
    async def reset_user_limits(self, user_id: str) -> bool:
        if self.backend == "firestore":
            return await self._firestore_reset_user_limits(user_id)
        else:
            return await self._memory_reset_user_limits(user_id)
    
    async def reset_all_limits(self) -> int:
        if self.backend == "firestore":
            try:
                today = self._get_today_key()
                docs = self.db.collection('rate_limits').where('date', '==', today).stream()
                reset_count = 0
                batch = self.db.batch()
                
                for doc in docs:
                    data = doc.to_dict()
                    user_id = data.get('user_id')
                    if user_id:
                        doc_ref = self.db.collection('rate_limits').document(doc.id)
                        batch.set(doc_ref, {
                            'user_id': user_id,
                            'date': today,
                            'total_requests': 0,
                            'image_generation_requests': 0,
                            'reset_at': firestore.SERVER_TIMESTAMP,
                            'updated_at': firestore.SERVER_TIMESTAMP
                        })
                        reset_count += 1
                
                if reset_count > 0:
                    batch.commit()
                return reset_count
            except Exception as e:
                return 0
        else:
            today = self._get_today_key()
            reset_count = 0
            for user_id in list(self.daily_counts.keys()):
                self.daily_counts[user_id] = {
                    'date': today,
                    'total_requests': 0,
                    'image_generation_requests': 0
                }
                reset_count += 1
            return reset_count
    
    async def get_all_stats(self) -> Dict:
        if self.backend == "firestore":
            return await self._firestore_get_all_stats()
        else:
            return await self._memory_get_all_stats()
    
    async def add_admin(self, user_id: str, added_by: str) -> bool:
        if self.backend == "firestore":
            try:
                self.db.collection('admin_users').document(user_id).set({
                    'user_id': user_id,
                    'is_admin': True,
                    'added_by': added_by,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                return True
            except Exception as e:
                return False
        else:
            self.admin_users.add(user_id)
            return True
    
    async def remove_admin(self, user_id: str) -> bool:
        if self.backend == "firestore":
            try:
                self.db.collection('admin_users').document(user_id).delete()
                return True
            except Exception as e:
                return False
        else:
            if user_id in self.admin_users:
                self.admin_users.remove(user_id)
                return True
            return False
    
    def get_next_reset_time(self) -> Dict:
        jst_now = self._get_jst_now()
        tomorrow = jst_now.date() + timedelta(days=1)
        next_reset = datetime.combine(tomorrow, datetime.min.time(), self.JST)
        time_until_reset = next_reset - jst_now
        hours, remainder = divmod(time_until_reset.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return {
            'next_reset_jst': next_reset.isoformat(),
            'current_jst': jst_now.isoformat(),
            'hours_until_reset': int(hours),
            'minutes_until_reset': int(minutes),
            'formatted_time_until': f"{int(hours)}時間{int(minutes):02d}分後",
            'backend': self.backend
        }

# シングルトンインスタンス
rate_limiter = RateLimiter()