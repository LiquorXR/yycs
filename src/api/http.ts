import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api'

const http = axios.create({
  baseURL,
  timeout: 10000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error)
  },
)

export default http
