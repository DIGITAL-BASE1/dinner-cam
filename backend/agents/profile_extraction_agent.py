import vertexai
from vertexai.generative_models import GenerativeModel
import json
import re
import os
from typing import Dict, List, Any, Optional

# 環境変数から設定を取得
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION") 
TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME")

# 必須環境変数のチェック
if PROJECT_ID and LOCATION and TEXT_MODEL_NAME:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

class ProfileExtractionAgent:
    """会話からユーザープロファイル情報を抽出するエージェント"""
    
    def __init__(self):
        if PROJECT_ID and LOCATION and TEXT_MODEL_NAME:
            self.model = GenerativeModel(TEXT_MODEL_NAME)
        else:
            self.model = None
    
    def extract_profile_info(self, message: str) -> Dict[str, Any]:
        """会話からユーザープロファイル情報を抽出する（全メッセージ対象）"""
        
        if not self.model:
            return {}
        
        # 短すぎるメッセージはスキップ
        if len(message.strip()) < 3:
            return {}
        
        # システムメッセージや一般的な応答はスキップ
        skip_patterns = [
            'こんにちは', 'ありがと', 'はい', 'いいえ', 'ok', 'オッケー'
        ]
        
        if message.strip().lower() in skip_patterns:
            return {}
            
        prompt = f"""
あなたは料理アシスタントの高度なプロファイル分析エキスパートです。
ユーザーのメッセージから料理・食事に関する個人情報を可能な限り抽出してください。

ユーザーメッセージ: "{message}"

以下の項目を詳細に分析し、関連する情報があれば全て抽出してください：

## 必須項目

1. **食事制限** (dietary_restrictions):
   - vegan (ビーガン), vegetarian (ベジタリアン), halal (ハラール), kosher (コーシャー)
   - low_carb (低糖質), keto (ケトジェニック), paleo (パレオ), mediterranean (地中海式)
   - lactose_free (乳糖不耐症), sugar_free (無糖), low_sodium (減塩)

2. **アレルギー** (allergies):
   - nuts (ナッツ), shellfish (甲殻類), dairy (乳製品), eggs (卵), soy (大豆)
   - gluten (グルテン), fish (魚), sesame (ごま), peanuts (ピーナッツ)

3. **調理スキルレベル** (cooking_skill_level):
   - beginner: 初心者、簡単、手軽、慣れていない、苦手
   - intermediate: 普通、まあまあ、ある程度、そこそこ
   - advanced: 上級、本格的、プロ並み、得意、料理好き

4. **時間制約** (available_cooking_time):
   - 調理にかけられる時間（分数）: 5, 10, 15, 30, 60, 90, 120など

5. **好きな料理ジャンル** (preferred_cuisines):
   - japanese (和食), italian (イタリア料理), chinese (中華料理), french (フランス料理)
   - korean (韓国料理), thai (タイ料理), indian (インド料理), mexican (メキシコ料理)
   - american (アメリカ料理), mediterranean (地中海料理), vietnamese (ベトナム料理)

6. **家族構成** (family_size):
   - 何人分の料理を作るか（1〜20人）

7. **健康目標** (health_goals):
   - diet (ダイエット), muscle_gain (筋肉増強), low_sodium (減塩), high_protein (高タンパク)
   - heart_health (心臓の健康), diabetes_management (糖尿病管理), weight_maintenance (体重維持)

8. **苦手な食材** (disliked_ingredients):
   - 具体的な食材名、嫌いなもの、苦手なもの

## 拡張項目

9. **好きな食材** (favorite_ingredients):
   - よく使う食材、好きな食材、お気に入りの食材

10. **調理方法の好み** (preferred_cooking_methods):
    - 炒める、煮る、焼く、揚げる、蒸す、生（サラダ）、電子レンジ、オーブンなど

11. **食事のタイミング** (meal_timing):
    - 朝食、昼食、夕食、おやつ、夜食

12. **特別な状況** (special_situations):
    - お弁当、パーティー、記念日、疲れた時、忙しい時

13. **味の好み** (taste_preferences):
    - 辛い、甘い、酸っぱい、しょっぱい、苦い、薄味、濃い味

14. **食べ物への関心** (food_interests):
    - 健康志向、グルメ、節約、時短、見た目重視、栄養バランス

**重要な判定基準**:
- 直接的な言及だけでなく、間接的な示唆も捉える
- 「○○が食べたい」→ preferred_cuisines や favorite_ingredients
- 「時間がない」「忙しい」→ available_cooking_time (短時間)
- 「ダイエット中」→ health_goals
- 「子供がいる」→ family_size の推測
- 料理名の言及 → preferred_cuisines の推測

以下のJSON形式で回答してください。該当しない項目はnullにしてください：
{{
    "dietary_restrictions": ["抽出された制限"],
    "allergies": ["抽出されたアレルギー"],
    "cooking_skill_level": "レベル",
    "available_cooking_time": 分数,
    "preferred_cuisines": ["料理ジャンル"],
    "family_size": 人数,
    "health_goals": ["健康目標"],
    "disliked_ingredients": ["苦手食材"],
    "favorite_ingredients": ["好きな食材"],
    "preferred_cooking_methods": ["調理方法"],
    "meal_timing": "食事タイミング",
    "special_situations": ["特別な状況"],
    "taste_preferences": ["味の好み"],
    "food_interests": ["食べ物への関心"],
    "confidence": 0.0-1.0の信頼度,
    "reasoning": "抽出理由の詳細説明"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            # JSONを抽出
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return self._validate_extracted_data(result)
            else:
                return {}
        except Exception as e:
            print(f"プロファイル抽出エラー: {e}")
            return {}
    
    def _validate_extracted_data(self, data: Dict) -> Dict[str, Any]:
        """抽出されたデータを検証・修正"""
        validated = {}
        
        # 食事制限の検証（拡張）
        valid_restrictions = [
            "vegan", "vegetarian", "halal", "kosher", "low_carb", "keto", 
            "paleo", "mediterranean", "lactose_free", "sugar_free", "low_sodium"
        ]
        if data.get("dietary_restrictions"):
            validated["dietary_restrictions"] = [
                r for r in data["dietary_restrictions"] 
                if r in valid_restrictions
            ]
        
        # アレルギーの検証（拡張）
        valid_allergies = [
            "nuts", "shellfish", "dairy", "eggs", "soy", "gluten", 
            "fish", "sesame", "peanuts"
        ]
        if data.get("allergies"):
            validated["allergies"] = [
                a for a in data["allergies"] 
                if a in valid_allergies
            ]
        
        # 調理スキルレベル
        if data.get("cooking_skill_level") in ["beginner", "intermediate", "advanced"]:
            validated["cooking_skill_level"] = data["cooking_skill_level"]
        
        # 調理時間（0-180分）
        cooking_time = data.get("available_cooking_time")
        if isinstance(cooking_time, (int, float)) and 0 < cooking_time <= 180:
            validated["available_cooking_time"] = int(cooking_time)
        
        # 料理ジャンル（拡張）
        valid_cuisines = [
            "japanese", "italian", "chinese", "french", "korean", "thai", 
            "indian", "mexican", "american", "mediterranean", "vietnamese"
        ]
        if data.get("preferred_cuisines"):
            validated["preferred_cuisines"] = [
                c for c in data["preferred_cuisines"] 
                if c in valid_cuisines
            ]
        
        # 家族構成（1-20人に拡張）
        family_size = data.get("family_size")
        if isinstance(family_size, (int, float)) and 1 <= family_size <= 20:
            validated["family_size"] = int(family_size)
        
        # 健康目標（拡張）
        valid_goals = [
            "diet", "muscle_gain", "low_sodium", "high_protein",
            "heart_health", "diabetes_management", "weight_maintenance"
        ]
        if data.get("health_goals"):
            validated["health_goals"] = [
                g for g in data["health_goals"] 
                if g in valid_goals
            ]
        
        # 苦手食材（そのまま保存）
        if data.get("disliked_ingredients"):
            validated["disliked_ingredients"] = data["disliked_ingredients"]
        
        # === 新しい拡張項目 ===
        
        # 好きな食材（そのまま保存）
        if data.get("favorite_ingredients"):
            validated["favorite_ingredients"] = data["favorite_ingredients"]
        
        # 調理方法の好み
        valid_cooking_methods = [
            "炒める", "煮る", "焼く", "揚げる", "蒸す", "生", "電子レンジ", "オーブン",
            "fry", "boil", "grill", "deep_fry", "steam", "raw", "microwave", "oven"
        ]
        if data.get("preferred_cooking_methods"):
            validated["preferred_cooking_methods"] = [
                m for m in data["preferred_cooking_methods"] 
                if m in valid_cooking_methods
            ]
        
        # 食事のタイミング
        valid_meal_timings = ["朝食", "昼食", "夕食", "おやつ", "夜食", "breakfast", "lunch", "dinner", "snack"]
        if data.get("meal_timing") in valid_meal_timings:
            validated["meal_timing"] = data["meal_timing"]
        
        # 特別な状況（そのまま保存）
        if data.get("special_situations"):
            validated["special_situations"] = data["special_situations"]
        
        # 味の好み（そのまま保存）
        if data.get("taste_preferences"):
            validated["taste_preferences"] = data["taste_preferences"]
        
        # 食べ物への関心（そのまま保存）
        if data.get("food_interests"):
            validated["food_interests"] = data["food_interests"]
        
        # 信頼度とその他のメタデータ
        validated["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        validated["reasoning"] = data.get("reasoning", "")
        
        return validated

# シングルトンインスタンス
profile_extraction_agent = ProfileExtractionAgent()