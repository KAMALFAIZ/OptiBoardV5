import React, { useEffect, useState } from 'react'
import { channelsApi, productsApi } from '../services/api'

export default function SettingsPage() {
  const [config, setConfig] = useState({})
  const [form, setForm] = useState({})
  const [saved, setSaved] = useState(false)
  const [products, setProducts] = useState([])
  const [testChannel, setTestChannel] = useState('telegram')
  const [testContact, setTestContact] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [verifyResult, setVerifyResult] = useState(null)

  useEffect(() => {
    channelsApi.getConfig().then(r => { setConfig(r.data.data); setForm({}) }).catch(() => {})
    productsApi.list().then(r => setProducts(r.data.data)).catch(() => {})
  }, [])

  const save = async () => {
    await channelsApi.updateConfig(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    channelsApi.getConfig().then(r => setConfig(r.data.data))
  }

  const testSend = async () => {
    const res = await channelsApi.test({ channel: testChannel, contact_info: testContact })
    setTestResult(res.data)
  }

  const verify = async () => {
    const res = await channelsApi.verify(form)
    setVerifyResult(res.data.data)
  }

  const F = ({ label, name, placeholder, type = 'text' }) => (
    <div>
      <label className="text-xs text-gray-500 block mb-1">{label}</label>
      <input type={type} className="w-full border rounded px-3 py-2 text-sm" placeholder={placeholder || label}
        value={form[name] ?? ''}
        onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))} />
    </div>
  )

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-800">Paramètres</h1>

      {/* Telegram */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">✈️</span>
          <h2 className="font-semibold">Telegram</h2>
          {config.telegram_configured && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Configuré</span>}
        </div>
        <F label="Bot Token" name="telegram_bot_token" placeholder={config.telegram_bot_token || 'Non configuré'} />
        <div className="text-xs text-gray-400">Créer via @BotFather sur Telegram</div>
      </div>

      {/* WhatsApp */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">📱</span>
          <h2 className="font-semibold">WhatsApp (Twilio)</h2>
          {config.whatsapp_configured && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Configuré</span>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <F label="Account SID" name="twilio_account_sid" placeholder={config.twilio_account_sid || 'ACxxxxxxxx'} />
          <F label="Auth Token" name="twilio_auth_token" type="password" placeholder="••••••" />
          <F label="Numéro WhatsApp" name="twilio_whatsapp_from" placeholder={config.twilio_whatsapp_from || 'whatsapp:+14155238886'} />
        </div>
        <div className="text-xs text-gray-400">Compte Twilio + WhatsApp Sandbox activé</div>
      </div>

      {/* Email */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">📧</span>
          <h2 className="font-semibold">Email (SMTP)</h2>
          {config.email_configured && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Configuré</span>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <F label="Serveur SMTP" name="smtp_host" placeholder={config.smtp_host || 'smtp.gmail.com'} />
          <F label="Port" name="smtp_port" placeholder={config.smtp_port || '587'} />
          <F label="Email / User" name="smtp_user" placeholder={config.smtp_user || 'contact@kasoft.ma'} />
          <F label="Mot de passe" name="smtp_password" type="password" placeholder="••••••" />
          <F label="Nom expéditeur" name="smtp_from_name" placeholder={config.smtp_from_name || 'KAsoft Hub'} />
        </div>
      </div>

      <div className="flex gap-3">
        <button onClick={save} className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-indigo-700">
          {saved ? '✅ Sauvegardé' : 'Sauvegarder'}
        </button>
        <button onClick={verify} className="border px-5 py-2 rounded-lg text-sm hover:bg-gray-50">Vérifier credentials</button>
      </div>

      {verifyResult && (
        <div className="bg-gray-50 border rounded-xl p-4 text-sm space-y-1">
          {Object.entries(verifyResult).map(([ch, res]) => (
            <div key={ch} className="flex items-center gap-2">
              <span>{res.success ? '✅' : '❌'}</span>
              <span className="font-medium capitalize">{ch}</span>
              <span className="text-gray-500">{res.success ? (res.bot_name || res.account_name || 'OK') : res.error}</span>
            </div>
          ))}
        </div>
      )}

      {/* Test envoi */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h2 className="font-semibold">Test d'envoi</h2>
        <div className="flex gap-3">
          <select className="border rounded px-3 py-2 text-sm" value={testChannel} onChange={e => setTestChannel(e.target.value)}>
            <option value="telegram">Telegram</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="email">Email</option>
          </select>
          <input className="border rounded px-3 py-2 text-sm flex-1" placeholder={testChannel === 'telegram' ? 'chat_id' : testChannel === 'whatsapp' ? '+212xxxxxxxxx' : 'email@exemple.com'}
            value={testContact} onChange={e => setTestContact(e.target.value)} />
          <button onClick={testSend} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">Envoyer test</button>
        </div>
        {testResult && (
          <div className={`text-sm p-3 rounded ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {testResult.success ? '✅ Message envoyé avec succès' : `❌ ${testResult.error}`}
          </div>
        )}
      </div>

      {/* Produits / Webhooks */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h2 className="font-semibold">Webhooks produits</h2>
        <div className="text-xs text-gray-500 mb-2">URL : <code className="bg-gray-100 px-1 rounded">POST http://localhost:8085/api/webhook/&#123;PRODUCT_CODE&#125;</code></div>
        <div className="space-y-2">
          {products.map(p => (
            <div key={p.code} className="flex items-center justify-between border rounded p-3">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ background: p.couleur }} />
                <span className="font-medium text-sm">{p.nom}</span>
                <code className="text-xs bg-gray-100 px-1 rounded">{p.code}</code>
              </div>
              <button onClick={async () => {
                const r = await productsApi.getSecret(p.code)
                alert(`Secret webhook ${p.code}:\n${r.data.secret}`)
              }} className="text-xs text-indigo-600 hover:underline">Voir secret</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
