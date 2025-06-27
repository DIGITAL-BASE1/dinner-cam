import { useState, useRef, useEffect } from 'react';

export function ChatInput({ onSendMessage, disabled = false }) {
  const [message, setMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isComposing, setIsComposing] = useState(false); // 日本語入力中フラグ
  const [isMobile, setIsMobile] = useState(false);
  const fileInputRef = useRef(null);

  // 画面サイズ監視
  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkIsMobile();
    window.addEventListener('resize', checkIsMobile);
    
    return () => window.removeEventListener('resize', checkIsMobile);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if ((!message.trim() && !selectedFile) || disabled || isComposing) return;

    onSendMessage(message.trim() || '冷蔵庫の写真を送りました', selectedFile);
    
    // フォームをリセット
    setMessage('');
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* ファイルプレビュー */}
      {selectedFile && (
        <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg border">
          <div className="flex items-center space-x-3">
            <img 
              src={URL.createObjectURL(selectedFile)} 
              alt="Preview" 
              className="w-12 h-12 object-cover rounded border"
            />
            <div>
              <div className="text-sm font-medium text-gray-900">{selectedFile.name}</div>
              <div className="text-xs text-gray-500">
                {(selectedFile.size / 1024 / 1024).toFixed(1)}MB
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={removeFile}
            className="text-red-500 hover:text-red-700 p-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* メイン入力エリア */}
      <div className="flex items-end space-x-2">
        {/* テキスト入力 */}
        <div className="flex-1 relative">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder={isMobile ? "メッセージ..." : "メッセージを入力してください..."}
            disabled={disabled}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            rows="1"
            style={{
              minHeight: '44px',
              maxHeight: '120px'
            }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
          />
        </div>

        {/* 画像添付ボタン */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="画像を添付"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </button>

        {/* 送信ボタン */}
        <button
          type="submit"
          disabled={(!message.trim() && !selectedFile) || disabled}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {disabled ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          ) : (
            '送信'
          )}
        </button>
      </div>

      {/* 隠しファイル入力 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* ヒントテキスト - レスポンシブ対応 */}
      <div className="text-xs text-gray-500 flex flex-col md:flex-row md:items-center md:justify-between gap-2 md:gap-0">
        <span className="flex items-center gap-1">
          <span>💡</span>
          <span className="hidden md:inline">食材を教えてください、または冷蔵庫の写真を送ってください</span>
          <span className="md:hidden">食材を教えるか写真を送ってください</span>
        </span>
        <span className="text-right md:text-left">
          <span className="hidden md:inline">Enter: 送信 | Shift+Enter: 改行</span>
          <span className="md:hidden">Enter: 送信</span>
        </span>
      </div>
    </form>
  );
}