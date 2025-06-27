import { useState } from 'react';

export function IngredientCheck({ ingredients, onConfirm, onReset }) {
  const [selected, setSelected] = useState(ingredients);

  const toggleIngredient = (ingredient) => {
    setSelected((prev) =>
      prev.includes(ingredient)
        ? prev.filter((item) => item !== ingredient)
        : [...prev, ingredient]
    );
  };

  return (
    <div className="p-4 text-left w-full">
      <div className="flex items-center mb-4">
        <span className="text-2xl mr-2">🔍</span>
        <h2 className="text-lg font-bold text-gray-800">抽出された食材</h2>
      </div>
      
      <p className="text-sm text-gray-600 mb-4">
        使用したい食材をタップして選択してください（複数選択可能）
      </p>

      <div className="flex flex-wrap gap-2 mb-6">
        {ingredients.map((ingredient, i) => (
          <button
            key={i}
            onClick={() => toggleIngredient(ingredient)}
            className={`px-3 py-2 rounded-lg border transition-all duration-200 text-sm font-medium ${
              selected.includes(ingredient)
                ? 'bg-green-500 text-white border-green-600 shadow-md transform scale-105'
                : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200 hover:border-gray-400'
            }`}
          >
            <span className="mr-1">
              {selected.includes(ingredient) ? '✓' : '○'}
            </span>
            {ingredient}
          </button>
        ))}
      </div>

      {selected.length > 0 && (
        <div className="mb-4 p-3 bg-green-50 rounded-lg border border-green-200">
          <p className="text-sm text-green-800 font-medium mb-2">
            📝 選択された食材 ({selected.length}個):
          </p>
          <p className="text-sm text-green-700">
            {selected.join(', ')}
          </p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onReset}
          className="flex-1 bg-gray-500 hover:bg-gray-600 text-white px-4 py-3 rounded-lg transition-colors font-medium"
        >
          キャンセル
        </button>
        <button
          onClick={() => onConfirm(selected)}
          disabled={selected.length === 0}
          className={`flex-1 px-4 py-3 rounded-lg transition-colors font-medium ${
            selected.length > 0
              ? 'bg-blue-500 hover:bg-blue-600 text-white'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {selected.length > 0 ? `${selected.length}個でレシピ作成` : '食材を選択してください'}
        </button>
      </div>
    </div>
  );
}