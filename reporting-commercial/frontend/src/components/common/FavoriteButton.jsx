import { useState, useEffect } from 'react'
import { Star } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'

/**
 * Bouton étoile pour ajouter/retirer un rapport des favoris.
 * Props: reportType ("gridview"|"dashboard"|"pivot"), reportId, reportNom
 */
export default function FavoriteButton({ reportType, reportId, reportNom }) {
  const { user } = useAuth()
  const [isFavorite, setIsFavorite] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!user?.id || !reportId) return
    api.get('/favorites/check', { params: { user_id: user.id, report_type: reportType, report_id: reportId } })
      .then(res => setIsFavorite(res.data.is_favorite || false))
      .catch(() => {})
  }, [user?.id, reportType, reportId])

  // Tracker la visite au montage du composant
  useEffect(() => {
    if (!user?.id || !reportId || !reportNom) return
    api.post('/favorites/recents', { report_type: reportType, report_id: reportId, nom: reportNom }, { params: { user_id: user.id } })
      .catch(() => {})
  }, [user?.id, reportType, reportId, reportNom])

  const toggle = async () => {
    if (!user?.id || loading) return
    setLoading(true)
    try {
      if (isFavorite) {
        await api.delete('/favorites', { params: { user_id: user.id, report_type: reportType, report_id: reportId } })
        setIsFavorite(false)
      } else {
        await api.post('/favorites', { report_type: reportType, report_id: reportId, nom: reportNom }, { params: { user_id: user.id } })
        setIsFavorite(true)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (!user?.id) return null

  return (
    <button
      onClick={toggle}
      disabled={loading}
      title={isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
      className={`p-1.5 rounded-lg transition-colors disabled:opacity-40 ${
        isFavorite
          ? 'text-amber-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20'
          : 'text-gray-400 hover:text-amber-400 hover:bg-gray-100 dark:hover:bg-gray-700'
      }`}
    >
      <Star className={`w-4 h-4 ${isFavorite ? 'fill-amber-400' : ''}`} />
    </button>
  )
}
