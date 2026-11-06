import React, { useState, useEffect } from 'react'
// import axios from 'axios'
import api from '../api.js' // Import the custom axios instance
import { Link } from 'react-router-dom'

const UserBookings = ({ token, userId }) => {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cancellingId, setCancellingId] = useState(null)
  const [notice, setNotice] = useState(null) // { type: 'success' | 'error', text }

  useEffect(() => {
    const fetchBookings = async () => {
      if (!token || !userId) {
        setLoading(false)
        return
      }
      try {
        const response = await api.get(`/api/user/${userId}/bookings/`, {
          headers: { Authorization: `Token ${token}` }
        })
        setBookings(response.data)
      } catch (error) {
        setError(error.response?.data?.error || 'Failed to load bookings')
      } finally {
        setLoading(false)
      }
    }
    fetchBookings()
  }, [userId, token])

  const handleCancel = async (booking) => {
    const ok = window.confirm(
      `Cancel your ticket for ${booking.bus_name}, seat ${booking.seat_number}, on ${formatTravelDate(booking.travel_date)}?\n\nThe seat will be released for other passengers.`
    )
    if (!ok) return
    setCancellingId(booking.id)
    setNotice(null)
    try {
      const response = await api.post(`/api/booking/${booking.id}/cancel/`, {}, {
        headers: { Authorization: `Token ${token}` }
      })
      setBookings(prev => prev.map(b => (b.id === booking.id ? response.data : b)))
      setNotice({ type: 'success', text: `Seat ${booking.seat_number} on ${booking.bus_name} was cancelled.` })
    } catch (err) {
      setNotice({ type: 'error', text: err.response?.data?.error || 'Could not cancel this booking. Please try again.' })
    } finally {
      setCancellingId(null)
    }
  }

  // 'YYYY-MM-DD' -> 'Wed, 4 Nov 2026' (built from parts so the time zone can't shift the day)
  const formatTravelDate = (iso) => {
    if (!iso) return ''
    const [y, m, d] = iso.split('-').map(Number)
    return new Date(y, m - 1, d).toLocaleDateString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
    })
  }

  const formatDate = (str) => {
    if (!str) return ''
    const d = new Date(str)
    return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  if (!token) return (
    <div style={{ paddingTop: 80, textAlign: 'center' }}>
      <div style={{ fontSize: 52, marginBottom: 16 }}>🔐</div>
      <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: 8 }}>Login Required</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>Please login to view your booking history</p>
      <Link to="/login" className="btn btn-primary" style={{ textDecoration: 'none' }}>Go to Login</Link>
    </div>
  )

  return (
    <div style={{ paddingTop: 40, paddingBottom: 60 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, marginBottom: 6 }}>My Bookings</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>Your travel history and upcoming trips</p>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>📋</div>
          <p style={{ color: 'var(--text-muted)' }}>Loading your bookings…</p>
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>⚠️</div>
          <p style={{ color: '#ef4444', fontWeight: 600 }}>{error}</p>
        </div>
      ) : bookings.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <div style={{ fontSize: 52, marginBottom: 16 }}>🎫</div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: 8, fontSize: 22 }}>No bookings yet</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 28 }}>Start your journey by finding a bus route</p>
          <Link to="/" className="btn btn-primary" style={{ textDecoration: 'none', display: 'inline-flex' }}>Browse Buses</Link>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
            {[
              { icon: '🎫', label: 'Total Bookings', value: bookings.length },
              { icon: '✅', label: 'Confirmed', value: bookings.filter(b => b.status === 'confirmed').length },
              { icon: '🚌', label: 'Buses Taken', value: new Set(bookings.filter(b => b.status === 'confirmed').map(b => b.bus)).size },
            ].map(({ icon, label, value }) => (
              <div key={label} className="card" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: 'var(--primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 22, flexShrink: 0,
                }}>{icon}</div>
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 24, color: 'var(--text)' }}>{value}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
                </div>
              </div>
            ))}
          </div>

          {notice && (
            <div style={{
              marginBottom: 16, padding: '12px 18px', borderRadius: 10, fontSize: 14, fontWeight: 600,
              background: notice.type === 'success' ? 'var(--primary-light)' : '#fdecea',
              color: notice.type === 'success' ? 'var(--primary-dark)' : '#b42318',
            }}>
              {notice.text}
            </div>
          )}

          {/* Booking list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {bookings.map((booking, i) => (
              <div key={booking.id || i} className="card" style={{ padding: '22px 28px', display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', opacity: booking.status === 'cancelled' ? 0.6 : 1 }}>
                {/* Status dot */}
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: 'var(--primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 22, flexShrink: 0,
                }}>🎫</div>

                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4, color: 'var(--text)' }}>
                    {booking.bus_name} — Seat {booking.seat_number}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    {booking.origin} → {booking.destination} · {booking.start_time?.slice(0, 5)} - {booking.reach_time?.slice(0, 5)}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600 }}>
                    📅 Travel date: {formatTravelDate(booking.travel_date)}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Booked: {formatDate(booking.booking_time)}
                  </div>
                  {booking.status === 'cancelled' && booking.cancelled_at && (
                    <div style={{ fontSize: 13, color: '#b42318' }}>
                      Cancelled: {formatDate(booking.cancelled_at)}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
                  <div style={{
                    background: booking.status === 'cancelled' ? '#fdecea' : 'var(--primary-light)',
                    color: booking.status === 'cancelled' ? '#b42318' : 'var(--primary-dark)',
                    borderRadius: 20, padding: '6px 14px',
                    fontSize: 12, fontWeight: 700,
                  }}>
                    {booking.status === 'cancelled' ? 'Cancelled ✕' : 'Confirmed ✓'}
                  </div>
                  {booking.can_cancel && (
                    <button
                      className="btn"
                      style={{ padding: '8px 16px', fontSize: 13, border: '1.5px solid #ef4444', color: '#ef4444', background: 'transparent', borderRadius: 8, cursor: cancellingId === booking.id ? 'wait' : 'pointer' }}
                      disabled={cancellingId === booking.id}
                      onClick={() => handleCancel(booking)}
                    >
                      {cancellingId === booking.id ? 'Cancelling…' : 'Cancel ticket'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export default UserBookings
