from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class DietaryRestriction(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    LACTOSE_FREE = "lactose_free"
    HALAL = "halal"
    KOSHER = "kosher"
    LOW_SODIUM = "low_sodium"
    LOW_CARB = "low_carb"
    KETO = "keto"
    DIABETIC = "diabetic"

class CookingSkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"

class PreferredCuisine(str, Enum):
    JAPANESE = "japanese"
    ITALIAN = "italian"
    CHINESE = "chinese"
    KOREAN = "korean"
    FRENCH = "french"
    INDIAN = "indian"
    THAI = "thai"
    MEXICAN = "mexican"
    AMERICAN = "american"
    MEDITERRANEAN = "mediterranean"

class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"

class UserProfile(BaseModel):
    user_id: str = Field(..., description="ユーザーID（Google Auth）")
    
    # 基本情報
    display_name: Optional[str] = Field(None, description="表示名")
    age_range: Optional[str] = Field(None, description="年齢層 (20s, 30s, 40s, etc.)")
    family_size: Optional[int] = Field(1, description="家族構成人数")
    
    # 食事制限・アレルギー
    dietary_restrictions: List[DietaryRestriction] = Field(default_factory=list, description="食事制限")
    allergies: List[str] = Field(default_factory=list, description="アレルギー食材")
    disliked_ingredients: List[str] = Field(default_factory=list, description="苦手な食材")
    
    # 料理嗜好
    preferred_cuisines: List[PreferredCuisine] = Field(default_factory=list, description="好きな料理ジャンル")
    favorite_ingredients: List[str] = Field(default_factory=list, description="好きな食材")
    spice_tolerance: Optional[int] = Field(3, ge=1, le=5, description="辛さ耐性 (1=苦手, 5=大好き)")
    sweetness_preference: Optional[int] = Field(3, ge=1, le=5, description="甘さ好み (1=控えめ, 5=甘め)")
    
    # 調理スキル・環境
    cooking_skill_level: Optional[CookingSkillLevel] = Field(CookingSkillLevel.BEGINNER, description="調理スキルレベル")
    available_cooking_time: Optional[int] = Field(30, description="平均調理可能時間（分）")
    kitchen_equipment: List[str] = Field(default_factory=list, description="利用可能な調理器具")
    
    # 栄養・健康目標
    health_goals: List[str] = Field(default_factory=list, description="健康目標（ダイエット、筋肉増強など）")
    daily_calorie_target: Optional[int] = Field(None, description="1日の目標カロリー")
    protein_target: Optional[int] = Field(None, description="1日のタンパク質目標（g）")
    
    # 食事パターン
    meal_timing_preferences: Dict[MealType, str] = Field(default_factory=dict, description="食事時間の好み")
    frequent_meal_types: List[MealType] = Field(default_factory=list, description="よく作る食事タイプ")
    
    # 学習データ
    recipe_feedback: Dict[str, Any] = Field(default_factory=dict, description="レシピフィードバック履歴")
    cooking_history: List[Dict[str, Any]] = Field(default_factory=list, description="調理履歴")
    
    # メタ情報
    created_at: datetime = Field(default_factory=datetime.utcnow, description="作成日時")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新日時")
    version: int = Field(1, description="プロファイルバージョン")

class UserProfileUpdate(BaseModel):
    # 更新用のモデル（すべてOptional）
    display_name: Optional[str] = None
    age_range: Optional[str] = None
    family_size: Optional[int] = None
    dietary_restrictions: Optional[List[DietaryRestriction]] = None
    allergies: Optional[List[str]] = None
    disliked_ingredients: Optional[List[str]] = None
    preferred_cuisines: Optional[List[PreferredCuisine]] = None
    favorite_ingredients: Optional[List[str]] = None
    spice_tolerance: Optional[int] = Field(None, ge=1, le=5)
    sweetness_preference: Optional[int] = Field(None, ge=1, le=5)
    cooking_skill_level: Optional[CookingSkillLevel] = None
    available_cooking_time: Optional[int] = None
    kitchen_equipment: Optional[List[str]] = None
    health_goals: Optional[List[str]] = None
    daily_calorie_target: Optional[int] = None
    protein_target: Optional[int] = None
    meal_timing_preferences: Optional[Dict[MealType, str]] = None
    frequent_meal_types: Optional[List[MealType]] = None

class RecipeFeedback(BaseModel):
    recipe_id: str = Field(..., description="レシピID")
    rating: int = Field(..., ge=1, le=5, description="評価 (1-5)")
    comments: Optional[str] = Field(None, description="コメント")
    adjustments_made: Optional[List[str]] = Field(default_factory=list, description="実際に行った調整")
    would_make_again: bool = Field(True, description="また作りたいか")
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5, description="難易度評価")
    time_taken: Optional[int] = Field(None, description="実際の調理時間（分）")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CookingSession(BaseModel):
    session_id: str = Field(..., description="調理セッションID")
    recipe_name: str = Field(..., description="レシピ名")
    ingredients_used: List[str] = Field(..., description="使用した食材")
    cooking_time: Optional[int] = Field(None, description="調理時間（分）")
    success_rating: Optional[int] = Field(None, ge=1, le=5, description="成功度")
    notes: Optional[str] = Field(None, description="メモ")
    photos: List[str] = Field(default_factory=list, description="写真URL")
    created_at: datetime = Field(default_factory=datetime.utcnow)