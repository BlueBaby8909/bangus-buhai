// Single application wiring point. Replace this provider when contracts/auth are accepted.
import { configureDataSource } from './dataSource.js'
import * as samples from '../data/sampleClient.js'

export function configureApplicationData() {
  configureDataSource({ mode: 'sample', provider: samples.api, preview: samples })
}
