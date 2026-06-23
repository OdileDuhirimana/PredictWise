import React from 'react'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import api from '../api'
import { useToast } from '../components/Toast.jsx'

function useInput(initial){
  const [v,setV]=React.useState(initial)
  return [v,(e)=>setV(e.target.value), setV]
}

export default function DataEntry(){
  const { notify } = useToast()
  // Assessments
  const [studentIdA, setStudentIdA] = useInput('1')
  const [subject, setSubject] = useInput('Math')
  const [score, setScore] = useInput('70')
  const [term, setTerm] = useInput('T1')
  const [savingA, setSavingA] = React.useState(false)

  const submitAssessment = async ()=>{
    if(!studentIdA || !subject || !score || !term){ notify('All fields required','error'); return }
    const s = Number(score)
    if(isNaN(s) || s<0 || s>100){ notify('Score must be 0-100','error'); return }
    try{
      setSavingA(true)
      await api.post('/students/assessment', { student_id: Number(studentIdA), subject, score: s, term })
      notify('Assessment saved','success')
    }catch{ notify('Failed to save assessment','error') }
    finally{ setSavingA(false) }
  }

  // Attendance
  const [studentIdT, setStudentIdT] = useInput('1')
  const [dateStr, setDateStr] = useInput(new Date().toISOString().slice(0,10))
  const [present, setPresentRaw] = React.useState(true)
  const [savingT, setSavingT] = React.useState(false)
  const setPresent = (e)=> setPresentRaw(e.target.checked)

  const submitAttendance = async ()=>{
    if(!studentIdT || !dateStr){ notify('Student and date required','error'); return }
    try{
      setSavingT(true)
      await api.post('/students/attendance', { student_id: Number(studentIdT), date: dateStr, present })
      notify('Attendance saved','success')
    }catch{ notify('Failed to save attendance','error') }
    finally{ setSavingT(false) }
  }

  // Survey
  const [studentIdS, setStudentIdS] = useInput('1')
  const [mood, setMood] = useInput('6')
  const [stress, setStress] = useInput('4')
  const [sleep, setSleep] = useInput('7.5')
  const [savingS, setSavingS] = React.useState(false)

  const submitSurvey = async ()=>{
    const m = Number(mood), st = Number(stress), sl = Number(sleep)
    if([studentIdS, mood, stress, sleep].some(x=> x==='')){ notify('All fields required','error'); return }
    if([m,st,sl].some(isNaN) || m<1||m>10||st<1||st>10||sl<0||sl>14){ notify('Invalid survey inputs','error'); return }
    try{
      setSavingS(true)
      await api.post('/students/survey', { student_id: Number(studentIdS), mood: m, stress: st, sleep_hours: sl })
      notify('Survey saved','success')
    }catch{ notify('Failed to save survey','error') }
    finally{ setSavingS(false) }
  }

  // Gamification Award
  const [studentIdG, setStudentIdG] = useInput('1')
  const [xp, setXp] = useInput('10')
  const [badge, setBadge] = useInput('')
  const [savingG, setSavingG] = React.useState(false)

  const submitAward = async ()=>{
    const sid = Number(studentIdG)
    const xpNum = Number(xp)
    if(!sid || isNaN(xpNum) || xpNum < 0){ notify('Valid student and XP required','error'); return }
    try{
      setSavingG(true)
      await api.post('/gamify/award', { student_id: sid, xp: xpNum, badge: badge || undefined })
      notify('Award granted','success')
      setBadge('')
    }catch{ notify('Failed to grant award','error') }
    finally{ setSavingG(false) }
  }

  return (
    <div className="grid two-col">
      <Card title="Add Assessment" subtitle="Record a subject score">
        <div className="grid-form">
          <label>Student ID<input value={studentIdA} onChange={setStudentIdA} /></label>
          <label>Subject<input value={subject} onChange={setSubject} /></label>
          <label>Score<input type="number" value={score} onChange={setScore} /></label>
          <label>Term<input value={term} onChange={setTerm} /></label>
          <Button onClick={submitAssessment} disabled={savingA}>{savingA? 'Saving…':'Save Assessment'}</Button>
        </div>
      </Card>

      <Card title="Add Attendance" subtitle="Mark present/absent for a date">
        <div className="grid-form">
          <label>Student ID<input value={studentIdT} onChange={setStudentIdT} /></label>
          <label>Date<input type="date" value={dateStr} onChange={setDateStr} /></label>
          <label>Present<input type="checkbox" checked={present} onChange={setPresent} /></label>
          <Button onClick={submitAttendance} disabled={savingT}>{savingT? 'Saving…':'Save Attendance'}</Button>
        </div>
      </Card>

      <Card title="Add Survey" subtitle="Mood, stress, sleep">
        <div className="grid-form">
          <label>Student ID<input value={studentIdS} onChange={setStudentIdS} /></label>
          <label>Mood (1-10)<input type="number" value={mood} onChange={setMood} /></label>
          <label>Stress (1-10)<input type="number" value={stress} onChange={setStress} /></label>
          <label>Sleep Hours<input type="number" step="0.1" value={sleep} onChange={setSleep} /></label>
          <Button onClick={submitSurvey} disabled={savingS}>{savingS? 'Saving…':'Save Survey'}</Button>
        </div>
      </Card>

      <Card title="Award XP/Badge" subtitle="Gamify motivation and progress">
        <div className="grid-form">
          <label>Student ID<input value={studentIdG} onChange={setStudentIdG} /></label>
          <label>XP<input type="number" value={xp} onChange={setXp} /></label>
          <label>Badge (optional)<input value={badge} onChange={setBadge} placeholder="e.g., Math Star" /></label>
          <Button onClick={submitAward} disabled={savingG}>{savingG? 'Granting…':'Grant Award'}</Button>
        </div>
      </Card>
    </div>
  )
}
