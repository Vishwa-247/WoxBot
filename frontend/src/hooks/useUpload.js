import { useState, useCallback } from 'react';
import { uploadPDF } from '../services/api';

/**
 * useUpload — manages PDF upload state and progress.
 * onSuccess(result) is called after a successful upload.
 */
export function useUpload(onSuccess) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const upload = useCallback(
    async (file) => {
      if (!file || file.type !== 'application/pdf') {
        setError('Please select a valid PDF file.');
        return;
      }

      setUploading(true);
      setProgress(0);
      setResult(null);
      setError(null);

      try {
        const data = await uploadPDF(file, setProgress);
        setResult(data);
        if (onSuccess) onSuccess(data);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Upload failed.');
      } finally {
        setUploading(false);
        setProgress(0);
      }
    },
    [onSuccess]
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { uploading, progress, result, error, upload, reset };
}
