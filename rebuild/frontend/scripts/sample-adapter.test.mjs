import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { api, resetSamples, setScenario } from '../src/data/sampleClient.js'
import { sampleLogsCsv } from '../src/api/exportCsv.js'
import { createDataClient, DataClientError, dataMethods } from '../src/services/createDataClient.js'
import { configureDataSource, api as configuredApi, getDataMode, getScenario, setScenario as previewScenario } from '../src/services/dataSource.js'
import { phProvenanceLabel } from '../src/presentation.js'

test('provider validates operations and forwards arguments with provider context', async()=>{
  assert.throws(()=>createDataClient({}), /missing methods/)
  const provider=Object.fromEntries(dataMethods.map(method=>[method, async()=>null]))
  provider.marker='backend'
  provider.listWaterLogs=function(...args){ return { marker:this.marker,args } }
  assert.deepEqual(await createDataClient(provider).listWaterLogs('tank-a',{limit:48}),{marker:'backend',args:['tank-a',{limit:48}]})
})

test('backend errors preserve metadata and never fall back to samples or preview controls',async()=>{
  const provider=Object.fromEntries(dataMethods.map(method=>[method, async()=>{throw Object.assign(new Error('Unavailable'),{status:503,code:'unavailable'})}]))
  configureDataSource({mode:'backend',provider,preview:{setScenario(){throw new Error('Sample controls must not run')}}})
  assert.equal(getDataMode(),'backend')
  assert.equal(getScenario(),'backend')
  previewScenario('ready')
  await assert.rejects(configuredApi.listTanks(),error=>error instanceof DataClientError && error.status===503 && error.code==='unavailable')
})

test('pH provenance distinguishes measured, default, estimated and unknown values',()=>{
  assert.equal(phProvenanceLabel('measured'),'Measured pH')
  assert.match(phProvenanceLabel('default'),/not measured/)
  assert.match(phProvenanceLabel('estimated'),/not measured/)
  assert.equal(phProvenanceLabel(undefined),'pH source unavailable')
})

afterEach(resetSamples)

test('invalid readings stay unavailable and valid zero survives display/export', async()=>{
  setScenario('invalid')
  const {latest_water_log:log}=await api.getTankSummary('nursery-01')
  assert.equal(log.temperature,null)
  assert.equal(log.pH,null)
  assert.equal(log.turbidity,0)
  assert.equal(await api.getLatestPrediction('nursery-01'),null)
  const csv=sampleLogsCsv([log])
  assert.match(csv,/"default","0"/)
  assert.doesNotMatch(csv,/NaN|undefined/)
})

test('sample forecasts carry estimated pH and exact fictional horizon times, unavailable for historical data',async()=>{
  const prediction=await api.getLatestPrediction('nursery-01')
  assert.equal(prediction.sample_only,true)
  assert.equal(prediction.ph_provenance,'estimated')
  for(const hour of [1,2,3,4]) assert.equal(Date.parse(prediction[`target_${hour}h`])-Date.parse(prediction.predicted_from),hour*3600000)
  for(const scenario of ['offline','stale','missing','invalid']){
    setScenario(scenario)
    assert.equal(await api.getLatestPrediction('nursery-01'),null,scenario)
  }
})

test('sample mutations are reversible and do not reuse another device identity',async()=>{
  const tank=await api.createTank({name:'Sample QA',volume_ml:10000,growth_stage:'larvae'})
  await api.updateTank(tank.id,{name:'Renamed'})
  assert.equal((await api.getTankSummary(tank.id)).tank.name,'Renamed')
  setScenario('offline')
  const devices=await api.listDevices()
  assert.equal(new Set(devices.map(device=>device.id)).size,devices.length)
  await api.deleteTank(tank.id)
  assert.equal((await api.listTanks()).length,4)
  resetSamples()
  assert.equal((await api.listTanks())[0].name,'Nursery 01')
})

test('CSV quotes embedded commas/quotes and includes sample/provenance/time metadata',async()=>{
  const {latest_water_log:log}=await api.getTankSummary('nursery-01')
  const csv=sampleLogsCsv([{...log,id:'record, "quoted"'}])
  assert.match(csv,/"record, ""quoted"""/)
  assert.match(csv,/"SAMPLE ONLY"/)
  assert.match(csv,/"pH provenance"/)
  assert.match(csv,/"2026-10-20T01:29:40.000Z"/)
  assert.equal(csv.split('\r\n').length,2)
})
