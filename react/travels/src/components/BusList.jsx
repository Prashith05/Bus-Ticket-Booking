import React, { useState, useEffect } from 'react'
// import axios from 'axios'          //
import api from '../api.js' // Import the custom axios instance
import { useNavigate } from 'react-router-dom'

// Customers can book from today up to this many days ahead (same limit as the backend).
const BOOKING_WINDOW_DAYS = 30

// 'YYYY-MM-DD' in the user's own time zone (toISOString() would use UTC and can be a day off).
const toISODate = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

// '2026-11-04' -> 'Wed, 4 Nov 2026'
const prettyDate = (iso) => {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  })
}

const BusList = () => {
  const today = new Date()
  const maxDate = new Date()
  maxDate.setDate(maxDate.getDate() + BOOKING_WINDOW_DAYS)
  const minISO = toISODate(today)
  const maxISO = toISODate(maxDate)

  const [trips, setTrips] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState({ origin: '', destination: '', date: minISO })
  const [searchedDate, setSearchedDate] = useState(minISO)
  const navigate = useNavigate()

  // Ask the backend for the buses running on one date (it also applies From / To).
  const fetchTrips = async (params) => {
    try {
      const response = await api.get('/api/trips/', {
        params: {
          date: params.date,
          origin: params.origin || undefined,
          destination: params.destination || undefined,
        },
      })
      setTrips(response.data)
      setSearchedDate(params.date)
    } catch (err) {
      console.log('Error fetching buses', err)
      setTrips([])
      setError(
        err.response?.data?.date
          ? 'Please pick a valid date.'
          : 'Could not load buses. Please check your connection and try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  // Load today's buses when the page opens. (State is only set after the request
  // finishes, so the "set state in effect" warning does not apply here.)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTrips({ origin: '', destination: '', date: minISO })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSearch = () => {
    if (!search.date || search.date < minISO || search.date > maxISO) {
      setError(`Please pick a date between today and ${prettyDate(maxISO)}.`)
      return
    }
    setLoading(true)
    setError(null)
    fetchTrips(search)
  }

  const formatTime = (t) => {
    if (!t) return '--:--'
    return t.slice(0, 5)
  }

  const duration = (start, end) => {
    if (!start || !end) return ''
    const [sh, sm] = start.split(':').map(Number)
    const [eh, em] = end.split(':').map(Number)
    const diff = (eh * 60 + em) - (sh * 60 + sm)
    if (diff <= 0) return ''
    const h = Math.floor(diff / 60), m = diff % 60
    return `${h}h ${m}m`
  }

  return (
    <div style={{ paddingTop: 40, paddingBottom: 60 }}>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #1a2e22 0%, #2d5a3d 50%, #1e3d2a 100%)',
        borderRadius: 24,
        padding: '48px 40px',
        marginBottom: 40,
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Decorative circles */}
        <div style={{ position: 'absolute', top: -40, right: -40, width: 220, height: 220, borderRadius: '50%', background: 'rgba(46,204,138,0.08)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: -60, right: 80, width: 160, height: 160, borderRadius: '50%', background: 'rgba(46,204,138,0.06)', pointerEvents: 'none' }} />

        <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: 14, fontWeight: 600, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 10 }}>Your journey starts here</p>
        <h1 style={{ fontFamily: 'var(--font-display)', color: '#fff', fontSize: 40, fontWeight: 700, lineHeight: 1.15, marginBottom: 8 }}>
          Find & Book<br /><span style={{ color: 'var(--primary)' }}>Bus Tickets</span>
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 15, marginBottom: 36 }}>Search from hundreds of routes at the best prices</p>

        {/* Search bar */}
        <div style={{
          background: '#fff',
          borderRadius: 16,
          padding: 20,
          display: 'flex', gap: 12, alignItems: 'flex-end',
          flexWrap: 'wrap',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
        }}>
          <div style={{ flex: 1, minWidth: 140 }}>
            <div className="input-label" style={{ marginBottom: 6 }}>📍 From</div>
            <input
              className="input-field"
              placeholder="City or stop"
              value={search.origin}
              onChange={e => setSearch({ ...search, origin: e.target.value })}
              style={{ background: 'var(--bg)' }}
            />
          </div>
          <div style={{ flex: 1, minWidth: 140 }}>
            <div className="input-label" style={{ marginBottom: 6 }}>🏁 To</div>
            <input
              className="input-field"
              placeholder="City or stop"
              value={search.destination}
              onChange={e => setSearch({ ...search, destination: e.target.value })}
              style={{ background: 'var(--bg)' }}
            />
          </div>
          <div style={{ flex: 1, minWidth: 160 }}>
            <div className="input-label" style={{ marginBottom: 6 }}>📅 Date</div>
            <input
              className="input-field"
              type="date"
              min={minISO}
              max={maxISO}
              value={search.date}
              onChange={e => setSearch({ ...search, date: e.target.value })}
              style={{ background: 'var(--bg)' }}
            />
          </div>
          <button className="btn btn-accent" style={{ padding: '13px 28px', borderRadius: 10 }} onClick={handleSearch}>
            Search
          </button>
        </div>
      </div>

      {/* Results */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 20, color: 'var(--text)' }}>
          {loading ? 'Searching…' : `${trips.length} ${trips.length === 1 ? 'bus' : 'buses'} on ${prettyDate(searchedDate)}`}
        </h2>
        <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500 }}>Sorted by departure time</span>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🚌</div>
          <p style={{ color: 'var(--text-muted)' }}>Fetching available buses…</p>
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>⚠️</div>
          <p style={{ color: '#d4530c', fontWeight: 600 }}>{error}</p>
        </div>
      ) : trips.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🔍</div>
          <p style={{ color: 'var(--text-muted)' }}>No buses found for this date. Try different search terms or another day.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {trips.map((bus, i) => (
            <div key={bus.id} className="card" style={{
              padding: '24px 28px',
              display: 'flex', alignItems: 'center', gap: 24,
              flexWrap: 'wrap',
              transition: 'box-shadow 0.2s, transform 0.2s',
              cursor: 'default',
              animationDelay: `${i * 50}ms`,
            }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = 'var(--shadow)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.transform = 'none' }}
            >
              {/* Bus info */}
              <div style={{ minWidth: 140 }}>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  background: 'var(--primary-light)', color: 'var(--primary-dark)',
                  borderRadius: 8, padding: '4px 10px', fontSize: 12, fontWeight: 700,
                  marginBottom: 8, letterSpacing: 0.5,
                }}>
                  🚌 {bus.bus_name || 'Express'}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 500 }}>
                  {bus.number}
                </div>
              </div>

              {/* Route */}
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 16, minWidth: 240 }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>
                    {formatTime(bus.start_time)}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500, marginTop: 4 }}>{bus.origin}</div>
                </div>
                <div style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-light)', fontWeight: 600, marginBottom: 6 }}>
                    {duration(bus.start_time, bus.reach_time)}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)', border: '2px solid #fff', boxShadow: '0 0 0 2px var(--primary)' }} />
                    <div style={{ flex: 1, height: 2, background: 'linear-gradient(90deg, var(--primary), var(--accent))' }} />
                    <div style={{ fontSize: 14 }}>→</div>
                    <div style={{ flex: 1, height: 2, background: 'var(--border)' }} />
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', border: '2px solid #fff', boxShadow: '0 0 0 2px var(--accent)' }} />
                  </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>
                    {formatTime(bus.reach_time)}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500, marginTop: 4 }}>{bus.destination}</div>
                </div>
              </div>

              {/* Price & CTA */}
              <div style={{ textAlign: 'right', minWidth: 120 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, color: 'var(--text)' }}>
                  ₹{bus.price || '53'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-light)', marginBottom: 4 }}>per seat</div>
                <div style={{
                  fontSize: 12, fontWeight: 700, marginBottom: 10,
                  color: bus.available_seats === 0 ? '#ef4444' : bus.available_seats <= 5 ? '#d97706' : 'var(--primary-dark)',
                }}>
                  {bus.available_seats === 0 ? 'Sold out' : `${bus.available_seats} seats left`}
                </div>
                {/* `bus` here is one trip (a bus on this date), so bus.id is the trip id */}
                <button
                  className="btn btn-primary"
                  style={{ padding: '10px 20px', fontSize: 14 }}
                  onClick={() => navigate(`/trip/${bus.id}`)}
                >
                  View Seats
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default BusList
