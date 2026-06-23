import React from 'react'

export default class ErrorBoundary extends React.Component{
  constructor(props){
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error){
    return { hasError: true, error }
  }
  componentDidCatch(error, info){
    // Could send to monitoring here
    // console.error('ErrorBoundary', error, info)
  }
  render(){
    if (this.state.hasError){
      return (
        <div role="alert" className="panel" style={{ borderColor: 'rgba(239,68,68,0.4)' }}>
          <h2>Something went wrong.</h2>
          <div className="muted" style={{ fontSize: 13 }}>An unexpected error occurred in the UI. Try reloading the page.</div>
        </div>
      )
    }
    return this.props.children
  }
}
