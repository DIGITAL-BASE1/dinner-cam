import { marked } from 'marked';

export function ChatMessage({ message }) {
  const isBot = message.type === 'bot';
  const renderedContent = marked.parse(message.content || '');

  const formatTime = (timestamp) => {
    return new Intl.DateTimeFormat('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(timestamp));
  };

  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'} mb-4`}>
      <div className={`flex items-start space-x-2 w-full max-w-2xl sm:max-w-3xl ${isBot ? 'flex-row' : 'flex-row-reverse space-x-reverse'}`}>
        {/* アバター */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
          isBot 
            ? 'bg-green-500 text-white' 
            : 'bg-blue-500 text-white'
        }`}>
          {isBot ? '🍳' : '👤'}
        </div>
        
        {/* メッセージバブル */}
        <div className={`rounded-lg px-4 py-2 shadow-sm ${
          isBot 
            ? 'bg-white text-gray-800 border border-gray-200' 
            : 'bg-blue-500 text-white'
        }`}>
          {/* 画像があれば表示 - スマホ対応修正 */}
          {message.image && (
            <div className="mb-2">
              <img 
                src={message.image} 
                alt="Upload" 
                className="w-full max-w-xs sm:max-w-sm rounded-lg border object-cover"
                style={{ maxHeight: '300px' }}
              />
            </div>
          )}
          
          {/* テキストコンテンツ */}
          {message.content && (
            <div 
              className={`prose prose-sm max-w-none ${
                isBot ? 'text-gray-800' : 'text-white prose-invert'
              }`}
              style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}
              dangerouslySetInnerHTML={{ __html: renderedContent }}
            />
          )}
          
          {/* レシピがある場合の特別表示 */}
          {message.recipe && (
            <div className="mt-3 p-4 bg-gradient-to-r from-orange-50 to-yellow-50 rounded-lg border border-orange-200">
              <div className="flex items-center mb-3">
                <span className="text-2xl mr-2">📄</span>
                <h3 className="text-lg font-bold text-orange-800">生成されたレシピ</h3>
              </div>
              <div 
                className="prose prose-sm max-w-none text-gray-800 bg-white p-4 rounded-md shadow-sm"
                dangerouslySetInnerHTML={{ __html: marked.parse(message.recipe) }}
              />
            </div>
          )}

          {/* 栄養情報がある場合の表示 */}
          {message.nutritionData && (
            <div className="mt-3 bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-lg border border-green-200">
              <div className="flex items-center mb-4">
                <span className="text-2xl mr-2">🥗</span>
                <h3 className="text-lg font-bold text-green-800">栄養情報</h3>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center bg-white p-3 rounded-lg shadow-sm">
                  <div className="text-2xl font-bold text-green-600">{message.nutritionData.calories_per_serving}</div>
                  <div className="text-sm text-gray-600">kcal/人</div>
                </div>
                <div className="text-center bg-white p-3 rounded-lg shadow-sm">
                  <div className="text-2xl font-bold text-blue-600">{message.nutritionData.servings}</div>
                  <div className="text-sm text-gray-600">人分</div>
                </div>
              </div>

              <div className="mb-4 bg-white p-3 rounded-lg shadow-sm">
                <h4 className="font-semibold mb-3 text-gray-800 flex items-center">
                  <span className="mr-2">📊</span>
                  栄養成分 (1人分)
                </h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex justify-between p-2 bg-gray-50 rounded">
                    <span>タンパク質</span>
                    <span className="font-medium">{message.nutritionData.macronutrients?.protein_g}g</span>
                  </div>
                  <div className="flex justify-between p-2 bg-gray-50 rounded">
                    <span>炭水化物</span>
                    <span className="font-medium">{message.nutritionData.macronutrients?.carbs_g}g</span>
                  </div>
                  <div className="flex justify-between p-2 bg-gray-50 rounded">
                    <span>脂質</span>
                    <span className="font-medium">{message.nutritionData.macronutrients?.fat_g}g</span>
                  </div>
                  <div className="flex justify-between p-2 bg-gray-50 rounded">
                    <span>食物繊維</span>
                    <span className="font-medium">{message.nutritionData.macronutrients?.fiber_g}g</span>
                  </div>
                </div>
              </div>

              {message.nutritionData.nutrition_score && (
                <div className="mb-4 bg-white p-3 rounded-lg shadow-sm">
                  <h4 className="font-semibold mb-3 text-gray-800 flex items-center">
                    <span className="mr-2">⭐</span>
                    栄養スコア
                  </h4>
                  <div className="flex gap-4 text-sm">
                    <div className="flex-1 text-center p-2 bg-blue-50 rounded">
                      <div className="text-lg font-bold text-blue-600">{message.nutritionData.nutrition_score.overall}/10</div>
                      <div className="text-xs text-gray-600">総合</div>
                    </div>
                    <div className="flex-1 text-center p-2 bg-purple-50 rounded">
                      <div className="text-lg font-bold text-purple-600">{message.nutritionData.nutrition_score.balance}/10</div>
                      <div className="text-xs text-gray-600">バランス</div>
                    </div>
                    <div className="flex-1 text-center p-2 bg-green-50 rounded">
                      <div className="text-lg font-bold text-green-600">{message.nutritionData.nutrition_score.healthiness}/10</div>
                      <div className="text-xs text-gray-600">ヘルシー度</div>
                    </div>
                  </div>
                </div>
              )}

              {message.nutritionData.dietary_tags && message.nutritionData.dietary_tags.length > 0 && (
                <div className="mb-4 bg-white p-3 rounded-lg shadow-sm">
                  <h4 className="font-semibold mb-3 text-gray-800 flex items-center">
                    <span className="mr-2">🏷️</span>
                    食事タグ
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {message.nutritionData.dietary_tags.map((tag, i) => (
                      <span key={i} className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium border border-green-200">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {message.nutritionData.health_benefits && message.nutritionData.health_benefits.length > 0 && (
                <div className="mb-4 bg-white p-3 rounded-lg shadow-sm">
                  <h4 className="font-semibold mb-3 text-gray-800 flex items-center">
                    <span className="mr-2">💪</span>
                    健康効果
                  </h4>
                  <ul className="text-sm text-gray-700 space-y-1">
                    {message.nutritionData.health_benefits.map((benefit, i) => (
                      <li key={i} className="flex items-start">
                        <span className="text-green-500 mr-2 mt-0.5">•</span>
                        <span>{benefit}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {message.nutritionData.recommendations && message.nutritionData.recommendations.length > 0 && (
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <h4 className="font-semibold mb-3 text-orange-800 flex items-center">
                    <span className="mr-2">💡</span>
                    改善提案
                  </h4>
                  <ul className="text-sm text-orange-700 space-y-1">
                    {message.nutritionData.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start">
                        <span className="text-orange-500 mr-2 mt-0.5">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* 単一手順画像がある場合の表示 - 修正版 */}
          {message.stepImage && (
            <div className="mt-3 bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border border-blue-200">
              <div className="flex items-center mb-3">
                <span className="text-2xl mr-2">👨‍🍳</span>
                <h3 className="font-bold text-blue-800">
                  手順 {message.stepImage.stepNumber}
                </h3>
              </div>
              
              {/* 修正：Markdownをレンダリングして表示 */}
              <div 
                className="mb-3 text-sm text-gray-700 bg-white p-3 rounded-md shadow-sm prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: marked.parse(message.stepImage.step_text || '') }}
              />
              
              {message.stepImage.image_url && (
                <div className="bg-white p-2 rounded-md shadow-sm">
                  <img
                    src={message.stepImage.image_url}
                    alt={`手順${message.stepImage.step_index + 1}`}
                    className="w-full rounded border object-cover"
                    style={{ maxHeight: '400px' }}
                  />
                </div>
              )}
              
              {message.stepImage.error && (
                <div className="w-full h-32 bg-red-100 rounded border flex items-center justify-center">
                  <span className="text-red-500 text-sm">画像生成に失敗しました</span>
                </div>
              )}
            </div>
          )}

          {/* 手順画像がある場合の表示（従来版 - 使わない予定だが念のため残す） */}
          {message.stepImages && (
            <div className="mt-3 bg-white p-4 rounded-lg border">
              <div className="space-y-4">
                {message.stepImages.map((step, i) => (
                  <div key={i} className="bg-gray-50 p-3 rounded border">
                    {/* 修正：Markdownをレンダリング */}
                    <div 
                      className="mb-2 font-semibold text-sm prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: marked.parse(`${i + 1}. ${step.text}`) }}
                    />
                    
                    {step.image && (
                      <img
                        src={step.image}
                        alt={`step-${i + 1}`}
                        className="w-full rounded border object-cover"
                        style={{ maxHeight: '300px' }}
                      />
                    )}
                    
                    {step.error && (
                      <div className="w-full h-24 bg-red-100 rounded border flex items-center justify-center">
                        <span className="text-red-500 text-sm">画像生成に失敗しました</span>
                      </div>
                    )}
                    
                    {!step.image && !step.error && (
                      <div className="w-full h-24 bg-gray-200 rounded border flex items-center justify-center">
                        <span className="text-gray-400 text-sm">画像なし</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* タイムスタンプ */}
          <div className={`text-xs mt-1 ${
            isBot ? 'text-gray-500' : 'text-blue-100'
          }`}>
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    </div>
  );
}