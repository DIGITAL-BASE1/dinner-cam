import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { login, loading } = useAuth();

  const handleGoogleSuccess = (credentialResponse) => {
    console.log('Google Login Success:', credentialResponse);
    login(credentialResponse);
  };

  const handleGoogleError = () => {
    console.error('Google login failed');
    alert('Googleログインに失敗しました。ページを再読み込みして再度お試しください。');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
        {/* ヘッダー */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🍳</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">DinnerCam</h1>
          <p className="text-gray-600 text-lg">AI料理アシスタント</p>
        </div>

        {/* 機能紹介 */}
        <div className="mb-8 space-y-4">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">📸</span>
            <span className="text-gray-700">冷蔵庫の写真から食材認識</span>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🤖</span>
            <span className="text-gray-700">AIが最適なレシピを提案</span>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🥗</span>
            <span className="text-gray-700">詳細な栄養分析</span>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🖼️</span>
            <span className="text-gray-700">手順画像で調理サポート</span>
          </div>
        </div>

        {/* ログインボタン */}
        <div className="space-y-4">
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-4">
              Googleアカウントでログインして始める
            </p>
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                theme="outline"
                size="large"
                text="signin_with"
                locale="ja"
                useOneTap={false}
                auto_select={false}
                cancel_on_tap_outside={true}
                itp_support={true}
                ux_mode="popup"
                context="signin"
              />
            </div>
          </div>
          
          {/* 注意事項 */}
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-800">
              <span className="font-semibold">🔒 プライバシー保護</span><br />
              Googleアカウント情報は認証のみに使用され、
              料理レシピの生成と保存以外の目的では使用されません。
            </p>
          </div>

          {/* トラブルシューティング */}
          <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
            <p className="text-xs text-yellow-800">
              <span className="font-semibold">⚠️ ログインできない場合</span><br />
              • ポップアップブロッカーを無効にしてください<br />
              • Cookieを有効にしてください<br />
              • プライベートブラウジングモードを無効にしてください
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}