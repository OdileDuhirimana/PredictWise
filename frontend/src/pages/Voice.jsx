import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { useToast } from '../components/Toast.jsx'

export default function Voice(){
  const [text,setText]=React.useState('Student felt anxious and was late to class.')
  const [res,setRes]=React.useState(null)
  const [running,setRunning]=React.useState(false)
  const { notify } = useToast()
  const analyze=async()=>{
    try{
      setRunning(true)
      const r = await api.post('/voice/analyze', {transcript:text})
      setRes(r.data)
      notify('Analysis complete','success')
    }catch(err){
      notify('Failed to analyze transcript','error')
    }finally{
      setRunning(false)
    }
  }
  return (
    <div className="grid two-col">
      <Card title="Voice-to-Insight" subtitle="Paste a transcript to extract sentiment and behaviors">
        <div className="col">
          <textarea rows={6} value={text} onChange={e=>setText(e.target.value)} />
          <div>
            <Button onClick={analyze} disabled={running}>{running? 'Analyzing…':'Analyze'}</Button>
          </div>
        </div>
      </Card>
      {res && (
        <Card title="Analysis" subtitle="Detected signals">
          <div className="grid">
            <div className="row"><h3>Sentiment</h3><div className="badge">{res.sentiment.label}</div><span className="muted"> (compound {res.sentiment.compound})</span></div>
            <div>
              <h3>Behaviors</h3>
              {res.behaviors.length? (
                <ul className="list">{res.behaviors.map((b,i)=>(<li key={i}>{b}</li>))}</ul>
              ) : <div className="muted">No specific behaviors detected.</div>}
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
