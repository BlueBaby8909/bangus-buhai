"""T12 reliable history and manual measurements"""
from alembic import op
import sqlalchemy as sa


revision = '0004_t12'
down_revision = '0003_t11'
branch_labels = None
depends_on = None

def upgrade():
    # Hold writers while deriving journal references from the existing records.
    op.execute('LOCK TABLE hatcheries, device_events IN SHARE ROW EXCLUSIVE MODE')
    op.create_unique_constraint('event_history_identity', 'device_events', ['id', 'hatchery_id', 'tank_id'])
    op.create_table('reading_history_state',
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('last_position', sa.BigInteger(), server_default='0', nullable=False),
    sa.CheckConstraint('last_position >= 0', name='history_position'),
    sa.ForeignKeyConstraint(['hatchery_id'], ['hatcheries.id'], ),
    sa.PrimaryKeyConstraint('hatchery_id')
    )
    op.create_table('manual_readings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('tank_id', sa.Uuid(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.Uuid(), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['user_identities.id'], ),
    sa.ForeignKeyConstraint(['tank_id', 'hatchery_id'], ['tanks.id', 'tanks.hatchery_id'], name='manual_tank_owner'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hatchery_id', 'created_by', 'request_id', name='manual_request_identity'),
    sa.UniqueConstraint('id', 'hatchery_id', 'tank_id', name='manual_identity')
    )
    op.create_table('manual_reading_revisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('reading_id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('tank_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('temperature_c', sa.Double(), nullable=True),
    sa.Column('ph', sa.Double(), nullable=True),
    sa.Column('turbidity_ntu', sa.Double(), nullable=True),
    sa.Column('notes', sa.String(length=2000), nullable=True),
    sa.Column('instrument', sa.String(length=200), nullable=True),
    sa.Column('voided', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=False),
    sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=True),
    sa.CheckConstraint("ph IS NULL OR (ph > '-Infinity'::float8 AND ph < 'Infinity'::float8)", name='manual_finite_ph'),
    sa.CheckConstraint("temperature_c IS NULL OR (temperature_c > '-Infinity'::float8 AND temperature_c < 'Infinity'::float8)", name='manual_finite_temperature_c'),
    sa.CheckConstraint("turbidity_ntu IS NULL OR (turbidity_ntu > '-Infinity'::float8 AND turbidity_ntu < 'Infinity'::float8)", name='manual_finite_turbidity_ntu'),
    sa.CheckConstraint('(version = 1 AND reason IS NULL AND NOT voided) OR (version > 1 AND reason IS NOT NULL AND length(trim(reason)) BETWEEN 1 AND 500)', name='manual_reason'),
    sa.CheckConstraint('temperature_c IS NOT NULL OR ph IS NOT NULL OR turbidity_ntu IS NOT NULL', name='manual_has_measurement'),
    sa.CheckConstraint('version >= 1', name='manual_version'),
    sa.ForeignKeyConstraint(['actor_id'], ['user_identities.id'], ),
    sa.ForeignKeyConstraint(['reading_id', 'hatchery_id', 'tank_id'], ['manual_readings.id', 'manual_readings.hatchery_id', 'manual_readings.tank_id'], name='revision_reading_owner'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'hatchery_id', 'tank_id', name='revision_history_identity'),
    sa.UniqueConstraint('reading_id', 'version', name='manual_revision_version')
    )
    op.create_index('manual_revisions_tank', 'manual_reading_revisions', ['tank_id', 'reading_id', 'version'], unique=False)
    op.create_table('reading_changes',
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.BigInteger(), nullable=False),
    sa.Column('tank_id', sa.Uuid(), nullable=False),
    sa.Column('device_event_id', sa.Uuid(), nullable=True),
    sa.Column('manual_revision_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint('(device_event_id IS NULL) <> (manual_revision_id IS NULL)', name='history_one_origin'),
    sa.CheckConstraint('position > 0', name='history_positive_position'),
    sa.ForeignKeyConstraint(['device_event_id', 'hatchery_id', 'tank_id'], ['device_events.id', 'device_events.hatchery_id', 'device_events.tank_id'], name='history_event_owner'),
    sa.ForeignKeyConstraint(['hatchery_id'], ['reading_history_state.hatchery_id'], ),
    sa.ForeignKeyConstraint(['manual_revision_id', 'hatchery_id', 'tank_id'], ['manual_reading_revisions.id', 'manual_reading_revisions.hatchery_id', 'manual_reading_revisions.tank_id'], name='history_revision_owner'),
    sa.PrimaryKeyConstraint('hatchery_id', 'position'),
    sa.UniqueConstraint('device_event_id'),
    sa.UniqueConstraint('manual_revision_id')
    )
    op.create_index('reading_changes_tank', 'reading_changes', ['tank_id', 'position'], unique=False)
    op.execute('INSERT INTO reading_history_state (hatchery_id) SELECT id FROM hatcheries')
    op.execute('''
        INSERT INTO reading_changes (hatchery_id, position, tank_id, device_event_id)
        SELECT hatchery_id, row_number() OVER (PARTITION BY hatchery_id ORDER BY received_at, id), tank_id, id
        FROM device_events WHERE kind = 'telemetry'
    ''')
    op.execute('''
        UPDATE reading_history_state s SET last_position = c.position FROM
        (SELECT hatchery_id, max(position) AS position FROM reading_changes GROUP BY hatchery_id) c
        WHERE s.hatchery_id = c.hatchery_id
    ''')
    op.execute('''
        CREATE FUNCTION t12_initialize_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO reading_history_state (hatchery_id) VALUES (NEW.id);
            RETURN NEW;
        END $$
    ''')
    op.execute('''CREATE TRIGGER initialize_reading_history AFTER INSERT ON hatcheries
        FOR EACH ROW EXECUTE FUNCTION t12_initialize_history()''')
    op.execute('''
        CREATE FUNCTION t12_record_change() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE next_position bigint;
        BEGIN
            IF TG_TABLE_NAME = 'device_events' AND to_jsonb(NEW)->>'kind' <> 'telemetry' THEN
                RETURN NEW;
            END IF;
            UPDATE reading_history_state SET last_position = last_position + 1
                WHERE hatchery_id = NEW.hatchery_id RETURNING last_position INTO STRICT next_position;
            INSERT INTO reading_changes (hatchery_id, position, tank_id, device_event_id, manual_revision_id)
                VALUES (NEW.hatchery_id, next_position, NEW.tank_id,
                    CASE WHEN TG_TABLE_NAME = 'device_events' THEN NEW.id END,
                    CASE WHEN TG_TABLE_NAME = 'manual_reading_revisions' THEN NEW.id END);
            RETURN NEW;
        END $$
    ''')
    for table in ('device_events', 'manual_reading_revisions'):
        op.execute(f'''CREATE TRIGGER record_reading_change AFTER INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION t12_record_change()''')
    op.execute('''
        CREATE FUNCTION t12_immutable_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Reading history is immutable' USING ERRCODE = '23514';
        END $$
    ''')
    for table in ('manual_readings', 'manual_reading_revisions', 'reading_changes'):
        op.execute(f'''CREATE TRIGGER immutable_reading_history BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION t12_immutable_history()''')
    op.execute('''
        CREATE FUNCTION t12_revision_order() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE previous_version integer; creator uuid;
        BEGIN
            SELECT created_by INTO STRICT creator FROM manual_readings WHERE id = NEW.reading_id FOR UPDATE;
            SELECT coalesce(max(version), 0) INTO previous_version FROM manual_reading_revisions WHERE reading_id = NEW.reading_id;
            IF NEW.version <> previous_version + 1 OR (NEW.version = 1 AND NEW.actor_id <> creator) THEN
                RAISE EXCEPTION 'Invalid manual revision sequence' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$
    ''')
    op.execute('''CREATE TRIGGER ordered_manual_revision BEFORE INSERT ON manual_reading_revisions
        FOR EACH ROW EXECUTE FUNCTION t12_revision_order()''')

def downgrade():
    op.execute('DROP TRIGGER initialize_reading_history ON hatcheries')
    op.execute('DROP TRIGGER record_reading_change ON device_events')
    op.drop_index('reading_changes_tank', table_name='reading_changes')
    op.drop_table('reading_changes')
    op.drop_constraint('event_history_identity', 'device_events', type_='unique')
    op.drop_index('manual_revisions_tank', table_name='manual_reading_revisions')
    op.drop_table('manual_reading_revisions')
    op.drop_table('manual_readings')
    op.drop_table('reading_history_state')
    for name in ('t12_initialize_history', 't12_record_change', 't12_immutable_history', 't12_revision_order'):
        op.execute(f'DROP FUNCTION {name}()')
