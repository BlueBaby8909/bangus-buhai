const paths = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  tank: <><path d="M4 7h16v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3Z" /><path d="M4 12c3-3 5 3 8 0s5 3 8 0M3 3h18" /></>,
  temperature: <><path d="M9 14.5V5a3 3 0 0 1 6 0v9.5a5 5 0 1 1-6 0Z" /><path d="M12 9v9M18 5h3M18 9h2" /></>,
  turbidity: <><path d="M12 2C9 7 5 10 5 15a7 7 0 0 0 14 0c0-5-4-8-7-13Z" /><path d="M8 15h8M9 18h6" /></>,
  ph: <><path d="m9 3 1 7-5 8a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-8 1-7M8 3h8M8 15h8" /></>,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  back: <path d="M19 12H5m5-5-5 5 5 5" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7v1" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  signal: <><path d="M4 9a12 12 0 0 1 16 0M7 12a8 8 0 0 1 10 0M10 15a3 3 0 0 1 4 0" /><circle cx="12" cy="19" r="1" /></>,
  warning: <><path d="m10 4-8 14a2 2 0 0 0 2 3h16a2 2 0 0 0 2-3L14 4a2 2 0 0 0-4 0Z" /><path d="M12 9v5M12 17v1" /></>,
  fish: <><path d="M3 12C8 3 16 3 20 12c-4 9-12 9-17 0Zm0 0L1 6v12l2-6ZM9 6l4-4M9 18l4 4" /><circle cx="16" cy="11" r="1" /></>,
}

export function Icon({ name, className = '' }) {
  return <svg className={`icon ${className}`} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.info}</svg>
}
