import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { useParams, useNavigate } from 'react-router-dom'

const BusSeats = ({ token }) => {
  const [bus, setBus] = useState(null)
  const [seats, setSeats] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [booking, setBooking] = useState(false)
  const [toast, setToast] = useState(null)
  const { busId } = useParams()
  const navigate = useNavigate()

  useEffect(() => {
    const fetchBusDetails = async () => {
      try {
        const response = await axios(`http://localhost:8000/api/buses/${busId}`)
        setBus(response.data)
        setSeats(response.data.seats || [])
      } catch (error) {
        console.log('Error fetching bus details', error)
      } finally {
        setLoading(false)
      }
    }
    fetchBusDetails()
  }, [busId])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const handleBook = async () => {
    if (!selected) return
    if (!token) {
      showToast('Please login to book a seat', 'error')
      setTimeout(() => navigate('/login'), 1200)
      return
    }
    setBooking(true)
    try {
      await axios.post('http://localhost:8000/api/booking/',
        { seat: selected },
        { headers: { Authorization: `Token ${token}` } }
      )
      showToast('Booking confirmed! 🎉')
      setSeats(prev => prev.map(s => s.id === selected ? { ...s, is_booked: true } : s))
      setSelected(null)
    } catch (error) {
      showToast(error.response?.data?.error || 'Booking failed', 'error')
    } finally {
      setBooking(false)
    }
  }

  const formatTime = (t) => t ? t.slice(0, 5) : '--:--'

  const selectedSeat = seats.find(s => s.id === selected)
  const available = seats.filter(s => !s.is_booked).length

  // Group seats into rows of 4 (2+2 layout)
  const rows = []
  for (let i = 0; i < seats.length; i += 4) {
    rows.push(seats.slice(i, i + 4))
  }

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>🚌</div>
      <p style={{ color: 'var(--text-muted)' }}>Loading bus details…</p>
    </div>
  )

  return (
    <div style={{ paddingTop: 36, paddingBottom: 60 }}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 999,
          background: toast.type === 'error' ? '#ef4444' : 'var(--primary)',
          color: '#fff', padding: '14px 22px', borderRadius: 12,
          fontWeight: 600, fontSize: 14,
          boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
          animation: 'slideIn 0.3s ease both',
        }}>
          {toast.msg}
        </div>
      )}

      <style>{`
        @keyframes slideIn { from { opacity:0; transform: translateX(20px) } to { opacity:1; transform: translateX(0) } }
        .seat-btn { transition: all 0.18s cubic-bezier(.4,0,.2,1); cursor: pointer; }
        .seat-btn:hover:not(:disabled) { transform: scale(1.08); }
      `}</style>

      {/* Back */}
      <button
        onClick={() => navigate('/')}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 24 }}
      >
        ← Back to results
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, alignItems: 'start' }}>
        {/* Left: Bus info + seat map */}
        <div>
          {/* Bus info card */}
          {bus && (
            <div className="card" style={{ padding: '28px 32px', marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                <div>
                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    background: 'var(--primary-light)', color: 'var(--primary-dark)',
                    borderRadius: 8, padding: '4px 12px', fontSize: 12, fontWeight: 700, marginBottom: 10,
                  }}>🚌 {bus.bus_name}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 500 }}>Bus #{bus.number}</div>
                </div>
                <div style={{
                  background: available > 5 ? 'var(--primary-light)' : '#fff3e0',
                  color: available > 5 ? 'var(--primary-dark)' : '#d97706',
                  borderRadius: 20, padding: '6px 14px', fontSize: 13, fontWeight: 700,
                }}>
                  {available} seats left
                </div>
              </div>

              {/* Route display */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 32, fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>
                    {formatTime(bus.start_time)}
                  </div>
                  <div style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 600, marginTop: 6 }}>{bus.origin}</div>
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div style={{ display: 'flex', width: '100%', alignItems: 'center' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--primary)', flexShrink: 0 }} />
                    <div style={{ flex: 1, height: 2, background: 'linear-gradient(90deg, var(--primary), var(--accent))' }} />
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0 }} />
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-light)', fontWeight: 600 }}>Direct Route</span>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 32, fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>
                    {formatTime(bus.reach_time)}
                  </div>
                  <div style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 600, marginTop: 6 }}>{bus.destination}</div>
                </div>
              </div>
            </div>
          )}

          {/* Seat map */}
          <div className="card" style={{ padding: 28 }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 6 }}>Select a Seat</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>Click on an available seat to select it</p>

            {/* Legend */}
            <div style={{ display: 'flex', gap: 20, marginBottom: 24 }}>
              {[
                { color: 'var(--primary)', label: 'Available' },
                { color: 'var(--accent)', label: 'Selected' },
                { color: '#e5e7eb', label: 'Booked' },
              ].map(({ color, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                  <div style={{ width: 16, height: 16, borderRadius: 4, background: color }} />
                  {label}
                </div>
              ))}
            </div>

            {/* Bus outline */}
            <div style={{
              background: 'var(--bg)', borderRadius: 20, padding: '20px 20px',
              border: '2px solid var(--border)', position: 'relative',
            }}>
              {/* Driver area */}
              <div style={{
                display: 'flex', justifyContent: 'flex-end', marginBottom: 16,
                paddingBottom: 16, borderBottom: '2px dashed var(--border)',
              }}>
                <div style={{
                  background: 'var(--surface)', border: '2px solid var(--border)',
                  borderRadius: 10, padding: '8px 14px', fontSize: 12, fontWeight: 700,
                  color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  🚗 Driver
                </div>
              </div>

              {/* Seat rows */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {rows.map((row, ri) => (
                  <div key={ri} style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                    {row.map((seat, ci) => {
                      const isBooked = seat.is_booked
                      const isSelected = selected === seat.id
                      const isAisle = ci === 1 // gap after 2nd seat
                      return (
                        <React.Fragment key={seat.id}>
                          <button
                            className="seat-btn"
                            disabled={isBooked}
                            onClick={() => setSelected(isSelected ? null : seat.id)}
                            style={{
                              width: 48, height: 52,
                              borderRadius: 10,
                              border: isSelected ? '2px solid var(--accent)' : isBooked ? '2px solid #e5e7eb' : '2px solid var(--primary)',
                              background: isSelected ? 'var(--accent)' : isBooked ? '#f1f2f4' : 'var(--primary-light)',
                              color: isSelected ? '#fff' : isBooked ? '#c0c4ce' : 'var(--primary-dark)',
                              fontWeight: 700, fontSize: 13,
                              cursor: isBooked ? 'not-allowed' : 'pointer',
                              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2,
                            }}
                            title={isBooked ? 'Booked' : `Seat ${seat.seat_number}`}
                          >
                            <span style={{ fontSize: 16 }}>{isBooked ? '🚫' : isSelected ? '✓' : '💺'}</span>
                            <span>{seat.seat_number}</span>
                          </button>
                          {/* Aisle space */}
                          {ci === 1 && <div style={{ width: 20 }} />}
                        </React.Fragment>
                      )
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Booking summary */}
        <div style={{ position: 'sticky', top: 'calc(var(--nav-h) + 20px)' }}>
          <div className="card" style={{ padding: 28 }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, marginBottom: 20 }}>Booking Summary</h3>

            {selectedSeat ? (
              <>
                <div style={{ background: 'var(--bg)', borderRadius: 12, padding: 16, marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>SELECTED SEAT</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text)' }}>
                    Seat {selectedSeat.seat_number}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
                  {[
                    { label: 'Route', value: `${bus?.origin} → ${bus?.destination}` },
                    { label: 'Departure', value: formatTime(bus?.start_time) },
                    { label: 'Arrival', value: formatTime(bus?.reach_time) },
                    { label: 'Price', value: `₹${bus?.price || '53'}` },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                      <span style={{ fontWeight: 600 }}>{value}</span>
                    </div>
                  ))}
                </div>
                <div style={{ borderTop: '1px dashed var(--border)', paddingTop: 16, marginBottom: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Total</span>
                    <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 22, color: 'var(--primary)' }}>₹{bus?.price || '53'}</span>
                  </div>
                </div>
                <button
                  className="btn btn-accent btn-full"
                  onClick={handleBook}
                  disabled={booking}
                  style={{ fontSize: 16, padding: '14px 0', borderRadius: 12 }}
                >
                  {booking ? 'Booking…' : 'Confirm Booking'}
                </button>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>💺</div>
                <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Select a seat to see your booking summary</p>
              </div>
            )}
          </div>

          {!token && (
            <div style={{
              background: 'var(--accent-light)', border: '1px solid rgba(255,107,61,0.2)',
              borderRadius: 12, padding: 16, marginTop: 12, fontSize: 13, color: '#d4530c', fontWeight: 500, textAlign: 'center',
            }}>
              ⚠️ You need to <strong><a href="/login" style={{ color: '#d4530c' }}>login</a></strong> to book seats
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default BusSeats
