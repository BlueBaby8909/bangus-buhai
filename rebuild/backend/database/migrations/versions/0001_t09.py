"""T09 ownership, bindings and event identity. Frozen schema, not live model imports."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_t09"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('hatcheries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(trim(name)) BETWEEN 1 AND 200', name='hatchery_name'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_identities',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('devices',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('external_id', sa.String(length=15), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("external_id ~ '^BB-[0-9A-F]{12}$'", name='canonical_device_id'),
    sa.ForeignKeyConstraint(['hatchery_id'], ['hatcheries.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_id'),
    sa.UniqueConstraint('id', 'hatchery_id', name='device_owner')
    )
    op.create_index(op.f('ix_devices_hatchery_id'), 'devices', ['hatchery_id'], unique=False)
    op.create_table('memberships',
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.CheckConstraint("role IN ('admin','operator','viewer')", name='membership_role'),
    sa.ForeignKeyConstraint(['hatchery_id'], ['hatcheries.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user_identities.id'], ),
    sa.PrimaryKeyConstraint('hatchery_id', 'user_id')
    )
    op.create_table('tanks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(trim(name)) BETWEEN 1 AND 200', name='tank_name'),
    sa.ForeignKeyConstraint(['hatchery_id'], ['hatcheries.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'hatchery_id', name='tank_owner')
    )
    op.create_index(op.f('ix_tanks_hatchery_id'), 'tanks', ['hatchery_id'], unique=False)
    op.create_table('bindings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('tank_id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('ended_at IS NULL OR ended_at > started_at', name='binding_interval'),
    sa.ForeignKeyConstraint(['device_id', 'hatchery_id'], ['devices.id', 'devices.hatchery_id'], name='binding_device_owner'),
    sa.ForeignKeyConstraint(['tank_id', 'hatchery_id'], ['tanks.id', 'tanks.hatchery_id'], name='binding_tank_owner'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'device_id', 'tank_id', 'hatchery_id', name='binding_identity')
    )
    op.create_index('bindings_tank', 'bindings', ['tank_id'], unique=False)
    op.create_index('one_active_binding_per_device', 'bindings', ['device_id'], unique=True, postgresql_where=sa.text('ended_at IS NULL'))
    op.create_table('device_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('binding_id', sa.Uuid(), nullable=False),
    sa.Column('tank_id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('boot_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.BigInteger(), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('time_quality', sa.String(length=16), nullable=False),
    sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('payload', postgresql.JSONB(), nullable=False),
    sa.CheckConstraint("(captured_at IS NOT NULL) = (time_quality = 'synchronized')", name='event_capture_time'),
    sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name='event_payload_object'),
    sa.CheckConstraint("kind IN ('telemetry','command_result')", name='event_kind'),
    sa.CheckConstraint("time_quality IN ('synchronized','unsynchronized')", name='event_time_quality'),
    sa.CheckConstraint('seq BETWEEN 0 AND 4294967295', name='event_sequence'),
    sa.ForeignKeyConstraint(['binding_id', 'device_id', 'tank_id', 'hatchery_id'], ['bindings.id', 'bindings.device_id', 'bindings.tank_id', 'bindings.hatchery_id'], name='event_binding_identity'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('device_id', 'boot_id', 'seq', name='device_event_identity')
    )
    op.create_index('events_tank_captured', 'device_events', ['tank_id', 'captured_at', 'id'], unique=False)
    op.create_index('events_tank_received', 'device_events', ['tank_id', 'received_at', 'id'], unique=False)
    op.execute("""
        CREATE FUNCTION t09_immutable_event() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Device events are append-only' USING ERRCODE = '23514';
        END $$
    """)
    op.execute("""
        CREATE TRIGGER immutable_device_event BEFORE UPDATE OR DELETE ON device_events
        FOR EACH ROW EXECUTE FUNCTION t09_immutable_event()
    """)
    op.execute("""
        CREATE FUNCTION t09_binding_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Binding history is retained' USING ERRCODE = '23514';
            END IF;
            IF ROW(NEW.id, NEW.device_id, NEW.tank_id, NEW.hatchery_id, NEW.started_at)
                IS DISTINCT FROM ROW(OLD.id, OLD.device_id, OLD.tank_id, OLD.hatchery_id, OLD.started_at)
                OR OLD.ended_at IS NOT NULL OR NEW.ended_at IS NULL THEN
                RAISE EXCEPTION 'Only closing an active binding is permitted' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER retain_binding_history BEFORE UPDATE OR DELETE ON bindings
        FOR EACH ROW EXECUTE FUNCTION t09_binding_history()
    """)
    op.execute("""
        CREATE FUNCTION t09_resource_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF ROW(NEW.id, NEW.hatchery_id) IS DISTINCT FROM ROW(OLD.id, OLD.hatchery_id)
                OR (to_jsonb(NEW)->'external_id') IS DISTINCT FROM (to_jsonb(OLD)->'external_id') THEN
                RAISE EXCEPTION 'Resource identity and ownership are immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    """)
    for table in ('tanks', 'devices'):
        op.execute(f"""
            CREATE TRIGGER retain_resource_identity BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION t09_resource_identity()
        """)


def downgrade():
    op.drop_table('device_events')
    op.drop_table('bindings')
    op.drop_table('tanks')
    op.drop_table('memberships')
    op.drop_table('devices')
    op.drop_table('user_identities')
    op.drop_table('hatcheries')
    op.execute('DROP FUNCTION t09_immutable_event()')
    op.execute('DROP FUNCTION t09_binding_history()')
    op.execute('DROP FUNCTION t09_resource_identity()')
