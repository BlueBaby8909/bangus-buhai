export function sampleLogsCsv(logs) {
  const cell=(value)=>`"${String(value ?? '').replace(/"/g,'""')}"`
  const number=(value)=>Number.isFinite(value)?value:''
  const rows=[['Source','ID','Tank ID','Recorded at (UTC)','Temperature (°C)','pH','pH provenance','Turbidity (NTU)','Reading freshness','Device connection','Relay state']]
  for(const log of logs) rows.push([log.sample_only === true ? 'SAMPLE ONLY' : 'Backend',log.id,log.tank_id,log.recorded_at,number(log.temperature),number(log.pH),log.ph_provenance,number(log.turbidity),log.freshness,log.connection,typeof log.relay_on==='boolean'?(log.relay_on?'ON':'OFF'):'Unknown'])
  return rows.map((row)=>row.map(cell).join(',')).join('\r\n')
}
