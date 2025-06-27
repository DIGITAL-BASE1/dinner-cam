import { useState } from 'react';

export function UploadForm({ onSuccess }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('image', file);

      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('解析に失敗しました');
      const data = await res.json();

      if (typeof onSuccess === 'function') {
        onSuccess(file, data.ingredients);
      }
    } catch (err) {
      setError(err.message || '不明なエラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center space-y-4">
      <input
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="border p-2 rounded"
      />
      {previewUrl && (
        <img src={previewUrl} alt="プレビュー" className="w-64 h-auto rounded shadow" />
      )}
      {file && (
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          {loading ? '解析中...' : '食材を解析する'}
        </button>
      )}
      {error && <p className="text-red-500">{error}</p>}
    </div>
  );
}
