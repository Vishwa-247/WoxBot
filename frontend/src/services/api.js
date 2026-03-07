import axios from 'axios';

const API_KEY = import.meta.env.VITE_API_KEY ?? 'woxbot-dev-key';

const client = axios.create({
  headers: { 'X-API-Key': API_KEY },
});

export async function getSources() {
  const { data } = await client.get('/api/sources');
  return data;
}

export async function deleteSource(filename) {
  const { data } = await client.delete(`/api/sources/${encodeURIComponent(filename)}`);
  return data;
}

export async function uploadPDF(file, onProgress) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post('/api/ingest', form, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export { API_KEY };
