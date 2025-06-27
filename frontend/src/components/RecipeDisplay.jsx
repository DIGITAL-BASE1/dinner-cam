import { marked } from 'marked';

export function RecipeDisplay({ ingredients, recipe, steps, nutritionData, onReset, isStreaming, chatMode = false }) {
  const renderedHTML = marked.parse(recipe || '');

  return (
    <div className={`p-4 text-left ${chatMode ? 'w-full' : 'max-w-md mx-auto'}`}>
      {!chatMode && <h2 className="text-xl font-bold mb-2 text-center">レシピ提案</h2>}

      {!chatMode && ingredients.length > 0 && (
        <p className="text-sm text-gray-600 mb-4 text-center">
          使用食材: <span className="font-medium">{ingredients.join(', ')}</span>
        </p>
      )}

      {/* レシピ本文 */}
      {recipe && (
        <div
          className="prose prose-sm sm:prose lg:prose-lg max-w-none bg-white p-4 rounded shadow overflow-x-auto mb-6"
          dangerouslySetInnerHTML={{ __html: renderedHTML }}
        />
      )}

      {/* レシピがまだ生成中の場合 */}
      {!recipe && isStreaming && (
        <div className="bg-gray-100 p-4 rounded shadow mb-6 animate-pulse">
          <p className="text-gray-500">レシピを生成中...</p>
        </div>
      )}

      {/* 栄養情報 */}
      {nutritionData && (
        <div className="mt-6 bg-green-50 p-4 rounded shadow">
          <h3 className="text-lg font-bold mb-3 text-green-800">🥗 栄養情報</h3>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{nutritionData.calories_per_serving}</div>
              <div className="text-sm text-gray-600">kcal/人</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{nutritionData.servings}</div>
              <div className="text-sm text-gray-600">人分</div>
            </div>
          </div>

          <div className="mb-4">
            <h4 className="font-semibold mb-2">栄養成分 (1人分)</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>タンパク質: {nutritionData.macronutrients?.protein_g}g</div>
              <div>炭水化物: {nutritionData.macronutrients?.carbs_g}g</div>
              <div>脂質: {nutritionData.macronutrients?.fat_g}g</div>
              <div>食物繊維: {nutritionData.macronutrients?.fiber_g}g</div>
            </div>
          </div>

          {nutritionData.nutrition_score && (
            <div className="mb-4">
              <h4 className="font-semibold mb-2">栄養スコア</h4>
              <div className="flex gap-4 text-sm">
                <div>総合: {nutritionData.nutrition_score.overall}/10</div>
                <div>バランス: {nutritionData.nutrition_score.balance}/10</div>
                <div>ヘルシー度: {nutritionData.nutrition_score.healthiness}/10</div>
              </div>
            </div>
          )}

          {nutritionData.dietary_tags && nutritionData.dietary_tags.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold mb-2">食事タグ</h4>
              <div className="flex flex-wrap gap-1">
                {nutritionData.dietary_tags.map((tag, i) => (
                  <span key={i} className="bg-green-200 text-green-800 px-2 py-1 rounded-full text-xs">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {nutritionData.health_benefits && nutritionData.health_benefits.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold mb-2">健康効果</h4>
              <ul className="text-sm text-gray-700">
                {nutritionData.health_benefits.map((benefit, i) => (
                  <li key={i} className="mb-1">• {benefit}</li>
                ))}
              </ul>
            </div>
          )}

          {nutritionData.recommendations && nutritionData.recommendations.length > 0 && (
            <div>
              <h4 className="font-semibold mb-2 text-orange-700">💡 改善提案</h4>
              <ul className="text-sm text-orange-700">
                {nutritionData.recommendations.map((rec, i) => (
                  <li key={i} className="mb-1">• {rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 栄養情報がストリーミング中の場合 */}
      {!nutritionData && isStreaming && recipe && (
        <div className="mt-6 bg-gray-100 p-4 rounded shadow animate-pulse">
          <p className="text-gray-500">栄養分析中...</p>
        </div>
      )}

      {/* 画像付き手順 */}
      {steps.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-bold mb-2">調理手順（画像付き）</h3>
          <ul className="space-y-4">
            {steps.map((step, i) => (
              <li key={i} className="bg-gray-100 p-4 rounded shadow">
                <p className="mb-2 font-semibold">{i + 1}. {step.text}</p>
                
                {/* 画像の状態に応じて表示を変更 */}
                {step.loading && (
                  <div className="w-full h-32 bg-gray-200 rounded border flex items-center justify-center animate-pulse">
                    <span className="text-gray-500">画像生成中...</span>
                  </div>
                )}
                
                {step.image && !step.loading && (
                  <img
                    src={step.image}
                    alt={`step-${i + 1}`}
                    className="w-full rounded border"
                  />
                )}
                
                {step.error && !step.loading && (
                  <div className="w-full h-32 bg-red-100 rounded border flex items-center justify-center">
                    <span className="text-red-500">画像生成に失敗しました</span>
                  </div>
                )}
                
                {!step.image && !step.loading && !step.error && (
                  <div className="w-full h-32 bg-gray-200 rounded border flex items-center justify-center">
                    <span className="text-gray-400">画像なし</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 手順が生成予定だが、まだ始まっていない場合 */}
      {steps.length === 0 && isStreaming && recipe && (
        <div className="mt-6">
          <h3 className="text-lg font-bold mb-2">調理手順（画像付き）</h3>
          <div className="bg-gray-100 p-4 rounded shadow animate-pulse">
            <p className="text-gray-500">手順画像を準備中...</p>
          </div>
        </div>
      )}

      <button
        onClick={onReset}
        className={`mt-6 w-full bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded ${chatMode ? 'bg-green-600 hover:bg-green-700' : ''}`}
        disabled={isStreaming}
      >
        {isStreaming ? '生成中...' : chatMode ? '新しい料理を作る' : 'もう一度やる'}
      </button>
    </div>
  );
}