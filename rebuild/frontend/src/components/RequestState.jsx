export function LoadingState({ label = 'Loading data' }) {
  return <div role="status" className="flex flex-col gap-3 items-center justify-center min-h-[240px] p-8 text-slate-500">
    <span aria-hidden="true" className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
    <span>{label}…</span>
  </div>
}

export function RequestError({ message, onRetry }) {
  return <div role="alert" className="flex flex-col items-center gap-4 text-center p-8 text-slate-600">
    <p>{message || 'Unable to load data.'}</p>
    {onRetry && <button type="button" onClick={onRetry} className="bg-sky-600 text-white font-bold rounded-full px-6 py-3 hover:bg-sky-700">Try again</button>}
  </div>
}
