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
        """会話からユーザープロファイル情報を抽出する"""
        
        if not self.model:
            return {}
        
        # 短いメッセージや明らかに関係ないメッセージはスキップ
        if len(message.strip()) < 10:
            return {}
        
        # キーワードベースの事前フィルタリング
        profile_keywords = [
            'ビーガン', 'ベジタリアン', 'アレルギー', '初心者', '上級', 
            '分で', '時間', '和食', '中華', '苦手', '好き', '人分'
        ]
        
        if not any(keyword in message for keyword in profile_keywords):
            return {}
            
        prompt = f"""
あなたは料理アシスタントのプロファイル分析エキスパートです。
ユーザーのメッセージから料理に関する個人情報を抽出してください。

ユーザーメッセージ: "{message}"

以下の項目から該当するものを抽出してください：

1. 食事制限 (dietary_restrictions):
   - "vegan", "vegetarian", "halal", "kosher", "low_carb", "keto"

2. アレルギー (allergies):
   - "nuts", "shellfish", "dairy", "eggs", "soy", "gluten", "fish"

3. 調理スキルレベル (cooking_skill_level):
   - "beginner" (初心者、簡単、手軽)
   - "intermediate" (普通、まあまあ)
   - "advanced" (上級、本格的、プロ並み)

4. 時間制約 (available_cooking_time):
   - 分数での時間指定 (例: 30, 60)

5. 好きな料理ジャンル (preferred_cuisines):
   - "japanese", "italian", "chinese", "french", "korean", "thai", "indian"

6. 家族構成 (family_size):
   - 人数 (例: 1, 2, 4)

7. 健康目標 (health_goals):
   - "diet", "muscle_gain", "low_sodium", "high_protein"

8. 苦手な食材 (disliked_ingredients):
   - 具体的な食材名

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
    "confidence": 0.0-1.0の信頼度,
    "reasoning": "抽出理由の説明"
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
        
        # 食事制限の検証
        valid_restrictions = ["vegan", "vegetarian", "halal", "kosher", "low_carb", "keto"]
        if data.get("dietary_restrictions"):
            validated["dietary_restrictions"] = [
                r for r in data["dietary_restrictions"] 
                if r in valid_restrictions
            ]
        
        # アレルギーの検証
        valid_allergies = ["nuts", "shellfish", "dairy", "eggs", "soy", "gluten", "fish"]
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
        
        # 料理ジャンル
        valid_cuisines = ["japanese", "italian", "chinese", "french", "korean", "thai", "indian"]
        if data.get("preferred_cuisines"):
            validated["preferred_cuisines"] = [
                c for c in data["preferred_cuisines"] 
                if c in valid_cuisines
            ]
        
        # 家族構成（1-10人）
        family_size = data.get("family_size")
        if isinstance(family_size, (int, float)) and 1 <= family_size <= 10:
            validated["family_size"] = int(family_size)
        
        # 健康目標
        valid_goals = ["diet", "muscle_gain", "low_sodium", "high_protein"]
        if data.get("health_goals"):
            validated["health_goals"] = [
                g for g in data["health_goals"] 
                if g in valid_goals
            ]
        
        # 苦手食材（そのまま保存）
        if data.get("disliked_ingredients"):
            validated["disliked_ingredients"] = data["disliked_ingredients"]
        
        # 信頼度とその他のメタデータ
        validated["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        validated["reasoning"] = data.get("reasoning", "")
        
        return validated

# シングルトンインスタンス
profile_extraction_agent = ProfileExtractionAgent()