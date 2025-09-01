import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { withBase } from './lib/paths'
import './App.css'
import { useEffect } from 'react'
import { trackPageview } from './lib/analytics'

function App() {
  const location = useLocation()

  useEffect(() => {
    if (import.meta.env.PROD) {
      trackPageview(location.pathname + location.search + location.hash, document.title)
    }
  }, [location])

  return (
    <div className="app-root">
      <nav className="top-nav">
        <Link to="/draft" className="brand">
          <img className="brand-icon" src={withBase('content/images/brand/captain.png')} alt="" />
          <span>D2Draft</span>
        </Link>
        <div className="nav-links">
          <NavLink to="/draft" className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}>Draft</NavLink>
          <NavLink to="/ban" className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}>Ban</NavLink>
          <NavLink to="/about" className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}>About</NavLink>
        </div>
        <div />
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}

export default App
