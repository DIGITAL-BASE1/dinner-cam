import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Dict, List, Any, Optional, AsyncGenerator
import json
import re
import os
import asyncio
from enum import Enum
from agents.profile_extraction_agent import profile_extraction_agent

# 環境変数から設定を取得（全て必須）
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME")

# 必須環境変数のチェック
if not PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable is required")
if not LOCATION:
    raise ValueError("LOCATION environment variable is required")
if not TEXT_MODEL_NAME:
    raise ValueError("TEXT_MODEL_NAME environment variable is required")

vertexai.init(project=PROJECT_ID, location=LOCATION)

class IntentType(Enum):
    IMAGE_REQUEST = "image_request"       # 冷蔵庫の写真を撮ってもらいたい
    TEXT_INGREDIENTS = "text_ingredients" # 手持ち食材を教えてくれた
    RECIPE_REQUEST = "recipe_request"     # 特定のレシピを作りたい
    NUTRITION_ADVICE = "nutrition_advice" # 栄養相談
    COOKING_ADVICE = "cooking_advice"     # 料理の相談・質問
    CASUAL_CHAT = "casual_chat"          # 雑談
    CLARIFICATION = "clarification"       # 詳細確認が必要

class ChatAgent:
    def __init__(self):
        self.model = GenerativeModel(TEXT_MODEL_NAME)
        self.conversation_context = []
    
    def analyze_user_intent(self, message: str, has_image: bool = False) -> Dict[str, Any]:
        """ユーザーの意図を分析する"""
        
        # 画像が添付されている場合
        if has_image:
            return {
                "intent": IntentType.IMAGE_REQUEST,
                "confidence": 1.0,
                "extracted_data": {},
                "response_type": "image_analysis",
                "profile_info": {}
            }
        
        # テキストベースの意図分析
        prompt = f"""
あなたは料理アシスタントの意図理解エキスパートです。
ユーザーのメッセージを慎重に分析して、以下のカテゴリのどれに該当するか判定してください。

ユーザーメッセージ: "{message}"

意図カテゴリ:
1. image_request: 冷蔵庫の写真を撮る/送ることに関する言及
2. text_ingredients: 具体的な食材名を複数含んでいて、かつレシピ生成を明確に求めている
3. recipe_request: 特定の料理名や調理法を明確に求めている（例：「カレー作りたい」「パスタのレシピ教えて」）
4. nutrition_advice: 栄養、健康、ダイエットに関する相談
5. cooking_advice: 料理のコツ、時短、失敗対策などの質問
6. casual_chat: 挨拶、感情表現、一般的な会話、情報提供（人数、時間、好みなど）
7. clarification: 不明確で詳細確認が必要

**重要な判定基準**:
- 単純な情報提供（「人数は○人です」「時間がない」など）は「casual_chat」
- 料理への願望・欲求（「食べたい」「飲みたい」「美味しそう」など）は「recipe_request」
- 料理作成の意図（「作りたい」「教えて」「作って」「レシピください」など）は「recipe_request」
- 食材を使った料理提案の要求（「○○を使って」「○○で何か」など）は「text_ingredients」

**casual_chatの例**:
- 「人数は5人です」「時間がない」「今日は忙しい」「お腹すいた」
- 「冷蔵庫にトマトがある」（使いたいという意図なし）
- 一般的な挨拶や感情表現

**recipe_requestの例**:
- 「カレーを作りたい」「パスタのレシピを教えて」「チャーハンを作って」
- 「韓国チゲが食べたいな」「ラーメンが飲みたい」「美味しいパスタが食べたい」
- 「今日はカレー気分」「パスタの気分」「韓国料理が食べたいな」
- 「チゲが美味しそうだな」「イタリア料理が食べたいなあ」

**text_ingredientsの例**:
- 「鶏肉でなにか作りたい」「トマトを使って何か作って」
- 「これらの食材でレシピをお願いします」

以下のJSON形式で回答してください：
{{
    "intent": "カテゴリ名",
    "confidence": 0.0-1.0の信頼度,
    "extracted_data": {{
        "ingredients": ["抽出された食材名"],
        "dish_name": "料理名（もしあれば）",
        "cooking_method": "調理法（炒める、煮る等）",
        "dietary_needs": "食事制限や目標",
        "time_constraint": "時間制約",
        "difficulty_level": "難易度要求",
        "context_info": "人数、時間、好みなどの文脈情報"
    }},
    "reasoning": "判定理由の簡潔な説明"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            # JSONを抽出
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                intent_result = self._validate_intent_result(result)
                
                # プロファイル情報も並行抽出
                profile_info = profile_extraction_agent.extract_profile_info(message)
                intent_result["profile_info"] = profile_info
                
                return intent_result
            else:
                return self._get_default_intent(message)
        except Exception as e:
            return self._get_default_intent(message)
    
    def _validate_intent_result(self, result: Dict) -> Dict[str, Any]:
        """意図分析結果の検証と修正"""
        try:
            # intentの検証
            intent_str = result.get("intent", "clarification")
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.CLARIFICATION
            
            return {
                "intent": intent,
                "confidence": max(0.0, min(1.0, float(result.get("confidence", 0.5)))),
                "extracted_data": result.get("extracted_data", {}),
                "reasoning": result.get("reasoning", ""),
                "response_type": self._determine_response_type(intent)
            }
        except Exception as e:
            return self._get_default_intent("")
    
    def _get_default_intent(self, message: str) -> Dict[str, Any]:
        """デフォルトの意図分析結果"""
        # 簡易的なキーワード検出
        if any(word in message.lower() for word in ['冷蔵庫', '写真', '画像', '撮る']):
            intent = IntentType.IMAGE_REQUEST
        elif self._extract_ingredients_simple(message):
            intent = IntentType.TEXT_INGREDIENTS
        elif self._detect_dish_name(message):
            intent = IntentType.RECIPE_REQUEST
        else:
            intent = IntentType.CASUAL_CHAT
            
        return {
            "intent": intent,
            "confidence": 0.7,
            "extracted_data": {
                "ingredients": self._extract_ingredients_simple(message),
                "dish_name": self._detect_dish_name(message)
            },
            "reasoning": "簡易キーワード検出",
            "response_type": self._determine_response_type(intent),
            "profile_info": profile_extraction_agent.extract_profile_info(message)
        }
    
    def _detect_dish_name(self, text: str) -> str:
        """料理名を検出（レシピ要求の意図がある場合のみ）"""
        dish_keywords = [
            # 日本料理
            'カレー', 'ラーメン', 'うどん', 'そば', 'チャーハン', 'オムライス',
            '丼', 'どんぶり', '親子丼', '牛丼', '豚丼', 'カツ丼', '天丼',
            'ハンバーグ', '唐揚げ', '餃子', '焼肉', 'ステーキ', '肉じゃが',
            'サラダ', 'スープ', '味噌汁', '炒め物', '煮物', '焼き物',
            '鍋', 'すき焼き', 'しゃぶしゃぶ', 'おでん', '寿司', '刺身',
            # 国際料理・ジャンル
            'パスタ', 'ピザ', 'リゾット', 'パエリア', 'タコス', 'ブリトー',
            'チゲ', 'キムチ', 'ビビンバ', 'サムギョプサル', 'チャプチェ',
            'トムヤムクン', 'パッタイ', 'グリーンカレー', 'ガパオ',
            '麻婆豆腐', '回鍋肉', '青椒肉絲', '酢豚', '春巻き',
            # 料理ジャンル
            '韓国料理', '中華料理', 'イタリア料理', 'タイ料理', 'インド料理',
            'フランス料理', 'メキシコ料理', '和食', '洋食', '中華'
        ]
        
        # レシピ要求を示すキーワード（願望表現も含む）
        request_keywords = [
            '作りたい', '作って', '教えて', 'レシピ', '作ろう', '作る',
            'お願い', 'ください', '欲しい', '手伝って', '提案', '候補',
            '食べたい', '飲みたい', '気分', '美味しい', '美味しそう'
        ]
        
        # 自然な願望表現も検出（正規表現）
        import re
        desire_patterns = [
            r'.*な$',    # 「韓国チゲが食べたいな」
            r'.*なあ$',  # 「パスタが食べたいなあ」  
            r'.*だな$',  # 「カレーが食べたいだな」
            r'.*だね$',  # 「美味しそうだね」
            r'.*気分$',  # 「パスタ気分」
            r'.*したい', # 「○○したい」
        ]
        
        has_request_intent = (
            any(keyword in text for keyword in request_keywords) or
            any(re.search(pattern, text) for pattern in desire_patterns)
        )
        
        if has_request_intent:
            for dish in dish_keywords:
                if dish in text:
                    return dish
        return ""
    
    def _extract_ingredients_simple(self, text: str) -> List[str]:
        """簡易的な食材抽出（レシピ要求の意図がある場合のみ）"""
        common_ingredients = [
            '鶏肉', '豚肉', '牛肉', '魚', '卵', '牛乳', '豆腐', 'チーズ', '納豆',
            '玉ねぎ', 'にんじん', 'じゃがいも', 'キャベツ', 'レタス', 'トマト', 'きゅうり',
            '米', 'パン', 'パスタ', 'うどん', 'そば', '小麦粉', 'もやし', 'ピーマン',
            '醤油', '味噌', '塩', '砂糖', '酢', '油', 'バター', 'マヨネーズ', 'ケチャップ'
        ]
        
        # レシピ要求を示すキーワードがある場合のみ食材を抽出（願望表現も含む）
        request_keywords = [
            '作りたい', '作って', '教えて', 'レシピ', '作ろう', '作る',
            'お願い', 'ください', '欲しい', '手伝って', '提案', '候補',
            '使って', '余って', 'ある', 'ため',
            '食べたい', '飲みたい', '気分', '美味しい', '美味しそう'
        ]
        
        # 自然な願望表現も検出（正規表現）
        import re
        desire_patterns = [
            r'.*な$',    # 「韓国チゲが食べたいな」
            r'.*なあ$',  # 「パスタが食べたいなあ」  
            r'.*だな$',  # 「カレーが食べたいだな」
            r'.*だね$',  # 「美味しそうだね」
            r'.*気分$',  # 「パスタ気分」
            r'.*したい', # 「○○したい」
        ]
        
        has_request_intent = (
            any(keyword in text for keyword in request_keywords) or
            any(re.search(pattern, text) for pattern in desire_patterns)
        )
        
        if has_request_intent:
            return [ingredient for ingredient in common_ingredients if ingredient in text]
        return []
    
    def _determine_response_type(self, intent: IntentType) -> str:
        """レスポンスタイプを決定"""
        mapping = {
            IntentType.IMAGE_REQUEST: "request_image",
            IntentType.TEXT_INGREDIENTS: "generate_recipe",
            IntentType.RECIPE_REQUEST: "generate_recipe",
            IntentType.NUTRITION_ADVICE: "nutrition_consultation",
            IntentType.COOKING_ADVICE: "cooking_consultation",
            IntentType.CASUAL_CHAT: "casual_response",
            IntentType.CLARIFICATION: "ask_clarification"
        }
        return mapping.get(intent, "casual_response")
    
    def generate_response(self, intent_result: Dict[str, Any], context: List[Dict] = None) -> str:
        """意図に基づいてレスポンスを生成"""
        intent = intent_result["intent"]
        extracted_data = intent_result["extracted_data"]
        
        if intent == IntentType.IMAGE_REQUEST:
            return self._generate_image_request_response()
        elif intent == IntentType.TEXT_INGREDIENTS:
            return self._generate_ingredient_response(extracted_data.get("ingredients", []))
        elif intent == IntentType.RECIPE_REQUEST:
            return self._generate_recipe_request_response(extracted_data)
        elif intent == IntentType.NUTRITION_ADVICE:
            return self._generate_nutrition_response(extracted_data)
        elif intent == IntentType.COOKING_ADVICE:
            return self._generate_cooking_advice_response(extracted_data)
        elif intent == IntentType.CASUAL_CHAT:
            return self._generate_casual_response(extracted_data)
        else:  # CLARIFICATION
            return self._generate_clarification_response()
    
    def _generate_image_request_response(self) -> str:
        """画像リクエストのレスポンス"""
        responses = [
            "冷蔵庫の写真を撮って送ってください！📸 食材を自動で認識してレシピを提案します。",
            "冷蔵庫の中身を確認させていただきますね！📷 写真をアップロードしてください。",
            "冷蔵庫の写真をお待ちしています！🔍 何が入っているか見てみましょう。"
        ]
        import random
        return random.choice(responses)
    
    def _generate_ingredient_response(self, ingredients: List[str]) -> str:
        """食材ベースのレスポンス"""
        if not ingredients:
            return "食材を教えていただけますか？具体的にどのような材料がお手元にありますか？\n\nまたは、作りたい料理名（例：カレー、チャーハン、パスタなど）を教えていただければ、その料理のレシピを提案します！"
        
        return f"素晴らしい食材ですね！🍳\n\n以下の食材でレシピを作成します：\n{chr(10).join([f'• {ing}' for ing in ingredients])}\n\n少々お待ちください..."
    
    def _generate_recipe_request_response(self, extracted_data: Dict) -> str:
        """レシピリクエストのレスポンス"""
        dish_name = extracted_data.get("dish_name", "")
        cooking_method = extracted_data.get("cooking_method", "")
        time_constraint = extracted_data.get("time_constraint", "")
        
        if dish_name:
            response = f"「{dish_name}」のレシピを作成しますね！🍳"
        else:
            response = "レシピを作成しますね！🍳"
            
        if cooking_method:
            response += f"\n{cooking_method}で調理する方向で考えます。"
        if time_constraint:
            response += f"\n{time_constraint}を考慮します。"
        
        return response + "\n\n少々お待ちください..."
    
    def _generate_nutrition_response(self, extracted_data: Dict) -> str:
        """栄養相談のレスポンス"""
        dietary_needs = extracted_data.get("dietary_needs", "")
        
        base_response = "栄養についてのご相談ですね！💪 "
        
        if dietary_needs:
            return f"{base_response}{dietary_needs}について考慮したアドバイスをしますね。まず、現在お手元にある食材を教えてください。"
        else:
            return f"{base_response}具体的にどのような栄養面でのお悩みがありますか？また、お手元の食材も教えてください。"
    
    def _generate_cooking_advice_response(self, extracted_data: Dict) -> str:
        """料理相談のレスポンス"""
        return "料理のご相談ですね！👨‍🍳 具体的にどのようなことでお悩みでしょうか？食材やお困りの点を詳しく教えてください。"
    
    def _generate_casual_response(self, extracted_data: Dict = None) -> str:
        """雑談・情報提供レスポンス"""
        if extracted_data and extracted_data.get("context_info"):
            context_info = extracted_data.get("context_info")
            # 文脈情報を受け取った場合の応答
            return f"承知いたしました！{context_info}ですね。😊\n\n他に何か詳しい情報があれば教えてください。例えば：\n• 作りたい料理の種類\n• お手元にある食材\n• お好みや苦手なもの\n\nより具体的な提案ができるよう、お手伝いします！🍳"
        
        # 一般的な雑談の場合
        casual_responses = [
            "こんにちは！😊 今日のお食事について何かお手伝いできることはありますか？",
            "お疲れさまです！🍳 美味しい料理を一緒に作りましょう！",
            "いらっしゃいませ！👨‍🍳 今日は何を作りたい気分ですか？",
            "こんにちは！何か美味しいものを作りたくなりましたか？😋"
        ]
        import random
        return random.choice(casual_responses)
    
    def _generate_clarification_response(self) -> str:
        """詳細確認のレスポンス"""
        return "申し訳ございませんが、もう少し詳しく教えていただけますか？🤔\n\n例えば：\n• 冷蔵庫の写真を送る\n• 手持ちの食材を教える\n• 作りたい料理の種類を伝える\n\nなどしていただけると、より良い提案ができます！"
    
    def add_to_context(self, user_message: str, bot_response: str):
        """会話履歴をコンテキストに追加"""
        self.conversation_context.append({
            "user": user_message,
            "bot": bot_response,
            "timestamp": "now"  # 実際の実装では適切なタイムスタンプを
        })
        
        # 履歴が長くなりすぎたら古いものを削除
        if len(self.conversation_context) > 10:
            self.conversation_context = self.conversation_context[-10:]
    
    # ===== 非同期メソッド（新機能） =====
    
    async def analyze_user_intent_async(self, message: str, has_image: bool = False) -> Dict[str, Any]:
        """非同期版意図分析（後方互換性のため、同期版を流用）"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.analyze_user_intent, message, has_image
        )
    
    async def generate_response_async(self, intent_result: Dict[str, Any]) -> str:
        """非同期版レスポンス生成（後方互換性のため、同期版を流用）"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.generate_response, intent_result
        )
    
    async def process_message_stream(
        self, 
        message: str, 
        has_image: bool = False, 
        user_id: str = None
    ) -> AsyncGenerator[str, None]:
        """統合ストリーミング処理 - ChatAgent中心型アーキテクチャの中核"""
        try:
            # Step 1: 意図理解
            yield self._create_sse_data("status", "analyzing_intent")
            intent_result = await self.analyze_user_intent_async(message, has_image)
            yield self._create_sse_data("intent", {
                "intent": intent_result["intent"].value,
                "confidence": intent_result["confidence"],
                "extracted_data": intent_result["extracted_data"]
            })
            
            # Step 2: プロファイル情報を自動更新（ユーザーIDが提供されている場合）
            if user_id:
                profile_info = intent_result.get("profile_info", {})
                if profile_info and profile_info.get("confidence", 0) > 0.3:
                    # バックグラウンドで実行（レスポンスをブロックしない）
                    asyncio.create_task(self._update_profile_from_conversation(user_id, profile_info))
            
            # Step 3: 応答生成
            response = await self.generate_response_async(intent_result)
            yield self._create_sse_data("chat_response", response)
            
            # Step 4: 必要に応じてレシピ生成を自動実行
            if intent_result["intent"] in [IntentType.TEXT_INGREDIENTS, IntentType.RECIPE_REQUEST]:
                yield self._create_sse_data("status", "starting_recipe_generation")
                
                # レシピ生成を自動実行
                async for recipe_data in self._generate_recipe_automatically(intent_result, user_id):
                    yield recipe_data
            
            # 会話コンテキストに追加
            self.add_to_context(message, response)
            
            yield self._create_sse_data("complete", {"status": "success"})
            
        except Exception as e:
            yield self._create_sse_data("error", {
                "message": "申し訳ございません。エラーが発生しました。🙏",
                "details": str(e)
            })
    
    async def process_recipe_generation_stream(
        self,
        message: str,
        has_image: bool = False,
        user_id: str = None,
        with_images: bool = False,
        with_nutrition: bool = True
    ) -> AsyncGenerator[str, None]:
        """完全な統合レシピ生成ストリーミング処理"""
        try:
            # 他のエージェントをインポート（遅延インポートでサイクル参照回避）
            from agents.recipe_agent import recipe_agent
            from agents.nutrition_agent import nutrition_agent
            from agents.generate_image_agent import image_agent
            from agents.vision_agent import extract_ingredients_from_image
            
            # Step 1: 意図理解とプロファイル抽出
            yield self._create_sse_data("status", "analyzing_intent")
            intent_result = await self.analyze_user_intent_async(message, has_image)
            yield self._create_sse_data("intent", {
                "intent": intent_result["intent"].value,
                "confidence": intent_result["confidence"],
                "extracted_data": intent_result["extracted_data"]
            })
            
            # Step 2: ユーザープロファイルを取得（user_idが提供されている場合）
            user_preferences = {}
            if user_id:
                try:
                    from services.profile_storage import profile_storage
                    user_preferences = await profile_storage.get_user_preferences_summary(user_id)
                except Exception:
                    pass  # プロファイル取得エラーは無視
            
            # Step 3: 食材抽出（画像分析または意図から）
            ingredients = []
            dish_name = ""
            extracted_data = intent_result.get("extracted_data", {})
            
            if has_image:
                yield self._create_sse_data("status", "analyzing_image")
                # 画像分析処理は同期的なので、非同期化
                # ここは実際の画像パスが必要ですが、ひとまずプレースホルダー
                yield self._create_sse_data("status", "image_analysis_complete")
            else:
                ingredients = extracted_data.get("ingredients", [])
                dish_name = extracted_data.get("dish_name", "")
            
            # Step 4: レシピ生成
            yield self._create_sse_data("status", "generating_recipe")
            
            if dish_name:
                recipe = await asyncio.get_event_loop().run_in_executor(
                    None, recipe_agent.generate_recipe_from_dish_name,
                    dish_name, {}, user_preferences
                )
            else:
                recipe = await asyncio.get_event_loop().run_in_executor(
                    None, recipe_agent.generate_recipe_from_ingredients,
                    ingredients, user_preferences
                )
            
            yield self._create_sse_data("recipe", recipe)
            
            # Step 5: 栄養分析（並列処理可能）
            nutrition_task = None
            if with_nutrition:
                yield self._create_sse_data("status", "analyzing_nutrition")
                analysis_target = ingredients if ingredients else [dish_name] if dish_name else ["一般的な料理"]
                nutrition_task = asyncio.get_event_loop().run_in_executor(
                    None, nutrition_agent.analyze_recipe_nutrition,
                    recipe, analysis_target
                )
            
            # Step 6: 手順画像生成（並列処理可能）
            image_tasks = []
            if with_images:
                yield self._create_sse_data("status", "preparing_image_generation")
                steps_text = await asyncio.get_event_loop().run_in_executor(
                    None, recipe_agent.extract_steps_from_text, recipe
                )
                
                for i, step in enumerate(steps_text):
                    yield self._create_sse_data("generating_image", {
                        "step_index": i,
                        "step_text": step
                    })
                    image_tasks.append(image_agent.generate_single_image_async(step))
            
            # Step 7: 並列処理の結果を取得
            if nutrition_task:
                nutrition_data = await nutrition_task
                yield self._create_sse_data("nutrition", nutrition_data)
            
            if image_tasks:
                images = await asyncio.gather(*image_tasks, return_exceptions=True)
                for i, (step, image_result) in enumerate(zip(steps_text, images)):
                    if isinstance(image_result, Exception):
                        yield self._create_sse_data("image_error", {
                            "step_index": i,
                            "step_text": step,
                            "error": str(image_result)
                        })
                    else:
                        yield self._create_sse_data("image", {
                            "step_index": i,
                            "step_text": step,
                            "image_url": image_result
                        })
            
            # Step 8: 会話履歴に追加
            response = self.generate_response(intent_result)
            self.add_to_context(message, response)
            
            yield self._create_sse_data("complete", {"status": "success"})
            
        except Exception as e:
            yield self._create_sse_data("error", {
                "message": "申し訳ございません。レシピ生成中にエラーが発生しました。🙏",
                "details": str(e)
            })
    
    async def _generate_recipe_automatically(self, intent_result: Dict[str, Any], user_id: str) -> AsyncGenerator[str, None]:
        """レシピ生成を自動実行（簡易版）"""
        try:
            # 他のエージェントをインポート（遅延インポートでサイクル参照回避）
            from agents.recipe_agent import recipe_agent
            from agents.nutrition_agent import nutrition_agent
            
            extracted_data = intent_result.get("extracted_data", {})
            ingredients = extracted_data.get("ingredients", [])
            dish_name = extracted_data.get("dish_name", "")
            
            # ユーザープロファイルを取得
            user_preferences = {}
            if user_id:
                try:
                    from services.profile_storage import profile_storage
                    user_preferences = await profile_storage.get_user_preferences_summary(user_id)
                except Exception:
                    pass  # プロファイル取得エラーは無視
            
            # Step 1: レシピ生成
            yield self._create_sse_data("status", "generating_recipe")
            
            if dish_name:
                recipe = await asyncio.get_event_loop().run_in_executor(
                    None, recipe_agent.generate_recipe_from_dish_name,
                    dish_name, {}, user_preferences
                )
            else:
                recipe = await asyncio.get_event_loop().run_in_executor(
                    None, recipe_agent.generate_recipe_from_ingredients,
                    ingredients, user_preferences
                )
            
            yield self._create_sse_data("recipe", recipe)
            
            # Step 2: 栄養分析
            yield self._create_sse_data("status", "analyzing_nutrition")
            analysis_target = ingredients if ingredients else [dish_name] if dish_name else ["一般的な料理"]
            nutrition_data = await asyncio.get_event_loop().run_in_executor(
                None, nutrition_agent.analyze_recipe_nutrition,
                recipe, analysis_target
            )
            
            yield self._create_sse_data("nutrition", nutrition_data)
            yield self._create_sse_data("status", "recipe_generation_complete")
            
        except Exception as e:
            yield self._create_sse_data("error", {
                "message": f"レシピ生成中にエラーが発生しました: {str(e)}",
                "details": str(e)
            })
    
    async def _update_profile_from_conversation(self, user_id: str, profile_info: Dict[str, Any]):
        """会話から抽出したプロファイル情報でユーザープロファイルを更新"""
        try:
            # main.pyのupdate_profile_from_conversation関数を呼び出し
            from app.main import update_profile_from_conversation
            await update_profile_from_conversation(user_id, profile_info)
        except Exception as e:
            print(f"[ERROR] ChatAgent プロファイル自動更新エラー: {e}")
    
    def _create_sse_data(self, event_type: str, data: Any) -> str:
        """Server-Sent Events形式のデータを作成"""
        import json
        return f"data: {json.dumps({'type': event_type, 'content': data}, ensure_ascii=False, separators=(',', ':'))}\n\n"

# シングルトンインスタンス
chat_agent = ChatAgent()