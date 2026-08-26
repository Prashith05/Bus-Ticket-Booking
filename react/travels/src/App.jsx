import React, { useState } from 'react'
import { Routes, Route, useNavigate, Link } from 'react-router-dom'
import RegisterForm from './components/RegisterForm'
import LoginForm from './components/LoginForm'
import BusList from './components/BusList'
import BusSeats from './components/BusSeats'
import UserBookings from './components/UserBookings'
import Wrapper from './components/Wrapper'
import './App.css'

const App = () => {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [userId, setUserId] = useState(localStorage.getItem('userId'))

  const handleLogin = (token, userId) => {
    localStorage.setItem('token', token)
    localStorage.setItem('userId', userId)
    setToken(token)
    setUserId(userId)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    setToken(null)
    setUserId(null)
  }

  return (
    <Wrapper handleLogout={handleLogout} token={token} userId={userId}>
      <Routes>
        <Route path='/' element={<BusList />} />
        <Route path='/register' element={<RegisterForm />} />
        <Route path='/login' element={<LoginForm onLogin={handleLogin} />} />
        <Route path='/bus/:busId' element={<BusSeats token={token} />} />
        <Route path='/my-bookings' element={<UserBookings token={token} userId={userId} />} />
      </Routes>
    </Wrapper>
  )
}

export default App
