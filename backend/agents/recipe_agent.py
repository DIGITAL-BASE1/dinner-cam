import vertexai
from vertexai.generative_models import GenerativeModel
import re
import os
from typing import List, Dict, Optional, Any

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

class RecipeAgent:
    def __init__(self):
        self.model = GenerativeModel(TEXT_MODEL_NAME)
    
    def generate_recipe_from_ingredients(self, ingredients: List[str], user_preferences: Optional[Dict[str, Any]] = None) -> str:
        """食材リストからレシピを生成する（プロファイル対応）"""
        
        # 基本プロンプト
        prompt = f"""
あなたは料理の専門家です。次の食材を使って夜ご飯を1品提案してください。
食材: {', '.join(ingredients)}
"""
        
        # ユーザープロファイルに基づく制約を追加
        if user_preferences:
            prompt += self._build_preferences_constraints(user_preferences)
        
        prompt += """
以下の形式で回答してください：
- 日本語で簡潔にレシピ名・材料・手順を提示してください。
- Markdown形式で出力してください。
- 手順は番号付きリスト（1. 2. 3. ...）で明確に記載してください。
"""
        
        response = self.model.generate_content(prompt)
        return response.text
    
    def generate_recipe_from_dish_name(self, dish_name: str, preferences: Dict = None, user_preferences: Optional[Dict[str, Any]] = None) -> str:
        """料理名からレシピを生成する（プロファイル対応）"""
        base_prompt = f"""
あなたは料理の専門家です。「{dish_name}」のレシピを提案してください。
"""
        
        # ユーザープロファイルに基づく制約を追加
        if user_preferences:
            base_prompt += self._build_preferences_constraints(user_preferences)
        
        base_prompt += """
以下の形式で回答してください：
- 日本語で簡潔にレシピ名・材料・手順を提示してください。
- Markdown形式で出力してください。
- 手順は番号付きリスト（1. 2. 3. ...）で明確に記載してください。
- 一般的で作りやすいレシピにしてください。
"""
        
        # 追加の要求があれば追加
        if preferences:
            if preferences.get("time_constraint"):
                base_prompt += f"\n- 調理時間: {preferences['time_constraint']}"
            if preferences.get("difficulty_level"):
                base_prompt += f"\n- 難易度: {preferences['difficulty_level']}"
            if preferences.get("cooking_method"):
                base_prompt += f"\n- 調理法: {preferences['cooking_method']}"
        
        response = self.model.generate_content(base_prompt)
        return response.text
    
    def generate_recipe_flexible(self, ingredients: List[str] = None, dish_name: str = None, preferences: Dict = None) -> str:
        """柔軟なレシピ生成（食材または料理名から）"""
        if dish_name and ingredients:
            # 食材と料理名両方ある場合：料理名を優先して食材を使用
            return self.generate_recipe_with_both(dish_name, ingredients, preferences)
        elif dish_name:
            # 料理名のみ
            return self.generate_recipe_from_dish_name(dish_name, preferences)
        elif ingredients:
            # 食材のみ
            return self.generate_recipe_from_ingredients(ingredients)
        else:
            # どちらもない場合は簡単な料理を提案
            return self.generate_recipe_from_dish_name("簡単で美味しい家庭料理", preferences)
    
    def generate_recipe_with_both(self, dish_name: str, ingredients: List[str], preferences: Dict = None) -> str:
        """食材と料理名両方を使ったレシピ生成"""
        base_prompt = f"""
あなたは料理の専門家です。「{dish_name}」を「{', '.join(ingredients)}」を使って作るレシピを提案してください。
以下の条件を守ってください：
- 料理名: {dish_name}
- 主要食材: {', '.join(ingredients)}
- 日本語で簡潔にレシピ名・材料・手順を提示してください。
- Markdown形式で出力してください。
- 手順は番号付きリスト（1. 2. 3. ...）で明確に記載してください。
- 指定された食材を必ず使用してください。
"""
        
        # 追加の要求があれば追加
        if preferences:
            if preferences.get("time_constraint"):
                base_prompt += f"\n- 調理時間: {preferences['time_constraint']}"
            if preferences.get("difficulty_level"):
                base_prompt += f"\n- 難易度: {preferences['difficulty_level']}"
            if preferences.get("cooking_method"):
                base_prompt += f"\n- 調理法: {preferences['cooking_method']}"
        
        response = self.model.generate_content(base_prompt)
        return response.text
    
    def extract_steps_from_text(self, recipe_text: str) -> List[str]:
        """レシピテキストから調理手順を抽出する"""
        # 番号付きリストの行を抽出（1. 2. 3. など）
        steps = []
        for line in recipe_text.splitlines():
            line = line.strip()
            if re.match(r"\d+\.\s", line):
                # 番号部分を除去してテキストのみ取得
                step_text = re.sub(r"^\d+\.\s*", "", line).strip()
                if step_text:
                    steps.append(step_text)
        return steps
    
    def analyze_recipe_complexity(self, recipe_text: str) -> dict:
        """レシピの複雑さを分析する"""
        steps = self.extract_steps_from_text(recipe_text)
        
        # 調理時間の推定（簡単な分析）
        time_keywords = {
            '煮る': 15, '茹でる': 10, '焼く': 10, '炒める': 5,
            '蒸す': 20, '漬ける': 60, '冷やす': 30, '発酵': 120
        }
        
        estimated_time = 10  # ベース時間
        for step in steps:
            for keyword, time in time_keywords.items():
                if keyword in step:
                    estimated_time += time
                    break
        
        return {
            'step_count': len(steps),
            'estimated_time_minutes': min(estimated_time, 180),  # 最大3時間
            'difficulty': 'easy' if len(steps) <= 3 else 'medium' if len(steps) <= 6 else 'hard'
        }
    
    def _build_preferences_constraints(self, preferences: Dict[str, Any]) -> str:
        """ユーザープロファイルから制約文を構築"""
        constraints = []
        
        # 食事制限・アレルギー
        if preferences.get('dietary_restrictions'):
            restrictions = ', '.join(preferences['dietary_restrictions'])
            constraints.append(f"食事制限: {restrictions}に対応してください")
        
        if preferences.get('allergies'):
            allergies = ', '.join(preferences['allergies'])
            constraints.append(f"アレルギー食材は絶対に使用しないでください: {allergies}")
        
        if preferences.get('disliked_ingredients'):
            dislikes = ', '.join(preferences['disliked_ingredients'])
            constraints.append(f"苦手な食材は避けてください: {dislikes}")
        
        # 好みの食材・料理ジャンル
        if preferences.get('favorite_ingredients'):
            favorites = ', '.join(preferences['favorite_ingredients'][:3])  # 最大3つまで
            constraints.append(f"できるだけ次の食材を活用してください: {favorites}")
        
        if preferences.get('preferred_cuisines'):
            cuisines = ', '.join(preferences['preferred_cuisines'][:2])  # 最大2つまで
            constraints.append(f"料理ジャンルの好み: {cuisines}")
        
        # 調理スキルレベル
        skill_level = preferences.get('cooking_skill_level', 'beginner')
        if skill_level == 'beginner':
            constraints.append("初心者でも作りやすい簡単なレシピにしてください")
        elif skill_level == 'advanced' or skill_level == 'professional':
            constraints.append("少し高度な調理技法を使った本格的なレシピでも構いません")
        
        # 調理時間制限
        if preferences.get('available_cooking_time'):
            time_limit = preferences['available_cooking_time']
            constraints.append(f"調理時間は約{time_limit}分以内で完成するようにしてください")
        
        # 家族構成
        if preferences.get('family_size') and preferences['family_size'] > 1:
            family_size = preferences['family_size']
            constraints.append(f"{family_size}人分のレシピにしてください")
        
        # 辛さ・甘さ制限
        if preferences.get('spice_tolerance'):
            spice_level = preferences['spice_tolerance']
            if spice_level <= 2:
                constraints.append("辛味は控えめにしてください")
            elif spice_level >= 4:
                constraints.append("スパイシーな味付けでも構いません")
        
        # 健康目標
        if preferences.get('health_goals'):
            goals = preferences['health_goals']
            if 'ダイエット' in str(goals):
                constraints.append("カロリー控えめで栄養バランスの良いレシピにしてください")
            if '筋肉増強' in str(goals):
                constraints.append("タンパク質を多く含むレシピにしてください")
            if '低糖質' in str(goals):
                constraints.append("糖質を抑えたレシピにしてください")
        
        # 利用可能な調理器具
        if preferences.get('kitchen_equipment'):
            equipment = preferences['kitchen_equipment']
            if 'オーブン' not in equipment:
                constraints.append("オーブンを使わないレシピにしてください")
            if '電子レンジ' in equipment and len(equipment) <= 3:
                constraints.append("簡単な調理器具のみを使用してください")
        
        if constraints:
            return "\n\n【制約条件】\n- " + "\n- ".join(constraints) + "\n"
        return ""

# シングルトンインスタンス
recipe_agent = RecipeAgent()

# 従来の関数インターフェース（互換性のため）
def generate_recipe_from_ingredients(ingredients: List[str]) -> str:
    return recipe_agent.generate_recipe_from_ingredients(ingredients)

def extract_steps_from_text(recipe_text: str) -> List[str]:
    return recipe_agent.extract_steps_from_text(recipe_text)