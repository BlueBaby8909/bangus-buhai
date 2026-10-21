import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './styles/global.css'
import App from './App.jsx'
import { configureApplicationData } from './services/configureApplicationData.js'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { RequestError } from './components/RequestState.jsx'

const root = createRoot(document.getElementById('root'))
configureApplicationData().then(() => {
  root.render(<StrictMode><HashRouter><ErrorBoundary><App /></ErrorBoundary></HashRouter></StrictMode>)
}).catch(() => {
  root.render(<RequestError message="The application configuration is invalid. Contact your administrator." />)
})
