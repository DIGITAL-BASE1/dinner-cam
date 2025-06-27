import vertexai
from vertexai.generative_models import GenerativeModel
import base64
from google import genai
from google.genai import types
import asyncio
import os
from typing import Optional

# 環境変数から設定を取得（全て必須）
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL_NAME")

# 必須環境変数のチェック
if not PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable is required")
if not LOCATION:
    raise ValueError("LOCATION environment variable is required")
if not IMAGE_MODEL_NAME:
    raise ValueError("IMAGE_MODEL_NAME environment variable is required")

vertexai.init(project=PROJECT_ID, location=LOCATION)

class GenerateImageAgent:
    def __init__(self):
        self.model_name = IMAGE_MODEL_NAME
        self.client = genai.Client()
    
    def generate_single_image(self, step_description: str) -> str:
        """単一の調理手順画像を生成する"""
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f"次の料理手順を視覚的に説明する画像を生成してください。文字などを含めないように注意してください。\n手順: {step_description}"
                    ),
                ],
            )
        ]

        config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])

        try:
            for chunk in self.client.models.generate_content_stream(
                model=self.model_name, contents=contents, config=config
            ):
                if (
                    chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue
                part = chunk.candidates[0].content.parts[0]
                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                    base64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                    return "data:image/png;base64," + base64_data
            return ""
        except Exception as e:
            return ""
    
    async def generate_single_image_async(self, step_description: str) -> str:
        """非同期で単一の調理手順画像を生成する"""
        try:
            # タイムアウト設定 (60秒)
            return await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self.generate_single_image, step_description
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            return ""
        except Exception as e:
            return ""
    
    def generate_images_for_steps(self, steps: list[str]) -> list[str]:
        """複数の手順に対して画像を一括生成する（従来版）"""
        image_urls = []
        for step in steps:
            image_url = self.generate_single_image(step)
            image_urls.append(image_url)
        return image_urls
    
    async def generate_images_for_steps_async(self, steps: list[str]) -> list[str]:
        """複数の手順に対して画像を非同期で一括生成する"""
        tasks = [self.generate_single_image_async(step) for step in steps]
        return await asyncio.gather(*tasks)

# シングルトンインスタンス
image_agent = GenerateImageAgent()

# 従来の関数インターフェース（互換性のため）
def generate_single_image_sync(step: str) -> str:
    return image_agent.generate_single_image(step)

async def generate_single_image_async(step: str) -> str:
    return await image_agent.generate_single_image_async(step)