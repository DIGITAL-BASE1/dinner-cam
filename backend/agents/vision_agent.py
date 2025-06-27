from vertexai.preview.generative_models import GenerativeModel, Part
import vertexai
import os

# 環境変数から設定を取得（全て必須）
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
MODEL_NAME = os.getenv("TEXT_MODEL_NAME")

# 必須環境変数のチェック
if not PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable is required")
if not LOCATION:
    raise ValueError("LOCATION environment variable is required")
if not MODEL_NAME:
    raise ValueError("TEXT_MODEL_NAME environment variable is required")

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel(MODEL_NAME)

def extract_ingredients_from_image(image_path: str) -> list[str]:
    with open(image_path, "rb") as f:
        image_data = f.read()

    prompt = (
        "この写真は冷蔵庫の中です。"
        "料理に使えそうな食材を、可能な限り多く日本語で"
        "簡潔に半角カンマ区切り（要はcsv形式）でリストアップしてください。"
        "また、はい、いいえ等の返答も絶対に含めないでください。"
    )

    response = model.generate_content([
        prompt,
        Part.from_data(data=image_data, mime_type="image/jpeg")
    ])

    return [item.strip() for item in response.text.strip().split(",") if item.strip()]