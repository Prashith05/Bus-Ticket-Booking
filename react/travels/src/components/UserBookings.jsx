import React, { useState, useEffect } from 'react'
// import axios from 'axios'
import api from '../api.js' // Import the custom axios instance
import { Link } from 'react-router-dom'

const GENDER_LABELS = { M: 'Male', F: 'Female', O: 'Other' }

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

  // One card per bus and date: seats booked together (or separately) on the same trip are grouped,
  // each with its own status and Cancel button. The server sends newest first, so the order is kept.
  const groups = []
  const byTrip = new Map()
  bookings.forEach(b => {
    let group = byTrip.get(b.trip)
    if (!group) {
      group = { trip: b.trip, seats: [] }
      byTrip.set(b.trip, group)
      groups.push(group)
    }
    group.seats.push(b)
  })
  groups.forEach(g => g.seats.sort((a, b) => a.seat - b.seat)) // seat order: S1, S2, ...

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
              { icon: '🎫', label: 'Seats Booked', value: bookings.length },
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

          {/* Booking list: one card per bus and date */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {groups.map(group => {
              const first = group.seats[0]
              const total = group.seats.length
              const confirmed = group.seats.filter(b => b.status === 'confirmed').length
              const allCancelled = confirmed === 0
              const badge = allCancelled ? 'Cancelled ✕' : confirmed === total ? 'Confirmed ✓' : `${confirmed} of ${total} confirmed`
              return (
                <div key={group.trip} className="card" style={{ padding: '22px 28px', display: 'flex', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap', opacity: allCancelled ? 0.6 : 1 }}>
                  {/* Ticket icon */}
                  <div style={{
                    width: 44, height: 44, borderRadius: 12,
                    background: 'var(--primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, flexShrink: 0,
                  }}>🎫</div>

                  <div style={{ flex: 1, minWidth: 240 }}>
                    <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4, color: 'var(--text)' }}>
                      {first.bus_name} · {total} {total === 1 ? 'seat' : 'seats'}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                      {first.origin} → {first.destination} · {first.start_time?.slice(0, 5)} - {first.reach_time?.slice(0, 5)}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600, marginBottom: 12 }}>
                      📅 Travel date: {formatTravelDate(first.travel_date)}
                    </div>
                    {first.contact_phone && (
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: -8, marginBottom: 12 }}>
                        📞 Contact: {first.contact_phone}
                      </div>
                    )}

                    {/* One row per seat, each with its own status and Cancel button */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {group.seats.map(b => {
                        const cancelled = b.status === 'cancelled'
                        return (
                          <div key={b.id} style={{
                            display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                            padding: '8px 12px', borderRadius: 10, background: 'var(--bg)',
                          }}>
                            <span style={{
                              minWidth: 38, textAlign: 'center', fontWeight: 700, fontSize: 13,
                              padding: '4px 8px', borderRadius: 8, background: '#fff', border: '1px solid var(--border)',
                              color: cancelled ? 'var(--text-muted)' : 'var(--text)',
                              textDecoration: cancelled ? 'line-through' : 'none',
                            }}>{b.seat_number}</span>
                            {/* Who is travelling (bookings made before passenger details existed have none) */}
                            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', minWidth: 130, textDecoration: cancelled ? 'line-through' : 'none' }}>
                              {b.passenger_name
                                ? `${b.passenger_name} · ${b.passenger_age} · ${GENDER_LABELS[b.passenger_gender] || ''}`
                                : <span style={{ color: 'var(--text-light)', fontWeight: 500 }}>No passenger name</span>}
                            </span>
                            <span style={{ fontSize: 12, fontWeight: 700, color: cancelled ? '#b42318' : 'var(--primary-dark)' }}>
                              {cancelled ? 'Cancelled ✕' : 'Confirmed ✓'}
                            </span>
                            <span style={{ fontSize: 12, color: 'var(--text-muted)', flex: 1, minWidth: 150 }}>
                              {cancelled && b.cancelled_at ? `Cancelled ${formatDate(b.cancelled_at)}` : `Booked ${formatDate(b.booking_time)}`}
                            </span>
                            {b.can_cancel && (
                              <button
                                className="btn"
                                style={{ padding: '6px 14px', fontSize: 12, border: '1.5px solid #ef4444', color: '#ef4444', background: 'transparent', borderRadius: 8, cursor: cancellingId === b.id ? 'wait' : 'pointer' }}
                                disabled={cancellingId === b.id}
                                onClick={() => handleCancel(b)}
                              >
                                {cancellingId === b.id ? 'Cancelling…' : 'Cancel seat'}
                              </button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  <div style={{
                    background: allCancelled ? '#fdecea' : 'var(--primary-light)',
                    color: allCancelled ? '#b42318' : 'var(--primary-dark)',
                    borderRadius: 20, padding: '6px 14px',
                    fontSize: 12, fontWeight: 700,
                  }}>
                    {badge}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

export default UserBookings
