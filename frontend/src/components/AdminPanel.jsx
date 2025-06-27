import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function AdminPanel() {
  const { getAuthHeaders } = useAuth();
  const [stats, setStats] = useState(null);
  const [resetInfo, setResetInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const fetchStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/stats`, {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setStats(data);
        setResetInfo(data.reset_info);
      } else {
        setMessage('統計情報の取得に失敗しました');
      }
    } catch (error) {
      console.error('Stats fetch error:', error);
      setMessage('エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  const resetUserLimits = async (userId) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/reset-user/${userId}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessage(data.message);
        fetchStats();
      } else {
        setMessage('リセットに失敗しました');
      }
    } catch (error) {
      console.error('Reset error:', error);
      setMessage('エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  const resetAllLimits = async () => {
    if (!confirm('全ユーザーの制限をリセットしますか？この操作は取り消せません。')) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/reset-all`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessage(data.message);
        fetchStats();
      } else {
        setMessage('全体リセットに失敗しました');
      }
    } catch (error) {
      console.error('Reset all error:', error);
      setMessage('エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) {
    return (
      <div className="p-6 bg-white rounded-lg shadow-lg">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
          <span className="mr-3">⚙️</span>
          DinnerCam 管理者パネル
        </h1>

        {message && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-blue-800">{message}</p>
            <button 
              onClick={() => setMessage('')}
              className="text-blue-600 hover:text-blue-800 text-sm mt-1"
            >
              ✕ 閉じる
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <div className="text-2xl font-bold text-blue-600">{stats.total_users}</div>
            <div className="text-sm text-blue-800">今日のアクティブユーザー</div>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <div className="text-2xl font-bold text-green-600">{stats.total_requests_today}</div>
            <div className="text-sm text-green-800">今日の総リクエスト</div>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <div className="text-2xl font-bold text-purple-600">{stats.image_requests_today}</div>
            <div className="text-sm text-purple-800">今日の画像生成</div>
          </div>
          
          <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
            <div className="text-2xl font-bold text-orange-600">
              {stats.total_requests_today > 0 ? 
                Math.round((stats.image_requests_today / stats.total_requests_today) * 100) : 0}%
            </div>
            <div className="text-sm text-orange-800">画像生成率</div>
          </div>
        </div>

        {resetInfo && (
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6">
            <h3 className="font-semibold text-gray-800 mb-2 flex items-center">
              <span className="mr-2">⏰</span>
              リセット情報
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-600">現在時刻（JST）:</span>
                <div className="font-mono text-gray-800">
                  {new Date(resetInfo.current_jst).toLocaleString('ja-JP')}
                </div>
              </div>
              <div>
                <span className="text-gray-600">次回リセット:</span>
                <div className="font-mono text-gray-800">
                  {new Date(resetInfo.next_reset_jst).toLocaleString('ja-JP')}
                </div>
              </div>
              <div>
                <span className="text-gray-600">リセットまで:</span>
                <div className="font-semibold text-orange-600">
                  {resetInfo.formatted_time_until}
                </div>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              Backend: {resetInfo.backend || stats.backend}
            </div>
          </div>
        )}

        <div className="bg-red-50 p-4 rounded-lg border border-red-200 mb-6">
          <h3 className="font-semibold text-red-800 mb-4 flex items-center">
            <span className="mr-2">🚨</span>
            管理アクション
          </h3>
          <div className="flex gap-4 flex-wrap">
            <button
              onClick={resetAllLimits}
              disabled={loading}
              className="bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white px-4 py-2 rounded-lg transition-colors flex items-center"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              ) : (
                <span className="mr-2">🔄</span>
              )}
              全ユーザーリセット
            </button>
            
            <button
              onClick={fetchStats}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-4 py-2 rounded-lg transition-colors flex items-center"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              ) : (
                <span className="mr-2">📊</span>
              )}
              統計更新
            </button>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <h3 className="font-semibold text-gray-800 flex items-center">
              <span className="mr-2">👥</span>
              今日のユーザー詳細
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    ユーザーID
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    総リクエスト
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    画像生成
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    アクション
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {stats.users.map((user, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm font-mono text-gray-600">
                      {user.user_id.substring(0, 12)}...
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                        user.total_requests >= 8 ? 'bg-red-100 text-red-800' :
                        user.total_requests >= 5 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {user.total_requests}/10
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                        user.image_requests >= 3 ? 'bg-red-100 text-red-800' :
                        user.image_requests >= 2 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {user.image_requests}/3
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <button
                        onClick={() => resetUserLimits(user.user_id)}
                        disabled={loading}
                        className="text-red-600 hover:text-red-800 disabled:text-red-300 text-xs"
                      >
                        リセット
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {stats.users.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              今日はまだユーザーアクティビティがありません
            </div>
          )}
        </div>
      </div>
    </div>
  );
}