import React from 'react'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import api from '../api'
import { useToast } from '../components/Toast.jsx'

export default function Alerts(){
  const [channel,setChannel]=React.useState('sms')
  const [to,setTo]=React.useState('2507XXXXXXX')
  const [message,setMessage]=React.useState('Reminder: Exam next week. Stay focused!')
  const [sending,setSending]=React.useState(false)
  const { notify } = useToast()

  const send = async ()=>{
    if(!to || !message){ notify('Recipient and message required','error'); return }
    try{
      setSending(true)
      const r = await api.post('/alerts/send', { channel, to, message })
      notify(`Alert ${r.data.status}`,'success')
    }catch(err){
      notify('Failed to send alert','error')
    }finally{
      setSending(false)
    }
  }

  return (
    <div className="grid two-col">
      <Card title="Send Alert" subtitle="Notify parents/teachers via SMS or WhatsApp">
        <div className="grid-form">
          <label>Channel
            <select value={channel} onChange={e=>setChannel(e.target.value)}>
              <option value="sms">SMS</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </label>
          <label>To<input placeholder="e.g., 2507… or whatsapp:+2507…" value={to} onChange={e=>setTo(e.target.value)} /></label>
          <label>Message<textarea rows={4} value={message} onChange={e=>setMessage(e.target.value)} /></label>
          <Button onClick={send} disabled={sending}>{sending? 'Sending…':'Send Alert'}</Button>
        </div>
      </Card>
      <Card title="Delivery Notes" subtitle="Environment-aware sending">
        <ul className="list">
          <li><b>Twilio</b><span className="muted"> — If credentials absent, backend mocks send.</span></li>
          <li><b>WhatsApp</b><span className="muted"> — Use format whatsapp:+&lt;country&gt;&lt;number&gt; if required.</span></li>
          <li><b>Auth</b><span className="muted"> — You must be logged in to send.</span></li>
        </ul>
      </Card>
    </div>
  )
}

