"""Snapshot CSV, bounded pages and passive checks between batches."""
import csv
import io
from backend.database.models import ReadingHistoryState

METRICS = ('temperature', 'ph', 'turbidity')
COLUMNS = ['origin','id','hatchery_id','tank_id','device_id','binding_id','measured_at','received_at',
    'version','revision_id','voided','created_by','actor_id','changed_at','reason','provenance','notes','instrument']
for metric in METRICS:
    COLUMNS += [metric + suffix for suffix in ('_value','_source','_validity','_sample_age_ms')]
COLUMNS += ['relay_on','relay_mode','relay_reason']


def cell(value):
    if value is None: return ''
    if hasattr(value, 'isoformat'): return value.isoformat()
    if isinstance(value, bool): return str(value).lower()
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) and not isinstance(value, (int,float)) else text


def row(reading):
    result = dict(reading)
    if reading['origin'] == 'device':
        for metric in METRICS:
            sample = reading['telemetry']['readings'][metric]
            for name in ('value','source','validity','sample_age_ms'): result[metric + '_' + name] = sample[name]
        for key, value in reading['telemetry']['relay'].items(): result['relay_' + key] = value
        result['provenance'] = 'device_telemetry'
    else:
        for metric, field in zip(METRICS, ('temperature_c','ph','turbidity_ntu')):
            result[metric + '_value'] = reading[field]
            result[metric + '_source'] = 'operator' if reading[field] is not None else None
    return [cell(result.get(key)) for key in COLUMNS]


def prepare(service, accounts, token, hatchery, actor, tank_id, filters):
    with service.registry.operation(hatchery, actor) as session:
        if tank_id: service.tank(session, hatchery, tank_id)
        position = session.get(ReadingHistoryState, hatchery).last_position
    if filters['since'] and filters['until'] and filters['since'] >= filters['until']:
        from .errors import ReadingsError
        raise ReadingsError(422, 'invalid_time_range')
    def generate():
        output = io.StringIO(newline=''); writer = csv.writer(output)
        def emit(values):
            output.seek(0); output.truncate(0); writer.writerow(values); return output.getvalue()
        yield emit(COLUMNS)
        tank_cursor = None
        while True:
            accounts.authenticate(token, touch=False).require_hatchery(hatchery)
            if tank_id:
                tanks, following = [dict(id=tank_id)], None
            else:
                page = service.registry.tanks(hatchery, actor, 100, tank_cursor, True)
                tanks, following = page['items'], page['next_cursor']
            for tank in tanks:
                cursor = None
                while True:
                    accounts.authenticate(token, touch=False).require_hatchery(hatchery)
                    page = service.history(hatchery, tank['id'], actor, limit=200, cursor=cursor, _position=position, **filters)
                    for reading in page['items']: yield emit(row(reading))
                    cursor = page['next_cursor']
                    if not cursor: break
            tank_cursor = following
            if not tank_cursor: break
    return generate()
