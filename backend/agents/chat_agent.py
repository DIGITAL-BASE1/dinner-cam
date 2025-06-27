import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Dict, List, Any, Optional
import json
import re
import os
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
ユーザーのメッセージを分析して、以下のカテゴリのどれに該当するか判定してください。

ユーザーメッセージ: "{message}"

意図カテゴリ:
1. image_request: 冷蔵庫の写真を撮る/送ることに関する言及
2. text_ingredients: 具体的な食材名を複数含んでいる
3. recipe_request: 特定の料理名や調理法を求めている（例：「カレー作りたい」「うまい丼を作って」）
4. nutrition_advice: 栄養、健康、ダイエットに関する相談
5. cooking_advice: 料理のコツ、時短、失敗対策などの質問
6. casual_chat: 挨拶、感情表現、一般的な会話
7. clarification: 不明確で詳細確認が必要

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
        "difficulty_level": "難易度要求"
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
        """料理名を検出"""
        dish_keywords = [
            'カレー', 'ラーメン', 'うどん', 'そば', 'パスタ', 'チャーハン', 'オムライス',
            '丼', 'どんぶり', '親子丼', '牛丼', '豚丼', 'カツ丼', '天丼',
            'ハンバーグ', '唐揚げ', '餃子', '焼肉', 'ステーキ', '肉じゃが',
            'サラダ', 'スープ', '味噌汁', '炒め物', '煮物', '焼き物',
            '鍋', 'すき焼き', 'しゃぶしゃぶ', 'おでん', '寿司', '刺身'
        ]
        
        for dish in dish_keywords:
            if dish in text:
                return dish
        return ""
    
    def _extract_ingredients_simple(self, text: str) -> List[str]:
        """簡易的な食材抽出"""
        common_ingredients = [
            '鶏肉', '豚肉', '牛肉', '魚', '卵', '牛乳', '豆腐', 'チーズ', '納豆',
            '玉ねぎ', 'にんじん', 'じゃがいも', 'キャベツ', 'レタス', 'トマト', 'きゅうり',
            '米', 'パン', 'パスタ', 'うどん', 'そば', '小麦粉', 'もやし', 'ピーマン',
            '醤油', '味噌', '塩', '砂糖', '酢', '油', 'バター', 'マヨネーズ', 'ケチャップ'
        ]
        return [ingredient for ingredient in common_ingredients if ingredient in text]
    
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
            return self._generate_casual_response(context)
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
    
    def _generate_casual_response(self, context: List[Dict] = None) -> str:
        """雑談レスポンス"""
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

# シングルトンインスタンス
chat_agent = ChatAgent()