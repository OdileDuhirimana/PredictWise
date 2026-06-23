import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { useToast } from '../components/Toast.jsx'

export default function Wellness(){
  const [studentId,setStudentId]=React.useState('1')
  const [res,setRes]=React.useState(null)
  const [running,setRunning]=React.useState(false)
  const { notify } = useToast()
  const fetchIt=()=> {
    setRunning(true)
    api.get(`/wellness/indicator?student_id=${studentId}`)
      .then(r=>{ setRes(r.data); notify('Indicator ready','success') })
      .catch(()=> notify('Failed to fetch indicator','error'))
      .finally(()=> setRunning(false))
  }
  return (
    <div className="grid two-col">
      <Card title="Wellness Indicator" subtitle="Evaluate mental health risk using recent signals">
        <div className="row" style={{gap:8}}>
          <input placeholder="Student ID" value={studentId} onChange={e=>setStudentId(e.target.value)} />
          <Button onClick={fetchIt} disabled={running}>{running? 'Checking…':'Check'}</Button>
        </div>
      </Card>
      {res && (
        <Card title="Result" subtitle="Composite score and risk label">
          <div className="grid">
            <div className="row"><h3>Risk</h3><div className="badge">{res.risk}</div></div>
            <div className="row"><h3>Score</h3><div className="badge">{res.score}</div></div>
            {res.inputs && (
              <div>
                <h3>Inputs</h3>
                <ul className="list">
                  <li>Mood avg: <span className="badge">{res.inputs.mood_avg}</span></li>
                  <li>Stress avg: <span className="badge">{res.inputs.stress_avg}</span></li>
                  <li>Sleep hrs: <span className="badge">{res.inputs.sleep_avg}</span></li>
                  <li>Attendance rate: <span className="badge">{res.inputs.attendance_rate}</span></li>
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
