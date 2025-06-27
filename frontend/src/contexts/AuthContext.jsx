import { createContext, useContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  // 初期化時にローカルストレージからトークンを確認
  useEffect(() => {
    const storedToken = localStorage.getItem('dinnercam_token');
    if (storedToken) {
      try {
        const decoded = jwtDecode(storedToken);
        
        // トークンの有効期限チェック
        if (decoded.exp * 1000 > Date.now()) {
          setToken(storedToken);
          setUser({
            id: decoded.sub,
            email: decoded.email,
            name: decoded.name,
            picture: decoded.picture
          });
        } else {
          // 期限切れの場合はクリア
          localStorage.removeItem('dinnercam_token');
        }
      } catch (error) {
        console.error('Invalid token:', error);
        localStorage.removeItem('dinnercam_token');
      }
    }
    setLoading(false);
  }, []);

  // Google認証成功時の処理
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      setLoading(true);
      
      // バックエンドでGoogle認証を検証
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          credential: credentialResponse.credential
        }),
      });

      if (!response.ok) {
        throw new Error('Authentication failed');
      }

      const data = await response.json();
      
      // JWTトークンを保存
      localStorage.setItem('dinnercam_token', data.token);
      setToken(data.token);
      setUser(data.user);
      
      console.log('Authentication successful:', data.user);
    } catch (error) {
      console.error('Authentication error:', error);
      alert('ログインに失敗しました。もう一度お試しください。');
    } finally {
      setLoading(false);
    }
  };

  // ログアウト
  const logout = () => {
    localStorage.removeItem('dinnercam_token');
    setToken(null);
    setUser(null);
  };

  // APIリクエスト用のヘッダー取得
  const getAuthHeaders = () => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const value = {
    user,
    token,
    loading,
    login: handleGoogleSuccess,
    logout,
    getAuthHeaders,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};