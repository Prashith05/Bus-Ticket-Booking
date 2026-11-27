import React, { useState, useEffect } from 'react'
// import axios from 'axios'
import api from '../api.js' // Import the custom axios instance
import { useParams, useNavigate } from 'react-router-dom'

// '2026-11-04' -> 'Wed, 4 Nov 2026'
const prettyDate = (iso) => {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  })
}

// How many seats one booking may include (the server enforces the same limit).
const MAX_SEATS_PER_BOOKING = 6

// Same rules as the server (which always re-checks them). Returns the problems found, or null.
const GENDERS = [{ value: 'M', label: 'Male' }, { value: 'F', label: 'Female' }, { value: 'O', label: 'Other' }]

const cleanName = (v) => (v || '').trim().replace(/\s+/g, ' ')

const checkPassenger = (p = {}) => {
  const errs = {}
  const name = cleanName(p.name)
  if (name.length < 2) errs.name = 'Enter the full name'
  else if (!/\p{L}/u.test(name) || /[<>]/.test(name)) errs.name = 'Use letters only'
  const age = Number(p.age)
  if (String(p.age ?? '').trim() === '') errs.age = 'Enter age'
  else if (!Number.isInteger(age) || age < 1 || age > 120) errs.age = 'Age 1–120'
  if (!['M', 'F', 'O'].includes(p.gender)) errs.gender = 'Choose one'
  return Object.keys(errs).length ? errs : null
}

const checkPhone = (v) => {
  const digits = (v || '').replace(/[\s-]/g, '').replace(/^\+91/, '').replace(/^91(?=\d{10}$)/, '').replace(/^0(?=\d{10}$)/, '')
  return /^[6-9]\d{9}$/.test(digits) ? null : 'Enter a valid 10-digit mobile number'
}

const checkEmail = (v) => (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((v || '').trim()) ? null : 'Enter a valid email address')

// The phone and email used last time are remembered in this browser (not important if that fails).
const saved = (key) => {
  try { return localStorage.getItem(key) || '' } catch { return '' }
}

const fieldErrStyle = { color: '#ef4444', fontSize: 11, fontWeight: 600, marginTop: 4 }
const invalid = (bad) => (bad ? { borderColor: '#ef4444' } : {})

// `bus` below is one trip: a bus on a specific date, with that date's own seats.
const BusSeats = ({ token }) => {
  const [bus, setBus] = useState(null)
  const [seats, setSeats] = useState([])
  const [selected, setSelected] = useState([]) // ids of the seats the person has picked
  const [passengers, setPassengers] = useState({}) // seat id -> { name, age, gender }
  const [phone, setPhone] = useState(() => saved('contactPhone'))
  const [email, setEmail] = useState(() => saved('contactEmail'))
  const [showErrors, setShowErrors] = useState(false) // show field problems after the first Book click
  const [loading, setLoading] = useState(true)
  const [booking, setBooking] = useState(false)
  const [toast, setToast] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const { tripId } = useParams()
  const navigate = useNavigate()

  useEffect(() => {
    const fetchBusDetails = async () => {
      try {
        const response = await api.get(`/api/trips/${tripId}/`)
        setBus(response.data)
        setSeats(response.data.seats || [])
      } catch (error) {
        console.log('Error fetching trip details', error)
        setLoadError(
          error.response?.status === 404
            ? 'This trip could not be found.'
            : 'Could not load this trip. Please try again.'
        )
      } finally {
        setLoading(false)
      }
    }
    fetchBusDetails()
  }, [tripId])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  // Tap a seat to pick it, tap again to un-pick it (up to MAX_SEATS_PER_BOOKING seats).
  const toggleSeat = (seatId) => {
    if (selected.includes(seatId)) {
      setSelected(selected.filter(id => id !== seatId))
    } else if (selected.length >= MAX_SEATS_PER_BOOKING) {
      showToast(`You can select up to ${MAX_SEATS_PER_BOOKING} seats at a time`, 'error')
    } else {
      setSelected([...selected, seatId])
    }
  }

  const setPassengerField = (seatId, field, value) =>
    setPassengers(prev => ({ ...prev, [seatId]: { ...prev[seatId], [field]: value } }))

  const handleBook = async () => {
    if (selected.length === 0 || closed) return
    if (!token) {
      showToast('Please login to book seats', 'error')
      setTimeout(() => navigate('/login'), 1200)
      return
    }
    // Every picked seat needs a passenger, and we need one contact number.
    const orderedIds = seats.filter(s => selected.includes(s.id)).map(s => s.id)
    if (checkPhone(phone) || checkEmail(email) || orderedIds.some(id => checkPassenger(passengers[id]))) {
      setShowErrors(true)
      showToast('Please fill in the passenger details', 'error')
      document.getElementById('passenger-details')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    setBooking(true)
    const count = selected.length
    try {
      await api.post('/api/booking/',
        {
          contact_phone: phone.trim(),
          contact_email: email.trim(),
          passengers: orderedIds.map(id => ({
            seat: id,
            name: cleanName(passengers[id].name),
            age: Number(passengers[id].age),
            gender: passengers[id].gender,
          })),
        },
        { headers: { Authorization: `Token ${token}` } }
      )
      try { localStorage.setItem('contactPhone', phone.trim()); localStorage.setItem('contactEmail', email.trim()) } catch { /* private mode: not important */ }
      setShowErrors(false)
      setPassengers(prev => {
        const rest = { ...prev }
        selected.forEach(id => delete rest[id])
        return rest
      })
      showToast(count === 1 ? 'Booking confirmed! 🎉' : `${count} seats booked! 🎉`)
      setSeats(prev => prev.map(s => selected.includes(s.id) ? { ...s, is_booked: true } : s))
      setSelected([])
    } catch (error) {
      // All or nothing: if someone else took some of the seats meanwhile, nothing was booked.
      // Mark those seats as taken and keep the rest selected so the person can try again.
      const taken = error.response?.data?.unavailable_seats
      if (taken?.length) {
        setSeats(prev => prev.map(s => taken.includes(s.id) ? { ...s, is_booked: true } : s))
        setSelected(prev => prev.filter(id => !taken.includes(id)))
      }
      showToast(error.response?.data?.error || 'Booking failed', 'error')
    } finally {
      setBooking(false)
    }
  }

  const formatTime = (t) => t ? t.slice(0, 5) : '--:--'

  // The picked seats in seat order (S1, S2, ...), and what they cost together.
  const selectedSeats = seats.filter(s => selected.includes(s.id))
  const pricePerSeat = Number(bus?.price || 53)
  const total = (pricePerSeat * selectedSeats.length).toFixed(2)
  const available = seats.filter(s => !s.is_booked).length
  // Booking stops shortly before departure (the server enforces this too). For such a trip the
  // server does not send any seats, so we show a message instead of a seat map.
  const departed = !!bus?.departed
  const closed = !!bus?.booking_closed

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

  if (loadError) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>⚠️</div>
      <p style={{ color: '#d4530c', fontWeight: 600, marginBottom: 16 }}>{loadError}</p>
      <button className="btn btn-primary" onClick={() => navigate('/')}>← Back to search</button>
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

      <div style={{ display: 'grid', gridTemplateColumns: closed ? '1fr' : '1fr 340px', gap: 24, alignItems: 'start' }}>
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
                  <div style={{ color: 'var(--text)', fontSize: 14, fontWeight: 700, marginTop: 6 }}>📅 {prettyDate(bus.date)}</div>
                </div>
                <div style={{
                  background: closed ? '#eef0f3' : available > 5 ? 'var(--primary-light)' : '#fff3e0',
                  color: closed ? '#667085' : available > 5 ? 'var(--primary-dark)' : '#d97706',
                  borderRadius: 20, padding: '6px 14px', fontSize: 13, fontWeight: 700,
                }}>
                  {departed ? 'Departed' : closed ? 'Booking closed' : `${available} seats left`}
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

          {closed ? (
            /* Dimmed message in place of the seat map: no seats are loaded for a closed trip */
            <div className="card" style={{
              padding: '56px 32px', textAlign: 'center', background: 'var(--bg)',
              border: '1.5px dashed var(--border)',
            }}>
              <div style={{ fontSize: 46, marginBottom: 14, filter: 'grayscale(1)', opacity: 0.7 }}>
                {departed ? '🚌' : '⏱️'}
              </div>
              <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 20, color: 'var(--text-muted)', marginBottom: 8 }}>
                {departed ? 'This bus has left' : 'Booking has closed for this bus'}
              </h3>
              <p style={{ fontSize: 14, color: 'var(--text-muted)', maxWidth: 420, margin: '0 auto 24px', lineHeight: 1.6 }}>
                {departed
                  ? `${bus.bus_name} departed at ${formatTime(bus.start_time)} on ${prettyDate(bus.date)}, so seats are no longer available.`
                  : `Tickets can be booked until ${bus.booking_cutoff_minutes} minutes before departure. ${bus.bus_name} leaves at ${formatTime(bus.start_time)}.`}
              </p>
              <button className="btn btn-primary" style={{ padding: '11px 24px' }} onClick={() => navigate('/')}>
                Browse other buses
              </button>
            </div>
          ) : (
          /* Seat map */
          <div className="card" style={{ padding: 28 }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 6 }}>Select Seats</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>Tap the seats you want. You can book up to {MAX_SEATS_PER_BOOKING} seats at a time.</p>

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
                      const isSelected = selected.includes(seat.id)
                      const isAisle = ci === 1 // gap after 2nd seat
                      return (
                        <React.Fragment key={seat.id}>
                          <button
                            className="seat-btn"
                            disabled={isBooked}
                            onClick={() => toggleSeat(seat.id)}
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
          )}

          {/* Passenger details: one row per picked seat, and one contact number */}
          {!closed && selectedSeats.length > 0 && (
            <div id="passenger-details" className="card" style={{ padding: 28, marginTop: 20 }}>
              <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 6 }}>Passenger Details</h3>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
                Enter the name, age and gender of the person who will travel in each seat.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {selectedSeats.map((seat, i) => {
                  const p = passengers[seat.id] || {}
                  const errs = (showErrors && checkPassenger(p)) || {}
                  return (
                    <div key={seat.id} style={{ background: 'var(--bg)', borderRadius: 12, padding: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                        <span style={{ background: 'var(--accent)', color: '#fff', borderRadius: 8, padding: '4px 10px', fontWeight: 700, fontSize: 13 }}>
                          {seat.seat_number}
                        </span>
                        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)' }}>Passenger {i + 1}</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 2fr) 90px minmax(120px, 1fr)', gap: 12 }}>
                        <div className="input-group">
                          <label className="input-label" htmlFor={`name-${seat.id}`}>Full name</label>
                          <input
                            id={`name-${seat.id}`} className="input-field" style={invalid(errs.name)}
                            value={p.name || ''} maxLength={100} placeholder="As on ID"
                            onChange={e => setPassengerField(seat.id, 'name', e.target.value)}
                          />
                          {errs.name && <div style={fieldErrStyle}>{errs.name}</div>}
                        </div>
                        <div className="input-group">
                          <label className="input-label" htmlFor={`age-${seat.id}`}>Age</label>
                          <input
                            id={`age-${seat.id}`} className="input-field" style={invalid(errs.age)}
                            type="number" min="1" max="120" inputMode="numeric"
                            value={p.age ?? ''} placeholder="Age"
                            onChange={e => setPassengerField(seat.id, 'age', e.target.value)}
                          />
                          {errs.age && <div style={fieldErrStyle}>{errs.age}</div>}
                        </div>
                        <div className="input-group">
                          <label className="input-label" htmlFor={`gender-${seat.id}`}>Gender</label>
                          <select
                            id={`gender-${seat.id}`} className="input-field" style={invalid(errs.gender)}
                            value={p.gender || ''}
                            onChange={e => setPassengerField(seat.id, 'gender', e.target.value)}
                          >
                            <option value="">Select</option>
                            {GENDERS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
                          </select>
                          {errs.gender && <div style={fieldErrStyle}>{errs.gender}</div>}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16, marginTop: 20 }}>
              <div className="input-group">
                <label className="input-label" htmlFor="contact-email">Email address</label>
                <input
                  id="contact-email" className="input-field" style={invalid(showErrors && checkEmail(email))}
                  type="email" inputMode="email" maxLength={254} placeholder="you@example.com"
                  value={email} onChange={e => setEmail(e.target.value)}
                />
                {showErrors && checkEmail(email) && <div style={fieldErrStyle}>{checkEmail(email)}</div>}
                <div style={{ fontSize: 12, color: 'var(--text-light)', marginTop: 4 }}>
                  Your ticket and trip updates are sent here.
                </div>
              </div>
              <div className="input-group">
                <label className="input-label" htmlFor="contact-phone">Contact mobile number</label>
                <input
                  id="contact-phone" className="input-field" style={invalid(showErrors && checkPhone(phone))}
                  type="tel" inputMode="tel" maxLength={16} placeholder="10-digit mobile number"
                  value={phone} onChange={e => setPhone(e.target.value)}
                />
                {showErrors && checkPhone(phone) && <div style={fieldErrStyle}>{checkPhone(phone)}</div>}
                <div style={{ fontSize: 12, color: 'var(--text-light)', marginTop: 4 }}>
                  We use this to reach you about this trip.
                </div>
              </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Booking summary (not needed when booking is closed) */}
        {!closed && (
        <div style={{ position: 'sticky', top: 'calc(var(--nav-h) + 20px)' }}>
          <div className="card" style={{ padding: 28 }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, marginBottom: 20 }}>Booking Summary</h3>

            {selectedSeats.length > 0 ? (
              <>
                <div style={{ background: 'var(--bg)', borderRadius: 12, padding: 16, marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 10 }}>
                    SELECTED SEAT{selectedSeats.length > 1 ? 'S' : ''} ({selectedSeats.length}/{MAX_SEATS_PER_BOOKING})
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {selectedSeats.map(s => (
                      <span key={s.id} style={{
                        background: 'var(--accent)', color: '#fff', borderRadius: 8,
                        padding: '6px 12px', fontWeight: 700, fontSize: 15,
                      }}>{s.seat_number}</span>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
                  {[
                    { label: 'Route', value: `${bus?.origin} → ${bus?.destination}` },
                    { label: 'Date', value: prettyDate(bus?.date) },
                    { label: 'Departure', value: formatTime(bus?.start_time) },
                    { label: 'Arrival', value: formatTime(bus?.reach_time) },
                    { label: 'Price per seat', value: `₹${pricePerSeat.toFixed(2)}` },
                    { label: 'Seats', value: selectedSeats.length },
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
                    <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 22, color: 'var(--primary)' }}>₹{total}</span>
                  </div>
                </div>
                <button
                  className="btn btn-accent btn-full"
                  onClick={handleBook}
                  disabled={booking}
                  style={{ fontSize: 16, padding: '14px 0', borderRadius: 12 }}
                >
                  {booking ? 'Booking…' : `Book ${selectedSeats.length} seat${selectedSeats.length > 1 ? 's' : ''}`}
                </button>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>💺</div>
                <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Select seats to see your booking summary</p>
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
        )}
      </div>
    </div>
  )
}

export default BusSeats
