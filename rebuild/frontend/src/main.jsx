import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './original/styles/global.css'
import App from './App.jsx'
import { configureApplicationData } from './services/configureApplicationData.js'

configureApplicationData()

createRoot(document.getElementById('root')).render(
  <StrictMode><HashRouter><App /></HashRouter></StrictMode>,
)
