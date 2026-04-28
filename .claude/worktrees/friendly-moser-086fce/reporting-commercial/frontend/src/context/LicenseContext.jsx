import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../services/api'

const LicenseContext = createContext(null)

export function LicenseProvider({ children }) {
  const [license, setLicense] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const checkLicense = useCallback(async () => {
    try {
      setLoading(true)
      const response = await api.get('/license/status')
      setLicense(response.data)
      setError(null)
    } catch (err) {
      console.error('Erreur verification licence:', err)
      setError(err.response?.data?.message || 'Erreur de verification')
      setLicense({ licensed: false, status: 'error' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkLicense()
  }, [checkLicense])

  const activateLicense = async (licenseKey) => {
    try {
      const response = await api.post('/license/activate', {
        license_key: licenseKey
      })
      if (response.data.success) {
        setLicense({
          licensed: true,
          license: response.data.license
        })
        setError(null)
        return { success: true, message: response.data.message }
      }
      return { success: false, message: response.data.message }
    } catch (err) {
      const message = err.response?.data?.detail || 'Erreur activation'
      setError(message)
      return { success: false, message }
    }
  }

  const deactivateLicense = async () => {
    try {
      await api.post('/license/deactivate')
      setLicense({ licensed: false, status: 'no_license' })
      return { success: true }
    } catch (err) {
      return { success: false, message: err.response?.data?.detail || 'Erreur' }
    }
  }

  const refreshLicense = async () => {
    try {
      const response = await api.post('/license/refresh')
      setLicense({
        licensed: response.data.success,
        license: response.data.license
      })
    } catch (err) {
      console.error('Erreur refresh licence:', err)
    }
  }

  const isLicensed = license?.licensed === true
  const isExpiringSoon = license?.license?.days_remaining <= 30 && license?.license?.days_remaining > 0
  const isGraceMode = license?.license?.grace_mode === true
  const licenseInfo = license?.license || null
  const machineId = license?.machine_id || ''

  // Features licensiées
  const features = licenseInfo?.features || []
  const hasFeature = (code) => features.includes('all') || features.includes(code)
  const isLimitedMode = isLicensed && !hasFeature('unlimited_rows')

  return (
    <LicenseContext.Provider value={{
      license: licenseInfo,
      loading,
      error,
      isLicensed,
      isExpiringSoon,
      isGraceMode,
      machineId,
      features,
      hasFeature,
      isLimitedMode,
      activateLicense,
      deactivateLicense,
      refreshLicense,
      checkLicense
    }}>
      {children}
    </LicenseContext.Provider>
  )
}

export function useLicense() {
  const context = useContext(LicenseContext)
  if (!context) {
    throw new Error('useLicense must be used within a LicenseProvider')
  }
  return context
}
