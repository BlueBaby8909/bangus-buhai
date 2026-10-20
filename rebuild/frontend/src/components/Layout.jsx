import { Icon } from './Icon.jsx'
import tankIcon from '../assets/original/tanks.svg'
import dashboardIcon from '../assets/original/dashboard.svg'

export function Layout({ route, mainRef, navigationTanks, children }) {
  const title = route.page === 'overview' ? 'Tanks'
    : navigationTanks.find((tank) => tank.id === route.id)?.name || 'Tank monitoring'
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content" onClick={(event) => {
        event.preventDefault()
        mainRef.current?.focus()
      }}>Skip to main content</a>
      <aside className="sidebar">
        <a className="brand" href="#/tanks" aria-label="Bangus Buhai tank overview">
          <span className="brand-symbol">B</span><span>Bangus BuhAI</span>
        </a>
        <nav aria-label="Main navigation">
          <p className="nav-caption">WORKSPACE</p>
          <a className="nav-link" href="#/tanks" aria-label="Tank overview"
            aria-current={route.page === 'overview' ? 'page' : undefined}>
            <img src={dashboardIcon} alt="" /><span className="desktop-nav-label">Tank overview</span><span className="mobile-nav-label">Tanks</span>
          </a>
          <p className="nav-caption tank-nav-caption">SAMPLE TANKS</p>
          <ul className="tank-nav">
            {navigationTanks.map((tank, index) => (
              <li key={tank.id}>
                <a className="nav-link" href={`#/tanks/${tank.id}`} aria-label={tank.name}
                  aria-current={route.id === tank.id ? 'page' : undefined}>
                  <img src={tankIcon} alt="" />
                  <span className="desktop-nav-label">{tank.name}</span>
                  <span className="mobile-nav-label">Tank {String(index + 1).padStart(2, '0')}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="sidebar-note"><span className="sample-dot" /> Frontend preview<p>Fictional tanks. No live connection.</p></div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          {route.page === 'tank' ? (
            <a className="header-back" href="#/tanks" aria-label="Back to tank overview"><Icon name="back" /></a>
          ) : <span className="header-brand" aria-hidden="true">B</span>}
          <span className="header-title">{title}</span>
          <span className="workspace-label">Sample</span>
        </header>
        <main id="main-content" tabIndex={-1} ref={mainRef}>{children}</main>
        <footer>Bangus BuhAI <span>Frontend preparation · T16–T18 integration pending</span></footer>
      </div>
    </div>
  )
}
