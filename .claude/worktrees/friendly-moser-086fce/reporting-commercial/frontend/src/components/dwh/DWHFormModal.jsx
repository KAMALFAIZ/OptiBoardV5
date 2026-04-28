import { useState } from 'react'
import {
  Building2, Plus, Edit2, Database, Mail, Save, X,
  MapPin, TestTube, Loader2, CheckCircle, AlertCircle, XCircle, Trash2, Server,
  Lock, ChevronDown, ChevronRight
} from 'lucide-react'

function SSHTunnelSection({ formData, setFormData }) {
  const [open, setOpen] = useState(!!formData.ssh_enabled)
  return (
    <div className="border border-gray-200 dark:border-gray-600 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        <span className="flex items-center gap-2">
          <Lock size={15} />
          Tunnel SSH (accès sécurisé SQL Server distant)
          {formData.ssh_enabled && (
            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300">Activé</span>
          )}
        </span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>

      {open && (
        <div className="p-4 space-y-4 bg-white dark:bg-gray-800">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={!!formData.ssh_enabled}
              onChange={e => setFormData(f => ({ ...f, ssh_enabled: e.target.checked }))}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Activer le tunnel SSH</span>
          </label>

          {formData.ssh_enabled && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Hôte SSH (IP/hostname du serveur Sage)</label>
                  <input type="text" value={formData.ssh_host || ''}
                    onChange={e => setFormData(f => ({ ...f, ssh_host: e.target.value }))}
                    placeholder="192.168.1.100 ou sage.monentreprise.com"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Port SSH</label>
                  <input type="number" value={formData.ssh_port || 22}
                    onChange={e => setFormData(f => ({ ...f, ssh_port: parseInt(e.target.value) || 22 }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Utilisateur SSH (ex: sageTunnelUser)</label>
                <input type="text" value={formData.ssh_user || ''}
                  onChange={e => setFormData(f => ({ ...f, ssh_user: e.target.value }))}
                  placeholder="sageTunnelUser"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Clé privée SSH (contenu PEM — ED25519 ou RSA)
                </label>
                <textarea
                  rows={6}
                  value={formData.ssh_private_key || ''}
                  onChange={e => setFormData(f => ({ ...f, ssh_private_key: e.target.value }))}
                  placeholder={"-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----"}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm font-mono text-xs"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Le serveur SQL est accessible via <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">localhost,{'{port_local}'}</code> une fois le tunnel actif.
                  Le port 1433 reste fermé sur le firewall.
                </p>
              </div>
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3 text-xs text-amber-700 dark:text-amber-300">
                <strong>Serveur SQL DWH :</strong> laisser <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">.</code> ou <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">localhost</code> — le tunnel redirige automatiquement vers le SQL Server distant.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function DWHFormModal({
  show, onClose, modalMode,
  formData, setFormData,
  smtpData, setSmtpData,
  sourceForm, setSourceForm, sources,
  saving, testing, connectionStatus, selectedDWH,
  handleSaveDWH, handleSaveSMTP,
  handleTestConnection, handleTestSMTP,
  handleAddSource, handleDeleteSource
}) {
  if (!show) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header Modal */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            {modalMode === 'create' && <><Plus size={20} /> Nouveau DWH Client</>}
            {modalMode === 'edit' && <><Edit2 size={20} /> Modifier {formData.nom}</>}
            {modalMode === 'smtp' && <><Mail size={20} /> Configuration SMTP - {selectedDWH?.nom}</>}
            {modalMode === 'sources' && <><Database size={20} /> Sources Sage - {selectedDWH?.nom}</>}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content Modal */}
        <div className="p-6">
          {/* Formulaire DWH create/edit */}
          {(modalMode === 'create' || modalMode === 'edit') && (
            <div className="space-y-6">
              {/* Identification */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <Building2 size={16} />
                  Identification
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Code DWH *</label>
                    <input
                      type="text"
                      value={formData.code}
                      onChange={(e) => {
                        const code = e.target.value.toUpperCase()
                        setFormData(f => ({
                          ...f,
                          code,
                          // Auto-remplissage des bases si non modifiées manuellement
                          base_dwh:        f.base_dwh        === `DWH_${f.code}`             || !f.base_dwh        ? `DWH_${code}`             : f.base_dwh,
                          base_optiboard:  f.base_optiboard  === `OptiBoard_clt${f.code}`    || !f.base_optiboard  ? `OptiBoard_clt${code}`    : f.base_optiboard,
                        }))
                      }}
                      disabled={modalMode === 'edit'}
                      placeholder="Ex: CLIENT1"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700 disabled:bg-gray-100"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Nom *</label>
                    <input
                      type="text"
                      value={formData.nom}
                      onChange={(e) => setFormData({...formData, nom: e.target.value})}
                      placeholder="Nom du client"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Raison sociale</label>
                    <input
                      type="text"
                      value={formData.raison_sociale}
                      onChange={(e) => setFormData({...formData, raison_sociale: e.target.value})}
                      placeholder="Raison sociale complete"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                </div>
              </div>

              {/* Coordonnees */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <MapPin size={16} />
                  Coordonnees
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Adresse</label>
                    <input
                      type="text"
                      value={formData.adresse}
                      onChange={(e) => setFormData({...formData, adresse: e.target.value})}
                      placeholder="Adresse complete"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Ville</label>
                    <input
                      type="text"
                      value={formData.ville}
                      onChange={(e) => setFormData({...formData, ville: e.target.value})}
                      placeholder="Ville"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Pays</label>
                    <input
                      type="text"
                      value={formData.pays}
                      onChange={(e) => setFormData({...formData, pays: e.target.value})}
                      placeholder="Pays"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Telephone</label>
                    <input
                      type="text"
                      value={formData.telephone}
                      onChange={(e) => setFormData({...formData, telephone: e.target.value})}
                      placeholder="+212 5XX XX XX XX"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                      placeholder="contact@client.com"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">URL Logo</label>
                    <input
                      type="text"
                      value={formData.logo_url}
                      onChange={(e) => setFormData({...formData, logo_url: e.target.value})}
                      placeholder="https://..."
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                </div>
              </div>

              {/* Connexion Base DWH */}
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
                <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-3 flex items-center gap-2">
                  <Database size={16} />
                  Connexion Base DWH
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Serveur SQL *</label>
                    <input type="text" value={formData.serveur_dwh}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        serveur_dwh: e.target.value,
                        // Auto-sync serveur_optiboard SEULEMENT si pas encore modifié manuellement
                        // (vide ou égal à l'ancienne valeur DWH → suit ; sinon → garde la valeur manuelle)
                        serveur_optiboard: (!f.serveur_optiboard || f.serveur_optiboard === f.serveur_dwh)
                          ? e.target.value
                          : f.serveur_optiboard,
                      }))}
                      placeholder="server.domain.com"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Base de données *</label>
                    <input type="text" value={formData.base_dwh}
                      onChange={(e) => setFormData({...formData, base_dwh: e.target.value})}
                      placeholder="DWH_Client1"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Utilisateur SQL *</label>
                    <input type="text" value={formData.user_dwh}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        user_dwh: e.target.value,
                        // Auto-sync user_optiboard seulement si pas encore modifié manuellement
                        user_optiboard: (!f.user_optiboard || f.user_optiboard === f.user_dwh)
                          ? e.target.value
                          : f.user_optiboard,
                      }))}
                      placeholder="sa"
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Mot de passe SQL *</label>
                    <input type="password" value={formData.password_dwh}
                      onChange={(e) => setFormData({...formData, password_dwh: e.target.value})}
                      placeholder={modalMode === 'edit' ? '(inchange si vide)' : 'Mot de passe'}
                      className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                </div>
                <button onClick={handleTestConnection}
                  disabled={testing || !formData.serveur_dwh || !formData.base_dwh}
                  className="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg flex items-center gap-2"
                >
                  {testing ? <Loader2 className="animate-spin" size={16} /> : <TestTube size={16} />}
                  Tester la connexion
                </button>
                {connectionStatus && (
                  <div className={`mt-2 p-3 rounded-lg text-sm flex items-start gap-2 ${
                    connectionStatus.type === 'success' ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300'
                    : connectionStatus.type === 'warning' ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300'
                    : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
                  }`}>
                    {connectionStatus.type === 'success' ? <CheckCircle size={16} className="mt-0.5 shrink-0" />
                    : connectionStatus.type === 'warning' ? <AlertCircle size={16} className="mt-0.5 shrink-0" />
                    : <XCircle size={16} className="mt-0.5 shrink-0" />}
                    <span>{connectionStatus.message}</span>
                  </div>
                )}
              </div>

              {/* Connexion Base OptiBoard_XXXX */}
              <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-4">
                <h3 className="text-sm font-medium text-emerald-800 dark:text-emerald-300 mb-1 flex items-center gap-2">
                  <Server size={16} />
                  Connexion Base OptiBoard_{formData.code || 'XXXX'}
                </h3>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-3">
                  Base de données client OptiBoard (si différente du DWH)
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Serveur SQL</label>
                    <input type="text" value={formData.serveur_optiboard}
                      onChange={(e) => setFormData(f => ({...f, serveur_optiboard: e.target.value}))}
                      placeholder="server.domain.com ou ."
                      className="w-full px-3 py-2 border border-emerald-300 dark:border-emerald-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Base de données</label>
                    <input type="text" value={formData.base_optiboard}
                      onChange={(e) => setFormData(f => ({...f, base_optiboard: e.target.value}))}
                      placeholder={`OptiBoard_clt${formData.code || 'XXXX'}`}
                      className="w-full px-3 py-2 border border-emerald-300 dark:border-emerald-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Utilisateur SQL</label>
                    <input type="text" value={formData.user_optiboard}
                      onChange={(e) => setFormData(f => ({...f, user_optiboard: e.target.value}))}
                      placeholder="sa"
                      className="w-full px-3 py-2 border border-emerald-300 dark:border-emerald-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Mot de passe SQL</label>
                    <input type="password" value={formData.password_optiboard}
                      onChange={(e) => setFormData(f => ({...f, password_optiboard: e.target.value}))}
                      placeholder={modalMode === 'edit' ? '(inchangé si vide)' : 'Mot de passe'}
                      className="w-full px-3 py-2 border border-emerald-300 dark:border-emerald-600 rounded-lg bg-white dark:bg-gray-700"
                    />
                  </div>
                </div>
              </div>

              {/* Tunnel SSH */}
              <SSHTunnelSection formData={formData} setFormData={setFormData} />

              {/* Statut */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.actif}
                  onChange={(e) => setFormData({...formData, actif: e.target.checked})}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">DWH actif</span>
              </label>
            </div>
          )}

          {/* Formulaire SMTP */}
          {modalMode === 'smtp' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Serveur SMTP *</label>
                  <input
                    type="text"
                    value={smtpData.smtp_server}
                    onChange={(e) => setSmtpData({...smtpData, smtp_server: e.target.value})}
                    placeholder="smtp.gmail.com"
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Port *</label>
                  <input
                    type="number"
                    value={smtpData.smtp_port}
                    onChange={(e) => setSmtpData({...smtpData, smtp_port: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Utilisateur SMTP</label>
                  <input
                    type="text"
                    value={smtpData.smtp_username}
                    onChange={(e) => setSmtpData({...smtpData, smtp_username: e.target.value})}
                    placeholder="user@gmail.com"
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Mot de passe SMTP</label>
                  <input
                    type="password"
                    value={smtpData.smtp_password}
                    onChange={(e) => setSmtpData({...smtpData, smtp_password: e.target.value})}
                    placeholder="App password"
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Email expediteur *</label>
                  <input
                    type="email"
                    value={smtpData.from_email}
                    onChange={(e) => setSmtpData({...smtpData, from_email: e.target.value})}
                    placeholder="noreply@client.com"
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Nom expediteur</label>
                  <input
                    type="text"
                    value={smtpData.from_name}
                    onChange={(e) => setSmtpData({...smtpData, from_name: e.target.value})}
                    placeholder="OptiBoard"
                    className="w-full px-3 py-2 border border-primary-300 dark:border-primary-600 rounded-lg bg-white dark:bg-gray-700"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={smtpData.use_tls}
                  onChange={(e) => setSmtpData({...smtpData, use_tls: e.target.checked})}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Utiliser TLS</span>
              </label>
              <button
                onClick={handleTestSMTP}
                disabled={testing || !smtpData.smtp_server}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg flex items-center gap-2"
              >
                {testing ? <Loader2 className="animate-spin" size={16} /> : <TestTube size={16} />}
                Envoyer email test
              </button>
            </div>
          )}

          {/* Gestion Sources Sage */}
          {modalMode === 'sources' && (
            <div className="space-y-6">
              {/* Liste des sources existantes */}
              {sources.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Sources configurees ({sources.length})
                  </h4>
                  <div className="space-y-2">
                    {sources.map((src) => (
                      <div
                        key={src.code_societe}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{src.nom_societe}</p>
                          <p className="text-sm text-gray-500 font-mono">
                            {src.serveur_sage} / {src.base_sage}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {src.etl_enabled ? (
                            <span className="text-xs px-2 py-1 bg-green-100 text-green-600 rounded">ETL Actif</span>
                          ) : (
                            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">ETL Inactif</span>
                          )}
                          <button
                            onClick={() => handleDeleteSource(src.code_societe)}
                            className="p-1 text-red-600 hover:bg-red-50 rounded"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Formulaire ajout source */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Ajouter une source Sage
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Code societe *</label>
                    <input
                      type="text"
                      value={sourceForm.code_societe}
                      onChange={(e) => setSourceForm({...sourceForm, code_societe: e.target.value})}
                      placeholder="SOC1"
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Nom societe *</label>
                    <input
                      type="text"
                      value={sourceForm.nom_societe}
                      onChange={(e) => setSourceForm({...sourceForm, nom_societe: e.target.value})}
                      placeholder="Societe 1"
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Serveur Sage *</label>
                    <input
                      type="text"
                      value={sourceForm.serveur_sage}
                      onChange={(e) => setSourceForm({...sourceForm, serveur_sage: e.target.value})}
                      placeholder="server.domain.com"
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Base Sage *</label>
                    <input
                      type="text"
                      value={sourceForm.base_sage}
                      onChange={(e) => setSourceForm({...sourceForm, base_sage: e.target.value})}
                      placeholder="SAGE_GESCOM"
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">User Sage *</label>
                    <input
                      type="text"
                      value={sourceForm.user_sage}
                      onChange={(e) => setSourceForm({...sourceForm, user_sage: e.target.value})}
                      placeholder="sa"
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Password Sage *</label>
                    <input
                      type="password"
                      value={sourceForm.password_sage}
                      onChange={(e) => setSourceForm({...sourceForm, password_sage: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={sourceForm.etl_enabled}
                      onChange={(e) => setSourceForm({...sourceForm, etl_enabled: e.target.checked})}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-sm">ETL actif</span>
                  </label>
                  <select
                    value={sourceForm.etl_mode}
                    onChange={(e) => setSourceForm({...sourceForm, etl_mode: e.target.value})}
                    className="px-3 py-1 border rounded-lg text-sm"
                  >
                    <option value="incremental">Incremental</option>
                    <option value="full">Full</option>
                  </select>
                </div>
                <button
                  onClick={handleAddSource}
                  disabled={saving || !sourceForm.code_societe || !sourceForm.serveur_sage}
                  className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white rounded-lg flex items-center gap-2"
                >
                  {saving ? <Loader2 className="animate-spin" size={16} /> : <Plus size={16} />}
                  Ajouter la source
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Modal */}
        {(modalMode === 'create' || modalMode === 'edit' || modalMode === 'smtp') && (
          <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg"
            >
              Annuler
            </button>
            <button
              onClick={modalMode === 'smtp' ? handleSaveSMTP : handleSaveDWH}
              disabled={saving}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2"
            >
              {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
              Enregistrer
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
