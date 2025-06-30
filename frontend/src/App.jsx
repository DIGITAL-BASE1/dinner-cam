import { useState, useRef, useEffect } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { RecipeDisplay } from './components/RecipeDisplay';
import { IngredientCheck } from './components/IngredientCheck';
import { LoginPage } from './components/LoginPage';
import { UserMenu } from './components/UserMenu';
import { AdminPanel } from './components/AdminPanel';
import { ProfileSettings } from './components/ProfileSettings';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

function AppContent() {
  const { user, isAuthenticated, loading, getAuthHeaders } = useAuth();
  
  // LINEスタイル会話のための状態管理
  const [messages, setMessages] = useState([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [messagesSynced, setMessagesSynced] = useState(false);
  
  const [currentRecipe, setCurrentRecipe] = useState(null);
  const [currentNutrition, setCurrentNutrition] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState('');
  const [withImages, setWithImages] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [showProfileSettings, setShowProfileSettings] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [rateLimitStatus, setRateLimitStatus] = useState(null);
  
  const [showIngredientCheck, setShowIngredientCheck] = useState(false);
  const [detectedIngredients, setDetectedIngredients] = useState([]);
  const [pendingImageMessageId, setPendingImageMessageId] = useState(null);
  
  // ストリーミング停止用
  const [isStreaming, setIsStreaming] = useState(false);
  const streamAbortControllerRef = useRef(null);
  const currentRecipeMessageIdRef = useRef(null);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const stopStreaming = () => {
    if (streamAbortControllerRef.current) {
      streamAbortControllerRef.current.abort();
      streamAbortControllerRef.current = null;
    }
    
    // 現在のレシピメッセージがあれば停止メッセージに更新
    if (currentRecipeMessageIdRef.current) {
      updateMessage(currentRecipeMessageIdRef.current, {
        content: 'レシピ生成を停止しました。何か他にお手伝いできることはありますか？'
      });
      currentRecipeMessageIdRef.current = null;
    } else {
      addMessage('bot', 'レシピ生成を停止しました。何か他にお手伝いできることはありますか？');
    }
    
    setIsStreaming(false);
    setStreamingStatus('');
    setIsTyping(false);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, showIngredientCheck]);

  // LINEスタイル会話復元：ログイン後にメッセージを読み込み
  const loadUserMessages = async () => {
    if (!isAuthenticated || messagesSynced) return;
    
    setIsLoadingMessages(true);
    try {
      console.log('[INFO] ユーザーメッセージを読み込み中...');
      
      const response = await fetch(`${API_BASE_URL}/conversations/messages`, {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log(`[INFO] ${data.message_count}件のメッセージを復元しました (${data.backend})`);
        
        if (data.messages && data.messages.length > 0) {
          // メッセージを復元（IDが文字列でない場合は新しいユニークIDを生成）
          const seenIds = new Set();
          const restoredMessages = data.messages.map((msg, index) => {
            let uniqueId = msg.id || `restored-${Date.now()}-${index}-${Math.random().toString(36).slice(2, 11)}`;
            
            // IDの重複をチェック、重複していたら新しいIDを生成
            while (seenIds.has(uniqueId)) {
              uniqueId = `${uniqueId}-${Math.random().toString(36).slice(2, 5)}`;
            }
            seenIds.add(uniqueId);
            
            return {
              ...msg,
              id: uniqueId,
              timestamp: new Date(msg.timestamp)
            };
          });
          
          setMessages(restoredMessages);
          console.log(`[INFO] 会話復元完了！${restoredMessages.length}件のメッセージを復元`);
        } else {
          // 新規ユーザーの場合は初回メッセージを表示
          console.log('[INFO] 新規ユーザー - 初回メッセージを表示');
          const welcomeMessage = {
            id: `welcome-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
            type: 'bot',
            content: `こんにちは、${user?.name || 'ゲスト'}さん！🍳 DinnerCamです。今日の食事について何でもお聞かせください！\n\n📸 冷蔵庫の写真を撮って食材を確認することも、\n📝 手持ちの食材を教えてもらうことも、\n💬 料理の相談をすることもできますよ！`,
            timestamp: new Date()
          };
          
          setMessages([welcomeMessage]);
          
          // 初回メッセージをサーバーに保存
          try {
            await fetch(`${API_BASE_URL}/conversations/messages`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
              },
              body: JSON.stringify({
                message: welcomeMessage
              })
            });
          } catch (saveError) {
            console.warn('[WARN] 初回メッセージの保存に失敗:', saveError);
          }
        }
        
        setMessagesSynced(true);
      } else {
        console.error('[ERROR] メッセージ読み込み失敗:', response.status);
      }
    } catch (error) {
      console.error('[ERROR] メッセージ読み込みエラー:', error);
    } finally {
      setIsLoadingMessages(false);
    }
  };

  // LINEスタイル会話保存：新しいメッセージをサーバーに保存
  const saveMessageToServer = async (message) => {
    try {
      await fetch(`${API_BASE_URL}/conversations/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          message: {
            ...message,
            timestamp: message.timestamp.toISOString()
          }
        })
      });
    } catch (error) {
      console.warn('[WARN] メッセージ保存失敗:', error);
    }
  };

  // 認証完了後にメッセージを読み込み
  useEffect(() => {
    if (isAuthenticated && !messagesSynced && !isLoadingMessages) {
      loadUserMessages();
    }
  }, [isAuthenticated, messagesSynced, isLoadingMessages]);

  const checkAdminStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/check`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setIsAdmin(data.is_admin);
      }
    } catch (error) {
      console.error('管理者権限チェック失敗:', error);
      setIsAdmin(false);
    }
  };

  const fetchRateLimitStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/rate-limits`, {
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

  useEffect(() => {
    if (isAuthenticated) {
      checkAdminStatus();
      fetchRateLimitStatus();
    }
  }, [isAuthenticated]);

  if (loading || isLoadingMessages) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">
            {loading ? '読み込み中...' : 'メッセージを復元中...'}
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (showAdminPanel) {
    return (
      <div className="h-screen bg-gray-50 overflow-auto">
        <div className="bg-white shadow-sm border-b px-4 py-3 sticky top-0 z-10">
          <div className="flex items-center justify-between max-w-6xl mx-auto">
            <button
              onClick={() => setShowAdminPanel(false)}
              className="flex items-center gap-2 text-blue-600 hover:text-blue-800 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              チャットに戻る
            </button>
            <h1 className="text-xl font-bold text-gray-800">管理者パネル</h1>
            <UserMenu onShowProfileSettings={() => setShowProfileSettings(true)} />
          </div>
        </div>
        <AdminPanel />
      </div>
    );
  }

  if (showProfileSettings) {
    return (
      <div className="h-screen bg-gray-50 overflow-auto">
        <ProfileSettings onClose={() => setShowProfileSettings(false)} />
      </div>
    );
  }


  const addMessage = (type, content, extra = {}) => {
    // より確実なユニークID生成
    const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
    const newMessage = {
      id: uniqueId,
      type,
      content,
      timestamp: new Date(),
      ...extra
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    // LINEスタイル：自動保存
    if (isAuthenticated) {
      saveMessageToServer(newMessage);
    }
    
    return newMessage.id;
  };

  const updateMessage = (messageId, updates) => {
    setMessages(prev => {
      const updatedMessages = prev.map(msg => 
        msg.id === messageId ? { ...msg, ...updates } : msg
      );
      
      // 更新されたメッセージをサーバーに保存
      if (isAuthenticated) {
        const updatedMessage = updatedMessages.find(m => m.id === messageId);
        if (updatedMessage) {
          saveMessageToServer(updatedMessage);
        }
      }
      
      return updatedMessages;
    });
  };

  const handleRateLimitError = (error) => {
    if (error.status === 429) {
      const detail = error.detail;
      addMessage('bot', detail.message);
      fetchRateLimitStatus();
      return true;
    }
    return false;
  };

  const handleUserMessage = async (message, image = null) => {
    console.log('[DEBUG] handleUserMessage 開始:', { message, hasImage: !!image });
    
    if (image) {
      addMessage('user', message, { image: URL.createObjectURL(image) });
    } else {
      addMessage('user', message);
    }

    setIsTyping(true);

    try {
      if (image) {
        console.log('[DEBUG] 画像処理ルート');
        await handleImageAnalysis(image);
      } else {
        console.log('[DEBUG] テキスト処理ルート');
        await handleTextMessage(message);
      }
    } catch (error) {
      console.error('[ERROR] handleUserMessage:', error);
      
      if (!handleRateLimitError(error)) {
        addMessage('bot', '申し訳ございません。エラーが発生しました。もう一度お試しください。🙏');
      }
    } finally {
      setIsTyping(false);
      fetchRateLimitStatus();
    }
  };

  const handleImageAnalysis = async (image) => {
    const botMessageId = addMessage('bot', '冷蔵庫の写真を確認しています...📸');

    try {
      const formData = new FormData();
      formData.append('image', image);

      const analyzeResponse = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders()
        },
        body: formData,
      });

      if (analyzeResponse.status === 429) {
        const errorData = await analyzeResponse.json();
        updateMessage(botMessageId, {
          content: errorData.detail.message
        });
        fetchRateLimitStatus();
        return;
      }

      if (!analyzeResponse.ok) throw new Error('画像解析に失敗しました');
      const analyzeData = await analyzeResponse.json();

      updateMessage(botMessageId, {
        content: `冷蔵庫を確認しました！🔍\n\n以下の食材が見つかりました。使用する食材を選択してください：`
      });

      setDetectedIngredients(analyzeData.ingredients);
      setShowIngredientCheck(true);
      setPendingImageMessageId(botMessageId);


    } catch (error) {
      updateMessage(botMessageId, {
        content: '画像の解析に失敗しました。もう一度お試しください。😅'
      });
    }
  };

  const handleIngredientConfirm = async (selectedIngredients) => {
    console.log('[DEBUG] 選択された食材:', selectedIngredients);
    
    setShowIngredientCheck(false);
    
    if (pendingImageMessageId) {
      updateMessage(pendingImageMessageId, {
        content: `選択された食材でレシピを作成します！🍳\n\n使用食材：\n${selectedIngredients.map(ing => `• ${ing}`).join('\n')}`
      });
    }
    
    // 選択された食材でレシピ生成要求をv2エンドポイントに送信
    const ingredientsMessage = `これらの食材でレシピを作ってください: ${selectedIngredients.join(', ')}`;
    await processChatWithV2(ingredientsMessage);
    
    setDetectedIngredients([]);
    setPendingImageMessageId(null);
  };

  const handleIngredientReset = () => {
    console.log('[DEBUG] 食材選択をリセット');
    
    setShowIngredientCheck(false);
    
    if (pendingImageMessageId) {
      updateMessage(pendingImageMessageId, {
        content: '食材の選択をキャンセルしました。もう一度写真を撮るか、手動で食材を教えてください。😊'
      });
    }
    
    setDetectedIngredients([]);
    setPendingImageMessageId(null);
  };

  const handleTextMessage = async (message) => {
    console.log('[DEBUG] handleTextMessage開始 (ChatAgent v2):', message);
    
    // 新しいChatAgent v2エンドポイントを使用
    await processChatWithV2(message);
  };




  // 会話クリア機能（LINEスタイル用）
  const clearConversation = async () => {
    if (confirm('会話履歴をクリアしますか？この操作は取り消せません。')) {
      try {
        const response = await fetch(`${API_BASE_URL}/conversations/messages`, {
          method: 'DELETE',
          headers: getAuthHeaders()
        });
        
        if (response.ok) {
          setMessages([]);
          setMessagesSynced(false);
          
          // 新しい初回メッセージを表示
          setTimeout(() => {
            loadUserMessages();
          }, 100);
          
          console.log('[INFO] 会話履歴をクリアしました');
        }
      } catch (error) {
        console.error('[ERROR] 会話クリアエラー:', error);
        alert('会話のクリアに失敗しました');
      }
    }
  };

  // ===== ChatAgent v2 統合チャット処理 =====
  
  const processChatWithV2 = async (message) => {
    console.log('[DEBUG] ChatAgent v2 processing message:', message);
    
    const messageId = addMessage('bot', '処理中...🔄');
    
    // AbortControllerを作成
    const abortController = new AbortController();
    streamAbortControllerRef.current = abortController;
    setIsStreaming(true);
    setStreamingStatus('処理中...');

    try {
      const requestBody = {
        message: message,
        has_image: false,
        with_images: withImages,
        with_nutrition: true,
      };
      
      console.log('[DEBUG] /chat/v2 リクエストボディ:', requestBody);

      const response = await fetch(`${API_BASE_URL}/chat/v2`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(requestBody),
        signal: abortController.signal,
      });

      if (response.status === 429) {
        const errorData = await response.json();
        updateMessage(messageId, {
          content: errorData.detail.message
        });
        fetchRateLimitStatus();
        return;
      }

      if (!response.ok) throw new Error('チャット処理に失敗しました');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonString = line.slice(6).trim();
            if (jsonString) {
              try {
                const data = JSON.parse(jsonString);
                await handleChatV2StreamEvent(data, messageId);
              } catch (e) {
                console.error('JSON parse error in /chat/v2:', e);
              }
            }
          }
        }
      }

      reader.releaseLock();
      fetchRateLimitStatus();

    } catch (error) {
      console.error('[ERROR] testChatV2Endpoint:', error);
      
      if (error.name === 'AbortError') {
        console.log('[INFO] ストリーミングが停止されました');
        return;
      }
      
      updateMessage(messageId, {
        content: 'チャット処理に失敗しました。もう一度お試しください。😅'
      });
    } finally {
      setIsStreaming(false);
      setStreamingStatus('');
      streamAbortControllerRef.current = null;
    }
  };

  // ChatAgent v2 ストリーミングイベントのハンドラー
  const handleChatV2StreamEvent = async (data, messageId) => {
    console.log('[DEBUG] handleChatV2StreamEvent:', data.type, data);
    
    switch (data.type) {
      case 'status':
        setStreamingStatus(data.content);
        break;
        
      case 'intent':
        console.log('[DEBUG] ChatAgent v2 意図解析:', data.content);
        updateMessage(messageId, {
          content: `意図解析結果: ${data.content.intent} (信頼度: ${Math.round(data.content.confidence * 100)}%)`
        });
        break;
        
      case 'chat_response':
        updateMessage(messageId, {
          content: data.content
        });
        break;
        
      case 'recipe':
        setCurrentRecipe(data.content);
        updateMessage(messageId, {
          content: 'レシピができました！🎉',
          recipe: data.content
        });
        break;
        
      case 'nutrition':
        setCurrentNutrition(data.content);
        addMessage('bot', '栄養分析が完了しました！🥗', { nutritionData: data.content });
        break;
        
      case 'generating_image':
        setStreamingStatus(`手順${data.content.step_index + 1}の画像を生成中...🖼️`);
        break;
        
      case 'image':
        addMessage('bot', `手順${data.content.step_index + 1}の画像ができました！`, { 
          stepImage: {
            step_index: data.content.step_index,
            step_text: data.content.step_text,
            image_url: data.content.image_url
          }
        });
        break;
        
      case 'image_error':
        addMessage('bot', `⚠️ 手順${data.content.step_index + 1}の画像生成に失敗しました: ${data.content.step_text}`);
        break;
        
      case 'suggestion':
        if (data.content.type === 'recipe_generation') {
          addMessage('bot', `💡 ${data.content.message}`, { 
            suggestion: data.content,
            extracted_data: data.content.extracted_data 
          });
        }
        break;
        
      case 'complete':
        setStreamingStatus('');
        console.log('[DEBUG] 処理完了:', data.content);
        break;
        
      case 'error':
        updateMessage(messageId, {
          content: `❌ エラー: ${data.content.message}`
        });
        console.error('[ERROR] チャット処理:', data.content);
        break;
        
      default:
        console.log('[DEBUG] Unknown ChatAgent v2 event type:', data.type, data);
    }
  };

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      <div className="bg-white shadow-sm border-b px-4 py-3 flex-shrink-0 sticky top-0 z-10">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            🍳 DinnerCam
          </h1>
          
          <div className="flex items-center gap-2 md:gap-4">
            
            {/* 会話クリアボタン */}
            {messagesSynced && messages.length > 1 && (
              <button
                onClick={clearConversation}
                className="px-3 py-1.5 bg-red-500 text-white rounded-full text-xs md:text-sm font-medium hover:bg-red-600 transition-colors flex items-center gap-1"
                title="会話履歴をクリア"
              >
                <span>🗑️</span>
                <span className="hidden md:inline">クリア</span>
              </button>
            )}
            

            {isAdmin && (
              <button
                onClick={() => setShowAdminPanel(true)}
                className="px-3 py-1.5 bg-purple-500 text-white rounded-full text-xs md:text-sm font-medium hover:bg-purple-600 transition-colors flex items-center gap-1"
              >
                <span>⚙️</span>
                <span className="hidden md:inline">管理者</span>
              </button>
            )}
            
            <button
              onClick={() => setWithImages(!withImages)}
              disabled={rateLimitStatus?.image_generation_remaining <= 0}
              className={`px-3 py-1.5 rounded-full text-xs md:text-sm font-medium transition-all duration-200 flex items-center gap-1 md:gap-2 transform active:scale-95 ${
                withImages
                  ? 'bg-blue-500 text-white shadow-md hover:bg-blue-600 hover:shadow-lg'
                  : rateLimitStatus?.image_generation_remaining <= 0
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 hover:border-gray-400'
              }`}
              title={
                rateLimitStatus?.image_generation_remaining <= 0 
                  ? '画像生成の制限に達しました' 
                  : withImages ? '手順画像生成をOFFにする' : '手順画像生成をONにする'
              }
            >
              <span className="text-sm">🖼️</span>
              <span className="hidden md:inline">
                {rateLimitStatus?.image_generation_remaining <= 0 ? '制限到達' : '手順画像'}
              </span>
              <span className="md:hidden">
                {rateLimitStatus?.image_generation_remaining <= 0 ? '✗' : ''}
              </span>
            </button>
            

            <UserMenu onShowProfileSettings={() => setShowProfileSettings(true)} />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex max-w-4xl mx-auto w-full">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-8">
          {messages.map((message, index) => (
            <ChatMessage key={`${message.id}-${index}`} message={message} />
          ))}
          
          {showIngredientCheck && (
            <div className="flex justify-start mb-4">
              <div className="bg-white rounded-lg px-4 py-2 shadow-sm border border-gray-200 max-w-lg">
                <IngredientCheck
                  ingredients={detectedIngredients}
                  onConfirm={handleIngredientConfirm}
                  onReset={handleIngredientReset}
                />
              </div>
            </div>
          )}
          
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white rounded-lg px-4 py-2 shadow-sm max-w-xs">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="bg-white border-t px-4 py-3 flex-shrink-0 sticky bottom-0 z-10">
        {streamingStatus && (
          <div className="max-w-4xl mx-auto mb-2">
            <div className="text-center">
              <div className="inline-flex items-center gap-3 px-3 py-2 bg-green-50 text-green-700 rounded-full text-sm animate-pulse">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce"></div>
                  <span>{streamingStatus}</span>
                </div>
                {isStreaming && (
                  <button
                    onClick={stopStreaming}
                    className="px-2 py-1 bg-red-500 text-white rounded-full text-xs hover:bg-red-600 transition-colors flex items-center gap-1"
                    title="レシピ生成を停止"
                  >
                    <span>⏹️</span>
                    <span>停止</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
        <div className="max-w-4xl mx-auto">
          <ChatInput 
            onSendMessage={handleUserMessage}
            disabled={isTyping || showIngredientCheck}
          />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  if (!GOOGLE_CLIENT_ID) {
    return (
      <div className="h-screen bg-red-50 flex items-center justify-center">
        <div className="text-center p-8 bg-white rounded-lg shadow-lg max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-xl font-bold text-red-600 mb-2">設定エラー</h1>
          <p className="text-red-700">
            Google Client IDが設定されていません。<br />
            <code className="bg-gray-100 px-2 py-1 rounded text-sm">
              VITE_GOOGLE_CLIENT_ID
            </code><br />
            環境変数を設定してください。
          </p>
        </div>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider 
      clientId={GOOGLE_CLIENT_ID}
      onScriptLoadError={() => console.error('Google Script Load Error')}
      onScriptLoadSuccess={() => console.log('Google Script Loaded Successfully')}
    >
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}