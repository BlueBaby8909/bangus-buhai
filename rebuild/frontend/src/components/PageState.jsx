import { Icon } from './Icon.jsx'

const content = {
  loading: { icon: 'clock', title: 'Loading sample tanks', message: 'This is a paused loading preview. No backend request is running.', action: 'Show sample data' },
  empty: { icon: 'tank', title: 'No sample data available', message: 'There are no tanks or readings in this scenario. Nothing has been removed.', action: 'Restore sample data' },
  error: { icon: 'warning', title: 'Sample data could not be loaded', message: 'This is a simulated error. Retry will restore the local sample fixtures.', action: 'Retry sample data' },
  'not-found': { icon: 'tank', title: 'Page not found', message: 'This tank or page is not available in the frontend preview.' },
}

export function PageState({ kind, onReset }) {
  const state = content[kind] || content['not-found']
  return <section className="page-state" aria-label={state.title} aria-busy={kind === 'loading'}><span className="state-icon"><Icon name={state.icon} /></span><h1>{state.title}</h1><p role={kind === 'error' ? 'alert' : undefined}>{state.message}</p>{onReset ? <button className="button button-primary" onClick={onReset}>{state.action}</button> : <a className="button button-primary" href="#/tanks">Back to tank overview</a>}</section>
}
