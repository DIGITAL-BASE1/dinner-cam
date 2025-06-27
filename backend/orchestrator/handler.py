from langchain_google_vertexai import ChatVertexAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from typing import List, Dict, Any
import asyncio
import json

from agents.vision_agent import extract_ingredients_from_image
from agents.recipe_agent import recipe_agent
from agents.generate_image_agent import image_agent
from agents.nutrition_agent import nutrition_agent

class DinnerCamOrchestrator:
    def __init__(self):
        self.llm = ChatVertexAI(
            model="gemini-2.5-flash-preview-05-20",
            temperature=0.7
        )
        self.tools = self._setup_tools()
        self.agent_executor = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
    
    def _setup_tools(self) -> List[Tool]:
        """エージェントツールをセットアップ"""
        return [
            Tool(
                name="ImageIngredientAnalyzer",
                func=self._analyze_ingredients_tool,
                description="冷蔵庫画像から食材を抽出します。入力は画像パス文字列。"
            ),
            Tool(
                name="RecipeGenerator",
                func=self._generate_recipe_tool,
                description="カンマ区切りの食材リストからレシピを生成します。"
            ),
            Tool(
                name="ImageGenerator",
                func=self._generate_step_image_tool,
                description="調理手順の説明テキストから画像を生成します。"
            ),
            Tool(
                name="RecipeAnalyzer",
                func=self._analyze_recipe_tool,
                description="レシピテキストを分析して手順数や難易度を判定します。"
            ),
            Tool(
                name="NutritionAnalyzer",
                func=self._analyze_nutrition_tool,
                description="レシピと食材から栄養価を分析します。入力はレシピテキスト。"
            )
        ]
    
    def _analyze_ingredients_tool(self, image_path: str) -> str:
        """食材抽出ツール"""
        ingredients = extract_ingredients_from_image(image_path)
        return ", ".join(ingredients)
    
    def _generate_recipe_tool(self, ingredients_csv: str) -> str:
        """レシピ生成ツール"""
        ingredients = [i.strip() for i in ingredients_csv.split(",")]
        return recipe_agent.generate_recipe_from_ingredients(ingredients)
    
    def _generate_step_image_tool(self, step_description: str) -> str:
        """手順画像生成ツール"""
        image_url = image_agent.generate_single_image(step_description)
        return image_url if image_url else "画像生成に失敗しました"
    
    def _analyze_recipe_tool(self, recipe_text: str) -> str:
        """レシピ分析ツール"""
        analysis = recipe_agent.analyze_recipe_complexity(recipe_text)
        return json.dumps(analysis, ensure_ascii=False)
    
    def run_agent(self, message: str) -> str:
        """エージェントを実行"""
        return self.agent_executor.run(message)
    
    def _analyze_nutrition_tool(self, recipe_text: str) -> str:
        """栄養分析ツール"""
        # 現在の食材リストを取得（簡易的に最後に使用された食材を想定）
        ingredients = ["鶏肉", "玉ねぎ", "にんじん"]  # TODO: 実際の食材リストを渡す仕組みを改善
        nutrition_data = nutrition_agent.analyze_recipe_nutrition(recipe_text, ingredients)
        return json.dumps(nutrition_data, ensure_ascii=False)
    
    async def generate_complete_recipe_async(self, ingredients: List[str], with_images: bool = False, with_nutrition: bool = True) -> Dict[str, Any]:
        """完全なレシピを非同期で生成（全エージェント協調）"""
        # 1. レシピ生成
        recipe = recipe_agent.generate_recipe_from_ingredients(ingredients)
        
        # 2. 手順抽出
        steps_text = recipe_agent.extract_steps_from_text(recipe)
        
        # 3. レシピ分析
        analysis = recipe_agent.analyze_recipe_complexity(recipe)
        
        result = {
            'recipe': recipe,
            'steps_text': steps_text,
            'analysis': analysis,
            'steps_with_images': [],
            'nutrition': None
        }
        
        # 4. 栄養分析（オプション）
        if with_nutrition:
            nutrition_data = nutrition_agent.analyze_recipe_nutrition(recipe, ingredients)
            result['nutrition'] = nutrition_data
        
        # 5. 画像生成（オプション）
        if with_images and steps_text:
            image_urls = await image_agent.generate_images_for_steps_async(steps_text)
            result['steps_with_images'] = [
                {'text': step, 'image': image}
                for step, image in zip(steps_text, image_urls)
            ]
        
        return result

# シングルトンインスタンス
orchestrator = DinnerCamOrchestrator()

# 従来の関数インターフェース（互換性のため）
def run_agent(message: str) -> str:
    return orchestrator.run_agent(message)