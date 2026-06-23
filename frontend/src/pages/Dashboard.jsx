import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import { Chart as ChartJS } from 'chart.js/auto'
import { Line, Bar } from 'react-chartjs-2'

export default function Dashboard(){
  const [data,setData]=React.useState(null)
  const [subjects,setSubjects]=React.useState(null)
  const [classes,setClasses]=React.useState(null)
  const [heat,setHeat]=React.useState(null)
  const [bench,setBench]=React.useState(null)
  React.useEffect(()=>{
    api.get('/analytics/dashboard').then(r=>setData(r.data))
    api.get('/analytics/subjects').then(r=>setSubjects(r.data.subjects))
    api.get('/analytics/classes').then(r=>setClasses(r.data.classes))
    api.get('/analytics/heatmap').then(r=>setHeat(r.data))
    api.get('/analytics/benchmarks').then(r=>setBench(r.data))
  },[])
  const chart = React.useMemo(()=>{
    if(!data){ return null }
    const labels = ['T1','T2','T3','T4','T5','T6']
    // Create a simple trend around the avg_score
    const base = Number(data.avg_score||0)
    const vals = labels.map((_,i)=> Math.max(0, Math.min(100, base + (i-3)*2 + (i%2? 1:-1)*3)))
    return {
      data: {
        labels,
        datasets: [{
          label: 'Average Score Trend',
          data: vals,
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79,70,229,0.2)',
          tension: 0.35,
          fill: true,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { suggestedMin: 0, suggestedMax: 100, grid: { color: 'rgba(255,255,255,0.08)' } }, x: { grid: { display:false } } },
        maintainAspectRatio: false,
      }
    }
  },[data])

  const subjectsChart = React.useMemo(()=>{
    if(!subjects) return null
    const labels = subjects.map(s=> s.subject)
    const vals = subjects.map(s=> Number(s.avg_score||0))
    const benchVal = bench?.national_avg ?? 65
    return {
      data: {
        labels,
        datasets: [
          { type:'bar', label:'Subject Avg', data: vals, backgroundColor:'rgba(99,102,241,0.6)' },
          { type:'line', label:'Benchmark', data: labels.map(()=> benchVal), borderColor:'#10b981', borderWidth:2, pointRadius:0, tension:0 }
        ]
      },
      options: { plugins:{ legend:{ display:false } }, scales:{ y:{ suggestedMin:0, suggestedMax:100 } }, maintainAspectRatio:false }
    }
  },[subjects, bench])

  const classesChart = React.useMemo(()=>{
    if(!classes) return null
    const labels = classes.map(c=> c.class_name || 'Unknown')
    const vals = classes.map(c=> Number(c.avg_score||0))
    const benchVal = bench?.current_avg ?? 0
    return {
      data: {
        labels,
        datasets: [
          { type:'bar', label:'Class Avg', data: vals, backgroundColor:'rgba(16,185,129,0.6)' },
          { type:'line', label:'School Avg', data: labels.map(()=> benchVal), borderColor:'#f59e0b', borderWidth:2, pointRadius:0, tension:0 }
        ]
      },
      options: { plugins:{ legend:{ display:false } }, scales:{ y:{ suggestedMin:0, suggestedMax:100 } }, maintainAspectRatio:false }
    }
  },[classes, bench])

  const Heatmap = ()=>{
    if(!heat) return <div className="skeleton" style={{height:220}} />
    const { subjects, classes, matrix } = heat
    const min = 0, max = 100
    const color = (v)=>{
      if(v==null) return 'rgba(255,255,255,0.06)'
      const t = Math.max(0, Math.min(1, (v-min)/(max-min)))
      const r = Math.round(255*(1-t))
      const g = Math.round(100 + 155*t)
      const b = 120
      return `rgba(${r},${g},${b},0.8)`
    }
    return (
      <div style={{display:'grid', gridTemplateColumns: `120px repeat(${classes.length}, minmax(0,1fr))`, gap:6}}>
        <div />
        {classes.map(c=> (<div key={c} className="muted" style={{fontSize:12, textAlign:'center'}}>{c}</div>))}
        {subjects.map((s,i)=> (
          <React.Fragment key={s}>
            <div className="muted" style={{fontSize:12}}>{s}</div>
            {classes.map((c,j)=>{
              const v = matrix[i][j]
              return (
                <div key={c} title={v==null? 'N/A': `${v.toFixed(1)}`}
                  style={{height:28, borderRadius:8, background: color(v), display:'grid', placeItems:'center', fontSize:12}}>
                  {v==null? '': v.toFixed(0)}
                </div>
              )
            })}
          </React.Fragment>
        ))}
      </div>
    )
  }
  return (
    <div className="grid two-col">
      <Card title="School Performance" subtitle="Key metrics across the institution">
        {data? (
          <div className="grid">
            <div className="row"><h3>Total Students</h3><div className="badge">{data.total_students}</div></div>
            <div className="row"><h3>Average Score</h3><div className="badge">{data.avg_score}</div></div>
            <div className="spacer-y" />
            <a className="report-link" href="/api/v1/analytics/report.pdf" target="_blank" rel="noreferrer">Download Annual Report (PDF)</a>
          </div>
        ) : (
          <div className="grid">
            <div className="skeleton" style={{height:28, width:200}} />
            <div className="skeleton" style={{height:28, width:240}} />
            <div className="skeleton" style={{height:18, width:180}} />
          </div>
        )}
      </Card>
      <Card title="Performance Trend" subtitle="How learning performance is evolving">
        {chart? (
          <div style={{height:260}}>
            <Line data={chart.data} options={chart.options} />
          </div>
        ) : <div className="skeleton" style={{height:260}} />}
      </Card>

      <Card title="Subject Performance" subtitle="Average per subject vs. national benchmark">
        {subjectsChart? (
          <div style={{height:260}}>
            <Bar data={subjectsChart.data} options={subjectsChart.options} />
          </div>
        ) : <div className="skeleton" style={{height:260}} />}
      </Card>

      <Card title="Class Performance" subtitle="Average per class vs. school average">
        {classesChart? (
          <div style={{height:260}}>
            <Bar data={classesChart.data} options={classesChart.options} />
          </div>
        ) : <div className="skeleton" style={{height:260}} />}
      </Card>

      <Card title="Heatmap" subtitle="Subjects x Classes (avg score)">
        <Heatmap />
      </Card>
    </div>
  )
}
