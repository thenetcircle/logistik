import axios from 'axios';
import config from '@/config';

const api = axios.create({
  baseURL: `${config.base}/api/`.replace('//', '/'),
  headers: { 'Content-type': 'Application/json' },
});

api.interceptors.response.use((response) => {
  if (response.data.status_code === 200) {
    return response.data.data;
  }
  return Promise.reject(response.data.message);
}, () => Promise.reject('An error occurred when sending HTTP request.'));

export default api;
