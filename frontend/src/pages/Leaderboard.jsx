import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'

export default function Leaderboard(){
  const [items,setItems]=React.useState([])
  React.useEffect(()=>{ api.get('/gamify/leaderboard').then(r=>setItems(r.data.leaderboard)) },[])
  return (
    <Card title="Class Leaderboard" subtitle="Top performers by XP">
      {items.length? (
        <ol className="list">
          {items.map((i,idx)=> (
            <li key={i.student_id}><b>#{idx+1} {i.name}</b><span className="muted"> — {i.xp} XP (streak {i.streak})</span></li>
          ))}
        </ol>
      ) : <div className="muted">No leaderboard data yet.</div>}
    </Card>
  )
}
