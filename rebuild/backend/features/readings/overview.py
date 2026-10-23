"""Tank pages and batched current-binding telemetry; no connectivity inference."""
from .repository import summary_records


def overview(service, hatchery, actor, limit, cursor, include_archived):
    with service.registry.operation(hatchery, actor) as session:
        tanks, following, pairs, configs, inventory, events = summary_records(session, hatchery, limit, cursor, include_archived)
        grouped = {t.id:[] for t in tanks}
        for device, binding in pairs:
            grouped[binding.tank_id].append(dict(id=device.id, device_id=device.external_id,
                display_name=device.display_name, version=device.version, archived_at=device.archived_at,
                hatchery_id=device.hatchery_id, created_at=device.created_at,
                verified=bool(inventory.get(device.id) and inventory[device.id].verified_at),
                binding=service.registry.binding_view(binding), configuration=service.registry.config_view(configs.get(device.id)),
                latest=service.device_view(events[binding.id]) if binding.id in events else None, connectivity='unknown'))
        return dict(items=[dict(tank=service.registry.tank_view(t), devices=grouped[t.id]) for t in tanks],
            next_cursor=following, server_time=service.clock(), temperature_stale_after_ms=60000)
