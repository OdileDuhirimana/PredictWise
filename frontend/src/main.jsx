import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import App from './pages/App.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Students from './pages/Students.jsx'
import Predict from './pages/Predict.jsx'
import Wellness from './pages/Wellness.jsx'
import Voice from './pages/Voice.jsx'
import DigitalTwin from './pages/DigitalTwin.jsx'
import Leaderboard from './pages/Leaderboard.jsx'
import DataEntry from './pages/DataEntry.jsx'
import Retraining from './pages/Retraining.jsx'
import Alerts from './pages/Alerts.jsx'
import './styles.css'
import { ToastProvider } from './components/Toast.jsx'
import { AuthProvider } from './auth/AuthContext.jsx'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import { LanguageProvider } from './i18n/LanguageContext.jsx'
import { SettingsProvider } from './a11y/SettingsContext.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <AuthProvider>
    <LanguageProvider>
      <SettingsProvider>
        <ToastProvider>
          <ErrorBoundary>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<App />}> 
                  <Route index element={<Dashboard />} />
                  <Route path="login" element={<Login />} />
                  <Route path="register" element={<Register />} />
                  <Route path="students" element={<ProtectedRoute><Students /></ProtectedRoute>} />
                  <Route path="data-entry" element={<ProtectedRoute><DataEntry /></ProtectedRoute>} />
                  <Route path="predict" element={<ProtectedRoute><Predict /></ProtectedRoute>} />
                  <Route path="wellness" element={<ProtectedRoute><Wellness /></ProtectedRoute>} />
                  <Route path="voice" element={<ProtectedRoute><Voice /></ProtectedRoute>} />
                  <Route path="digital-twin" element={<ProtectedRoute><DigitalTwin /></ProtectedRoute>} />
                  <Route path="alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
                  <Route path="leaderboard" element={<ProtectedRoute><Leaderboard /></ProtectedRoute>} />
                  <Route path="retraining" element={<ProtectedRoute><Retraining /></ProtectedRoute>} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </ErrorBoundary>
        </ToastProvider>
      </SettingsProvider>
    </LanguageProvider>
  </AuthProvider>
)
