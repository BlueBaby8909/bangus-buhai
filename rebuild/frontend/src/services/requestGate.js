// Ignore responses from superseded requests, including route changes and unmounts.
export function createRequestGate() {
  let revision = 0
  return {
    begin() { const ownRevision = ++revision; return () => revision === ownRevision },
    cancel() { revision += 1 },
  }
}
