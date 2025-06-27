import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function UserMenu({ onShowProfileSettings }) {
  const { user, logout, getAuthHeaders } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [rateLimitStatus, setRateLimitStatus] = useState(null);

  // 利用状況を取得
  useEffect(() => {
    const fetchRateLimitStatus = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/rate-limits`, {
          headers: getAuthHeaders()
        });
        if (response.ok) {
          const status = await response.json();
          setRateLimitStatus(status);
        }
      } catch (error) {
        console.error('利用状況の取得に失敗:', error);
      }
    };

    if (user) {
      fetchRateLimitStatus();
      // 5分ごとに更新
      const interval = setInterval(fetchRateLimitStatus, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [user, getAuthHeaders]);

  const handleLogout = () => {
    if (confirm('ログアウトしますか？')) {
      logout();
    }
  };

  return (
    <div className="relative">
      {/* ユーザーアバター */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <img
          src={user.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=059669&color=fff`}
          alt={user.name}
          className="w-8 h-8 rounded-full border-2 border-gray-200"
        />
        <span className="hidden md:block text-sm font-medium text-gray-700">
          {user.name}
        </span>
        
        {/* 制限警告インジケーター */}
        {rateLimitStatus && rateLimitStatus.total_remaining <= 3 && (
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
        )}
        
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* ドロップダウンメニュー */}
      {isOpen && (
        <>
          {/* オーバーレイ */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* メニュー */}
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
            {/* ユーザー情報 */}
            <div className="px-4 py-3 border-b border-gray-100">
              <div className="flex items-center space-x-3">
                <img
                  src={user.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=059669&color=fff`}
                  alt={user.name}
                  className="w-10 h-10 rounded-full"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {user.name}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {user.email}
                  </p>
                </div>
              </div>
            </div>

            {/* 利用状況表示 */}
            {rateLimitStatus && (
              <div className="px-4 py-3 border-b border-gray-100">
                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center">
                  <span className="mr-2">📊</span>
                  今日の利用状況
                </h4>
                
                <div className="space-y-3">
                  {/* 総利用回数 */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-gray-600">総リクエスト数</span>
                      <span className="text-xs font-medium text-gray-800">
                        {rateLimitStatus.total_used}/{rateLimitStatus.limits.total}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          rateLimitStatus.total_remaining > 3 ? 'bg-green-500' :
                          rateLimitStatus.total_remaining > 0 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ 
                          width: `${(rateLimitStatus.total_used / rateLimitStatus.limits.total) * 100}%` 
                        }}
                      ></div>
                    </div>
                    <div className="mt-1 text-xs text-gray-600">
                      残り {rateLimitStatus.total_remaining} 回
                    </div>
                  </div>

                  {/* 画像生成利用回数 */}
                  <div className="bg-blue-50 rounded-lg p-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-blue-800">🖼️ 画像生成</span>
                      <span className="text-xs font-medium text-blue-800">
                        {rateLimitStatus.image_generation_used}/{rateLimitStatus.limits.image_generation}
                      </span>
                    </div>
                    <div className="w-full bg-blue-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          rateLimitStatus.image_generation_remaining > 0 ? 'bg-blue-500' : 'bg-red-500'
                        }`}
                        style={{ 
                          width: `${(rateLimitStatus.image_generation_used / rateLimitStatus.limits.image_generation) * 100}%` 
                        }}
                      ></div>
                    </div>
                    <div className="mt-1 text-xs text-blue-700">
                      残り {rateLimitStatus.image_generation_remaining} 回
                    </div>
                  </div>

                  {/* リセット時間 */}
                  <div className="text-xs text-gray-500 text-center">
                    ⏰ 明日の0時（JST）にリセット
                  </div>
                </div>
              </div>
            )}

            {/* メニュー項目 */}
            <div className="py-1">
              <button
                onClick={() => {
                  setIsOpen(false);
                  if (onShowProfileSettings) {
                    onShowProfileSettings();
                  }
                }}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                プロファイル設定
              </button>

              <button
                onClick={() => {
                  setIsOpen(false);
                  alert('ヘルプ機能は今後実装予定です');
                }}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                ヘルプ
              </button>

              <div className="border-t border-gray-100 my-1"></div>

              <button
                onClick={handleLogout}
                className="flex items-center w-full px-4 py-2 text-sm text-red-700 hover:bg-red-50 transition-colors"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                ログアウト
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}