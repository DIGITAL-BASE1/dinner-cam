import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const DIETARY_RESTRICTIONS = [
  { value: 'vegetarian', label: 'ベジタリアン', icon: '🥬' },
  { value: 'vegan', label: 'ビーガン', icon: '🌱' },
  { value: 'gluten_free', label: 'グルテンフリー', icon: '🌾' },
  { value: 'lactose_free', label: '乳糖不耐症', icon: '🥛' },
  { value: 'halal', label: 'ハラル', icon: '☪️' },
  { value: 'kosher', label: 'コーシャ', icon: '✡️' },
  { value: 'low_sodium', label: '低塩分', icon: '🧂' },
  { value: 'low_carb', label: '低糖質', icon: '🍞' },
  { value: 'keto', label: 'ケトジェニック', icon: '🥑' },
  { value: 'diabetic', label: '糖尿病対応', icon: '💉' }
];

const PREFERRED_CUISINES = [
  { value: 'japanese', label: '和食', icon: '🍣' },
  { value: 'italian', label: 'イタリア料理', icon: '🍝' },
  { value: 'chinese', label: '中華料理', icon: '🥟' },
  { value: 'korean', label: '韓国料理', icon: '🌶️' },
  { value: 'french', label: 'フランス料理', icon: '🥖' },
  { value: 'indian', label: 'インド料理', icon: '🍛' },
  { value: 'thai', label: 'タイ料理', icon: '🥥' },
  { value: 'mexican', label: 'メキシコ料理', icon: '🌮' },
  { value: 'american', label: 'アメリカ料理', icon: '🍔' },
  { value: 'mediterranean', label: '地中海料理', icon: '🫒' }
];

const COOKING_SKILL_LEVELS = [
  { value: 'beginner', label: '初心者', icon: '🔰' },
  { value: 'intermediate', label: '中級者', icon: '👨‍🍳' },
  { value: 'advanced', label: '上級者', icon: '⭐' },
  { value: 'professional', label: 'プロ', icon: '👨‍🍳⭐' }
];

const KITCHEN_EQUIPMENT = [
  '電子レンジ', 'オーブン', 'ガスコンロ', 'IHコンロ', 'フライパン', 
  '鍋', '炊飯器', 'ミキサー', 'フードプロセッサー', 'ホットプレート',
  'トースター', '圧力鍋', '蒸し器', 'グリル', 'オーブンレンジ'
];

export function ProfileSettings({ onClose }) {
  const { getAuthHeaders } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  
  // リクエスト重複防止用
  const abortControllerRef = useRef(null);
  const isLoadingRef = useRef(false);

  // フォーム状態
  const [formData, setFormData] = useState({
    display_name: '',
    age_range: '',
    family_size: 1,
    dietary_restrictions: [],
    allergies: [],
    disliked_ingredients: [],
    preferred_cuisines: [],
    favorite_ingredients: [],
    spice_tolerance: 3,
    sweetness_preference: 3,
    cooking_skill_level: 'beginner',
    available_cooking_time: 30,
    kitchen_equipment: [],
    health_goals: [],
    daily_calorie_target: null,
    protein_target: null
  });

  useEffect(() => {
    loadProfile();
    
    // クリーンアップ関数
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      isLoadingRef.current = false;
    };
  }, []);

  const loadProfile = async () => {
    // 重複リクエストを防止
    if (isLoadingRef.current) {
      console.log('[DEBUG] プロファイル読み込み中のため、リクエストをスキップ');
      return;
    }
    
    isLoadingRef.current = true;
    setLoading(true);
    
    // 既存のリクエストをキャンセル
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // 新しいAbortControllerを作成
    abortControllerRef.current = new AbortController();
    
    try {
      console.log('[DEBUG] プロファイル読み込み開始');
      
      // タイムアウトを設定（10秒）
      const timeoutId = setTimeout(() => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
      }, 10000);
      
      const response = await fetch(`${API_BASE_URL}/profile`, {
        headers: getAuthHeaders(),
        signal: abortControllerRef.current.signal
      });
      
      clearTimeout(timeoutId);

      if (response.ok) {
        const profileData = await response.json();
        console.log('[DEBUG] プロファイル読み込み成功');
        setProfile(profileData);
        setFormData({
          display_name: profileData.display_name || '',
          age_range: profileData.age_range || '',
          family_size: profileData.family_size || 1,
          dietary_restrictions: profileData.dietary_restrictions || [],
          allergies: profileData.allergies || [],
          disliked_ingredients: profileData.disliked_ingredients || [],
          preferred_cuisines: profileData.preferred_cuisines || [],
          favorite_ingredients: profileData.favorite_ingredients || [],
          spice_tolerance: profileData.spice_tolerance || 3,
          sweetness_preference: profileData.sweetness_preference || 3,
          cooking_skill_level: profileData.cooking_skill_level || 'beginner',
          available_cooking_time: profileData.available_cooking_time || 30,
          kitchen_equipment: profileData.kitchen_equipment || [],
          health_goals: profileData.health_goals || [],
          daily_calorie_target: profileData.daily_calorie_target,
          protein_target: profileData.protein_target
        });
      } else {
        console.error('[ERROR] プロファイル読み込み失敗:', response.status);
        // エラー時もデフォルト値で初期化
        setProfile({});
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('[INFO] プロファイル読み込みがキャンセルされました');
      } else {
        console.error('[ERROR] プロファイル読み込みエラー:', error);
        // エラー時もデフォルト値で初期化
        setProfile({});
      }
    } finally {
      isLoadingRef.current = false;
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE_URL}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const result = await response.json();
        setProfile(result.profile);
        alert('プロファイルを保存しました！');
      } else {
        throw new Error('保存に失敗しました');
      }
    } catch (error) {
      console.error('プロファイル保存エラー:', error);
      alert('保存に失敗しました。もう一度お試しください。');
    } finally {
      setSaving(false);
    }
  };

  const handleArrayToggle = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].includes(value)
        ? prev[field].filter(item => item !== value)
        : [...prev[field], value]
    }));
  };

  const handleStringArrayChange = (field, value, action = 'add') => {
    if (action === 'add' && value.trim()) {
      setFormData(prev => ({
        ...prev,
        [field]: [...prev[field], value.trim()]
      }));
    } else if (action === 'remove') {
      setFormData(prev => ({
        ...prev,
        [field]: prev[field].filter(item => item !== value)
      }));
    }
  };

  const TabButton = ({ id, label, icon }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${
        activeTab === id
          ? 'bg-blue-500 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
    >
      <span>{icon}</span>
      <span className="hidden md:inline">{label}</span>
    </button>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <span>⚙️</span>
          プロファイル設定
        </h1>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
        >
          閉じる
        </button>
      </div>

      {/* タブナビゲーション */}
      <div className="flex flex-wrap gap-2 mb-6 overflow-x-auto">
        <TabButton id="basic" label="基本情報" icon="👤" />
        <TabButton id="dietary" label="食事制限" icon="🥗" />
        <TabButton id="preferences" label="好み" icon="❤️" />
        <TabButton id="cooking" label="調理環境" icon="🍳" />
        <TabButton id="health" label="健康目標" icon="💪" />
      </div>

      <div className="bg-white rounded-lg shadow-lg p-6">
        {/* 基本情報タブ */}
        {activeTab === 'basic' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">基本情報</h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                表示名
              </label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="お名前またはニックネーム"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                年齢層
              </label>
              <select
                value={formData.age_range}
                onChange={(e) => setFormData(prev => ({ ...prev, age_range: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">選択してください</option>
                <option value="10s">10代</option>
                <option value="20s">20代</option>
                <option value="30s">30代</option>
                <option value="40s">40代</option>
                <option value="50s">50代</option>
                <option value="60s">60代以上</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                家族構成人数
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.family_size}
                onChange={(e) => setFormData(prev => ({ ...prev, family_size: parseInt(e.target.value) || 1 }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        )}

        {/* 食事制限タブ */}
        {activeTab === 'dietary' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">食事制限・アレルギー</h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                食事制限
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {DIETARY_RESTRICTIONS.map(restriction => (
                  <button
                    key={restriction.value}
                    onClick={() => handleArrayToggle('dietary_restrictions', restriction.value)}
                    className={`p-3 rounded-lg border-2 transition-colors text-left ${
                      formData.dietary_restrictions.includes(restriction.value)
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="text-lg mb-1">{restriction.icon}</div>
                    <div className="text-sm font-medium">{restriction.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                アレルギー食材
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {formData.allergies.map((allergy, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm flex items-center gap-2"
                  >
                    {allergy}
                    <button
                      onClick={() => handleStringArrayChange('allergies', allergy, 'remove')}
                      className="text-red-600 hover:text-red-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="アレルギー食材を入力してEnter"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleStringArrayChange('allergies', e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                苦手な食材
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {formData.disliked_ingredients.map((ingredient, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm flex items-center gap-2"
                  >
                    {ingredient}
                    <button
                      onClick={() => handleStringArrayChange('disliked_ingredients', ingredient, 'remove')}
                      className="text-yellow-600 hover:text-yellow-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="苦手な食材を入力してEnter"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleStringArrayChange('disliked_ingredients', e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>
          </div>
        )}

        {/* 嗜好タブ */}
        {activeTab === 'preferences' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">料理の好み</h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                好きな料理ジャンル
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {PREFERRED_CUISINES.map(cuisine => (
                  <button
                    key={cuisine.value}
                    onClick={() => handleArrayToggle('preferred_cuisines', cuisine.value)}
                    className={`p-3 rounded-lg border-2 transition-colors text-left ${
                      formData.preferred_cuisines.includes(cuisine.value)
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="text-lg mb-1">{cuisine.icon}</div>
                    <div className="text-sm font-medium">{cuisine.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                好きな食材
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {formData.favorite_ingredients.map((ingredient, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm flex items-center gap-2"
                  >
                    {ingredient}
                    <button
                      onClick={() => handleStringArrayChange('favorite_ingredients', ingredient, 'remove')}
                      className="text-green-600 hover:text-green-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="好きな食材を入力してEnter"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleStringArrayChange('favorite_ingredients', e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  辛さ耐性: {formData.spice_tolerance}/5
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={formData.spice_tolerance}
                  onChange={(e) => setFormData(prev => ({ ...prev, spice_tolerance: parseInt(e.target.value) }))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>苦手</span>
                  <span>大好き</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  甘さ好み: {formData.sweetness_preference}/5
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={formData.sweetness_preference}
                  onChange={(e) => setFormData(prev => ({ ...prev, sweetness_preference: parseInt(e.target.value) }))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>控えめ</span>
                  <span>甘め</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 調理環境タブ */}
        {activeTab === 'cooking' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">調理環境・スキル</h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                調理スキルレベル
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {COOKING_SKILL_LEVELS.map(level => (
                  <button
                    key={level.value}
                    onClick={() => setFormData(prev => ({ ...prev, cooking_skill_level: level.value }))}
                    className={`p-3 rounded-lg border-2 transition-colors text-center ${
                      formData.cooking_skill_level === level.value
                        ? 'border-purple-500 bg-purple-50 text-purple-700'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="text-lg mb-1">{level.icon}</div>
                    <div className="text-sm font-medium">{level.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                平均調理可能時間: {formData.available_cooking_time}分
              </label>
              <input
                type="range"
                min="10"
                max="120"
                step="10"
                value={formData.available_cooking_time}
                onChange={(e) => setFormData(prev => ({ ...prev, available_cooking_time: parseInt(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>10分</span>
                <span>2時間</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                利用可能な調理器具
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {KITCHEN_EQUIPMENT.map(equipment => (
                  <label
                    key={equipment}
                    className="flex items-center space-x-2 p-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    <input
                      type="checkbox"
                      checked={formData.kitchen_equipment.includes(equipment)}
                      onChange={() => handleArrayToggle('kitchen_equipment', equipment)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm">{equipment}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 健康目標タブ */}
        {activeTab === 'health' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">健康目標・栄養管理</h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                健康目標
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {formData.health_goals.map((goal, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm flex items-center gap-2"
                  >
                    {goal}
                    <button
                      onClick={() => handleStringArrayChange('health_goals', goal, 'remove')}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="健康目標を入力してEnter（例：ダイエット、筋肉増強など）"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleStringArrayChange('health_goals', e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  1日の目標カロリー (kcal)
                </label>
                <input
                  type="number"
                  min="1000"
                  max="4000"
                  value={formData.daily_calorie_target || ''}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    daily_calorie_target: e.target.value ? parseInt(e.target.value) : null 
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="例：2000"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  1日のタンパク質目標 (g)
                </label>
                <input
                  type="number"
                  min="30"
                  max="200"
                  value={formData.protein_target || ''}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    protein_target: e.target.value ? parseInt(e.target.value) : null 
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="例：60"
                />
              </div>
            </div>
          </div>
        )}

        {/* 保存ボタン */}
        <div className="mt-8 flex justify-end space-x-4">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            キャンセル
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            )}
            {saving ? '保存中...' : 'プロファイルを保存'}
          </button>
        </div>
      </div>
    </div>
  );
}