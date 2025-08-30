import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createHashRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import DraftPage from './pages/DraftPage'
import BanPage from './pages/BanPage'
import AboutPage from './pages/AboutPage'

const router = createHashRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <DraftPage /> },
      { path: '/draft', element: <DraftPage /> },
      { path: '/ban', element: <BanPage /> },
      { path: '/about', element: <AboutPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
