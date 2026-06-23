import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { useToast } from '../components/Toast.jsx'
import { Chart as ChartJS } from 'chart.js/auto'
import { Bar } from 'react-chartjs-2'

export default function Predict(){
  const [form,setForm]=React.useState({avg_score:67, attendance_rate:0.8, homework_completion:0.7, behavior_incidents:0})
  const [res,setRes]=React.useState(null)
  const [running,setRunning]=React.useState(false)
  const { notify } = useToast()
  const onChange=(k)=>(e)=> setForm({...form,[k]: e.target.type==='number'? Number(e.target.value): e.target.value})
  const submit=async()=>{
    try{
      setRunning(true)
      const r = await api.post('/ml/predict', form)
      setRes(r.data)
      notify('Prediction ready','success')
    }catch(err){
      notify('Failed to run prediction','error')
    }finally{
      setRunning(false)
    }
  }
  return (
    <div className="grid two-col">
      <Card title="Predict Performance" subtitle="Enter context to forecast risk and outcomes">
        <div className="grid-form">
          <label>Avg Score<input type="number" value={form.avg_score} onChange={onChange('avg_score')} /></label>
          <label>Attendance Rate<input type="number" step="0.01" value={form.attendance_rate} onChange={onChange('attendance_rate')} /></label>
          <label>Homework Completion<input type="number" step="0.01" value={form.homework_completion} onChange={onChange('homework_completion')} /></label>
          <label>Behavior Incidents<input type="number" value={form.behavior_incidents} onChange={onChange('behavior_incidents')} /></label>
          <Button onClick={submit} disabled={running}>{running? 'Running…':'Run Prediction'}</Button>
        </div>
      </Card>
      {res && (
        <Card title="Result" subtitle="Risk, probabilities and recommendations">
          <div className="grid">
            <div className="row"><h3>Risk</h3><div className="badge">{res.risk}</div></div>
            <div className="row"><h3>Predicted Score</h3><div className="badge">{res.prediction.predicted_score.toFixed(1)}</div></div>
            <div className="row"><h3>Pass Probability</h3><div className="badge">{(res.prediction.pass_prob*100).toFixed(1)}%</div></div>
            <div className="row"><h3>Expected Growth</h3><div className="badge">{(res.prediction.expected_growth*100).toFixed(1)}%</div></div>
            {res.shap && res.shap.length>0 && (
              <div>
                <h3>Feature Contributions (SHAP)</h3>
                <div style={{height:220}}>
                  <Bar data={{
                    labels: res.shap.map(s=> s.feature),
                    datasets: [{
                      label: 'SHAP value',
                      data: res.shap.map(s=> s.shap_value),
                      backgroundColor: 'rgba(79,70,229,0.45)'
                    }]
                  }} options={{ plugins:{ legend:{ display:false } }, indexAxis:'y', maintainAspectRatio:false, scales:{ x:{ grid:{ color:'rgba(255,255,255,.1)'}}, y:{ grid:{ display:false }}} }} />
                </div>
              </div>
            )}
            <div>
              <h3>Recommendations</h3>
              <ul className="list">{res.recommendations.map((r,i)=>(<li key={i}><b>{r.type}</b><span className="muted"> — {r.detail}</span></li>))}</ul>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
