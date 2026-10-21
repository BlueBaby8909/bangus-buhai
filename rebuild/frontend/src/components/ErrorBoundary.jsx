import { Component } from 'react'
import { RequestError } from './RequestState.jsx'

export default class ErrorBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <RequestError message="This page could not be displayed. Reload to try again." onRetry={() => window.location.reload()} />
    return this.props.children
  }
}
