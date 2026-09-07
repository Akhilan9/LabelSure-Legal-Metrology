import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  timeout: 8000,
})

let accessToken = null
let onUnauthorized = () => {}
export function setAccessToken(token) { accessToken = token }
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
  return () => { onUnauthorized = () => {} }
}
api.interceptors.request.use(config => {
  if (accessToken && config.url !== '/auth/login') config.headers.Authorization = `Bearer ${accessToken}`
  return config
})
api.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401 && error.config?.url !== '/auth/login'
      && accessToken && error.config?.headers?.Authorization === `Bearer ${accessToken}`) onUnauthorized()
  return Promise.reject(error)
})
