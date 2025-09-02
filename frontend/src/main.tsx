import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import DraftPage from './pages/DraftPage'
import BanPage from './pages/BanPage'
import AboutPage from './pages/AboutPage'
import { initAnalytics } from './lib/analytics'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/draft" replace /> },
      { path: '/draft', element: <DraftPage /> },
      { path: '/ban', element: <BanPage /> },
      { path: '/about', element: <AboutPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)

// Initialize GA only in production builds when an ID is provided
if (import.meta.env.PROD) {
  const measurementId = import.meta.env.VITE_GA_MEASUREMENT_ID as string | undefined
  initAnalytics(measurementId)
}
