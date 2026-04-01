import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Mail, Phone, MapPin, Key, Plus, Trash2, User } from 'lucide-react'
import { StatusBadge } from './Dashboard'
import api from '../services/api'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('fr-FR')
}

export default function ClientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [client, setClient] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/clients/${id}`)
        setClient(res.data.data)
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    load()
  }, [id])

  const handleDelete = async () => {
    if (!confirm(`Desactiver le client "${client.name}" et revoquer toutes ses licences ?`)) return
    try {
      await api.delete(`/clients/${id}`)
      navigate('/clients')
    } catch (e) { alert('Erreur: ' + e.message) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (!client) {
    return <div className="p-8 text-red-400">Client non trouve</div>
  }

  return (
    <div className="p-6 space-y-6">
      {/* Back */}
      <Link to="/clients" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Retour aux clients
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-blue-600/20 rounded-xl flex items-center justify-center">
            <User className="w-7 h-7 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{client.name}</h1>
            <p className="text-gray-500 font-mono text-sm">{client.code}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/licenses/generate?client_id=${client.id}`}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Generer une licence
          </Link>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-4 py-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-500/20 rounded-lg text-sm font-medium transition-colors"
          >
            <Trash2 className="w-4 h-4" /> Desactiver
          </button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {client.email && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3">
            <Mail className="w-5 h-5 text-blue-400" />
            <div>
              <p className="text-xs text-gray-500">Email</p>
              <p className="text-sm">{client.email}</p>
            </div>
          </div>
        )}
        {client.phone && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3">
            <Phone className="w-5 h-5 text-blue-400" />
            <div>
              <p className="text-xs text-gray-500">Telephone</p>
              <p className="text-sm">{client.phone}</p>
            </div>
          </div>
        )}
        {client.address && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3">
            <MapPin className="w-5 h-5 text-blue-400" />
            <div>
              <p className="text-xs text-gray-500">Adresse</p>
              <p className="text-sm">{client.address}</p>
            </div>
          </div>
        )}
      </div>

      {/* Licences */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <h2 className="font-semibold flex items-center gap-2">
            <Key className="w-5 h-5 text-blue-400" />
            Licences ({client.licenses?.length || 0})
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left p-4 font-medium">Plan</th>
                <th className="text-left p-4 font-medium">Users</th>
                <th className="text-left p-4 font-medium">DWH</th>
                <th className="text-left p-4 font-medium">Machine</th>
                <th className="text-left p-4 font-medium">Expiration</th>
                <th className="text-left p-4 font-medium">Statut</th>
                <th className="text-left p-4 font-medium">Dernier check</th>
                <th className="p-4"></th>
              </tr>
            </thead>
            <tbody>
              {client.licenses?.map(lic => (
                <tr key={lic.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-4">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 capitalize">
                      {lic.plan}
                    </span>
                  </td>
                  <td className="p-4 text-gray-400">{lic.max_users}</td>
                  <td className="p-4 text-gray-400">{lic.max_dwh}</td>
                  <td className="p-4 text-gray-400 font-mono text-xs">{lic.hostname || lic.machine_id?.substring(0, 12) || '*'}</td>
                  <td className="p-4 text-gray-400">{formatDate(lic.expiry_date)}</td>
                  <td className="p-4"><StatusBadge status={lic.status} /></td>
                  <td className="p-4 text-gray-500 text-xs">{lic.last_check ? formatDate(lic.last_check) : 'Jamais'}</td>
                  <td className="p-4">
                    <Link to={`/licenses/${lic.id}`} className="text-blue-400 hover:text-blue-300 text-xs">
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
              {(!client.licenses || client.licenses.length === 0) && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-gray-600">
                    Aucune licence pour ce client
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
