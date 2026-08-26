import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

const Wrapper = ({ token, handleLogout, children, userId }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const logout = () => {
    handleLogout()
    navigate('/')
  }

  const isActive = (path) => location.pathname === path

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navbar */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border)',
        height: 'var(--nav-h)',
        display: 'flex', alignItems: 'center',
        padding: '0 32px',
      }}>
        <div style={{ maxWidth: 1200, width: '100%', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Logo */}
          <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 38, height: 38,
              background: 'linear-gradient(135deg, var(--primary), var(--primary-dark))',
              borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20,
              boxShadow: '0 4px 12px var(--primary-glow)'
            }}>🚌</div>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 20, color: 'var(--text)' }}>
              BusGo
            </span>
          </Link>

          {/* Nav links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {[
              { to: '/', label: 'Search' },
              ...(token ? [{ to: '/my-bookings', label: 'My Bookings' }] : []),
            ].map(({ to, label }) => (
              <Link key={to} to={to} style={{
                textDecoration: 'none',
                padding: '8px 16px',
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                color: isActive(to) ? 'var(--primary)' : 'var(--text-muted)',
                background: isActive(to) ? 'var(--primary-light)' : 'transparent',
                transition: 'all 0.2s',
              }}>{label}</Link>
            ))}
          </div>

          {/* Auth */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {token ? (
              <>
                <div style={{
                  width: 36, height: 36, borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--primary-light), var(--primary-glow))',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, border: '2px solid var(--primary)',
                }}>👤</div>
                <button className="btn btn-ghost" style={{ padding: '8px 18px', fontSize: 14 }} onClick={logout}>
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn btn-ghost" style={{ padding: '8px 18px', fontSize: 14 }}>
                  Login
                </Link>
                <Link to="/register" className="btn btn-primary" style={{ padding: '8px 18px', fontSize: 14 }}>
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, maxWidth: 1200, width: '100%', margin: '0 auto', padding: '0 32px', boxSizing: 'border-box' }}>
        <div className="page-enter">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        padding: '24px 32px',
        marginTop: 64,
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: 13,
      }}>
        <p>© 2025 BusGo — Safe, comfortable travel across every route.</p>
      </footer>
    </div>
  )
}

export default Wrapper
