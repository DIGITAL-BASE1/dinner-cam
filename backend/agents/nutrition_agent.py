import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Dict, List, Any
import json
import re
import os

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

class NutritionAgent:
    def __init__(self):
        self.model = GenerativeModel(TEXT_MODEL_NAME)
    
    def analyze_recipe_nutrition(self, recipe_text: str, ingredients: List[str]) -> Dict[str, Any]:
        """レシピの栄養価を分析する"""
        prompt = f"""
あなたは栄養学の専門家です。以下のレシピの栄養価を分析してください。

使用食材: {', '.join(ingredients)}

レシピ:
{recipe_text}

以下のJSON形式で回答してください：
{{
    "calories_per_serving": 推定カロリー数（数値のみ）,
    "servings": 推定人数分（数値のみ）,
    "macronutrients": {{
        "protein_g": タンパク質グラム数（数値のみ）,
        "carbs_g": 炭水化物グラム数（数値のみ）,
        "fat_g": 脂質グラム数（数値のみ）,
        "fiber_g": 食物繊維グラム数（数値のみ）
    }},
    "vitamins_minerals": [
        "主要なビタミン・ミネラル名1",
        "主要なビタミン・ミネラル名2",
        "主要なビタミン・ミネラル名3"
    ],
    "health_benefits": [
        "健康効果1",
        "健康効果2",
        "健康効果3"
    ],
    "dietary_tags": [
        "該当する食事タグ（例：高タンパク、低糖質、ベジタリアン対応など）"
    ],
    "nutrition_score": {{
        "overall": 総合栄養スコア（1-10の数値）,
        "balance": 栄養バランススコア（1-10の数値）,
        "healthiness": ヘルシー度スコア（1-10の数値）
    }},
    "recommendations": [
        "栄養面での改善提案1",
        "栄養面での改善提案2"
    ]
}}

数値は整数で、文字列は日本語で記述してください。JSONの形式を厳密に守ってください。
"""
        
        try:
            response = self.model.generate_content(prompt)
            # JSONのみを抽出
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                nutrition_data = json.loads(json_match.group())
                return self._validate_nutrition_data(nutrition_data)
            else:
                return self._get_default_nutrition_data()
        except Exception as e:
            print(f"[ERROR] 栄養分析失敗: {e}")
            return self._get_default_nutrition_data()
    
    def _validate_nutrition_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """栄養データの妥当性をチェック"""
        try:
            # 必須フィールドのチェックと型変換
            validated_data = {
                "calories_per_serving": int(data.get("calories_per_serving", 400)),
                "servings": int(data.get("servings", 2)),
                "macronutrients": {
                    "protein_g": float(data.get("macronutrients", {}).get("protein_g", 20)),
                    "carbs_g": float(data.get("macronutrients", {}).get("carbs_g", 40)),
                    "fat_g": float(data.get("macronutrients", {}).get("fat_g", 15)),
                    "fiber_g": float(data.get("macronutrients", {}).get("fiber_g", 5))
                },
                "vitamins_minerals": data.get("vitamins_minerals", ["ビタミンC", "鉄分", "カルシウム"])[:5],
                "health_benefits": data.get("health_benefits", ["バランスの良い栄養", "エネルギー補給"])[:5],
                "dietary_tags": data.get("dietary_tags", ["バランス食"])[:3],
                "nutrition_score": {
                    "overall": max(1, min(10, int(data.get("nutrition_score", {}).get("overall", 7)))),
                    "balance": max(1, min(10, int(data.get("nutrition_score", {}).get("balance", 7)))),
                    "healthiness": max(1, min(10, int(data.get("nutrition_score", {}).get("healthiness", 7))))
                },
                "recommendations": data.get("recommendations", ["野菜を増やしてみましょう"])[:3]
            }
            return validated_data
        except Exception as e:
            print(f"[ERROR] 栄養データ検証失敗: {e}")
            return self._get_default_nutrition_data()
    
    def _get_default_nutrition_data(self) -> Dict[str, Any]:
        """デフォルトの栄養データ"""
        return {
            "calories_per_serving": 400,
            "servings": 2,
            "macronutrients": {
                "protein_g": 20,
                "carbs_g": 40,
                "fat_g": 15,
                "fiber_g": 5
            },
            "vitamins_minerals": ["ビタミンC", "鉄分", "カルシウム"],
            "health_benefits": ["バランスの良い栄養", "エネルギー補給"],
            "dietary_tags": ["バランス食"],
            "nutrition_score": {
                "overall": 7,
                "balance": 7,
                "healthiness": 7
            },
            "recommendations": ["野菜を増やしてバランスを向上させましょう"]
        }
    
    def calculate_total_nutrition(self, nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
        """1食分の総栄養価を計算"""
        servings = nutrition_data.get("servings", 2)
        calories_per_serving = nutrition_data.get("calories_per_serving", 400)
        macros = nutrition_data.get("macronutrients", {})
        
        return {
            "total_calories": calories_per_serving * servings,
            "calories_per_serving": calories_per_serving,
            "servings": servings,
            "total_macros": {
                "protein_g": macros.get("protein_g", 20) * servings,
                "carbs_g": macros.get("carbs_g", 40) * servings,
                "fat_g": macros.get("fat_g", 15) * servings,
                "fiber_g": macros.get("fiber_g", 5) * servings
            },
            "per_serving_macros": macros
        }
    
    def get_nutrition_recommendations(self, nutrition_data: Dict[str, Any], user_goals: str = "balance") -> List[str]:
        """栄養目標に基づく推奨事項"""
        recommendations = []
        macros = nutrition_data.get("macronutrients", {})
        score = nutrition_data.get("nutrition_score", {})
        
        # 基本的な改善提案
        if score.get("balance", 7) < 6:
            recommendations.append("栄養バランスを改善するため、野菜や果物を追加しましょう")
        
        if macros.get("protein_g", 20) < 15:
            recommendations.append("タンパク質を増やすため、卵や豆類を追加してみましょう")
        
        if macros.get("fiber_g", 5) < 3:
            recommendations.append("食物繊維を増やすため、きのこや海藻を加えてみましょう")
        
        # ユーザー目標に応じた提案
        if user_goals == "high_protein":
            recommendations.append("高タンパク質を目指すなら、鶏肉や魚を増量しましょう")
        elif user_goals == "low_carb":
            recommendations.append("低糖質を目指すなら、米やパンの量を減らし野菜を増やしましょう")
        elif user_goals == "diet":
            recommendations.append("ダイエット中なら、調理油を控えめにして蒸し料理にしてみましょう")
        
        return recommendations[:3]  # 最大3つまで

# シングルトンインスタンス
nutrition_agent = NutritionAgent()