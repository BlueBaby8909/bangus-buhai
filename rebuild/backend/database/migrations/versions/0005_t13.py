"""T13 ingestion receipts and quarantine"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import hashlib
import json
from uuid import UUID, uuid4

revision = '0005_t13'
down_revision = '0004_t12'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('ingestion_quarantine',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('external_id', sa.String(length=15), nullable=False),
    sa.Column('boot_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.BigInteger(), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('digest', sa.String(length=64), nullable=False),
    sa.Column('reason', sa.String(length=64), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint("external_id ~ '^BB-[0-9A-F]{12}$' AND length(digest) = 64", name='quarantine_identity'),
    sa.CheckConstraint("kind IN ('telemetry','command_result') AND jsonb_typeof(payload) = 'object'", name='quarantine_event'),
    sa.CheckConstraint('seq BETWEEN 0 AND 4294967295', name='quarantine_sequence'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_id', 'boot_id', 'seq', 'digest', name='quarantine_candidate')
    )
    op.create_index('quarantine_device', 'ingestion_quarantine', ['external_id'], unique=False)
    op.create_index('quarantine_order', 'ingestion_quarantine', ['received_at', 'id'], unique=False)
    op.create_table('device_configuration_receipts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('binding_id', sa.Uuid(), nullable=True),
    sa.Column('tank_id', sa.Uuid(), nullable=True),
    sa.Column('revision', sa.BigInteger(), nullable=False),
    sa.Column('digest', sa.String(length=64), nullable=False),
    sa.Column('credential_fingerprint', sa.String(length=64), nullable=False),
    sa.Column('document', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("jsonb_typeof(document) = 'object'", name='receipt_document'),
    sa.CheckConstraint('(binding_id IS NULL) = (tank_id IS NULL)', name='receipt_assignment'),
    sa.CheckConstraint('revision >= 1 AND length(digest) = 64 AND length(credential_fingerprint) = 64', name='receipt_identity'),
    sa.ForeignKeyConstraint(['binding_id', 'device_id', 'tank_id', 'hatchery_id'], ['bindings.id', 'bindings.device_id', 'bindings.tank_id', 'bindings.hatchery_id'], name='receipt_binding_identity'),
    sa.ForeignKeyConstraint(['device_id', 'hatchery_id'], ['devices.id', 'devices.hatchery_id'], name='receipt_device_owner'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('device_id', 'revision', name='configuration_receipt_revision')
    )
    op.create_index('receipts_binding', 'device_configuration_receipts', ['binding_id'], unique=False)
    # Capture only the last currently confirmed document. Earlier audit entries
    # do not retain full documents, so cannot prove old configuration contents.
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE device_configurations, device_inventory, devices, bindings IN SHARE ROW EXCLUSIVE MODE'))
    rows = connection.execute(sa.text('''
        SELECT c.*, d.hatchery_id, d.external_id, i.fingerprint
        FROM device_configurations c JOIN devices d ON d.id=c.device_id
        JOIN device_inventory i ON i.device_id=d.id AND i.external_id=d.external_id
        WHERE i.verified_at IS NOT NULL AND c.confirmed_revision=c.revision AND c.confirmed_at IS NOT NULL
    ''')).mappings().all()
    for row in rows:
        document = row['document']
        try:
            binding_id = UUID(document['binding_id']) if document['binding_id'] else None
            tank_id = UUID(document['tank_id']) if document['tank_id'] else None
            expected = dict(schema_version=1, device_id=row['external_id'], hatchery_id=str(row['hatchery_id']),
                binding_id=str(binding_id) if binding_id else None, tank_id=str(tank_id) if tank_id else None,
                archived=document['archived'], revision=row['revision'])
            if (document != expected or type(document['archived']) is not bool or
                    type(document['schema_version']) is not int or type(document['revision']) is not int or
                    (binding_id is None) != (tank_id is None)):
                continue
            canonical = json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
            if hashlib.sha256(canonical.encode('ascii')).hexdigest() != row['digest']:
                continue
            if binding_id and not connection.scalar(sa.text('''SELECT count(*) FROM bindings WHERE
                    id=:binding AND device_id=:device AND tank_id=:tank AND hatchery_id=:hatchery'''),
                    dict(binding=binding_id, device=row['device_id'], tank=tank_id, hatchery=row['hatchery_id'])):
                continue
        except (ValueError, TypeError, KeyError):
            continue
        connection.execute(sa.text('''INSERT INTO device_configuration_receipts
            (id,device_id,hatchery_id,binding_id,tank_id,revision,digest,credential_fingerprint,document,confirmed_at)
            VALUES (:id,:device,:hatchery,:binding,:tank,:revision,:digest,:fingerprint,CAST(:document AS jsonb),:confirmed)'''),
            dict(id=uuid4(), device=row['device_id'], hatchery=row['hatchery_id'], binding=binding_id, tank=tank_id,
                revision=row['revision'], digest=row['digest'], fingerprint=row['fingerprint'], document=canonical,
                confirmed=row['confirmed_at']))
    op.execute('''CREATE FUNCTION t13_immutable_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Ingestion evidence is immutable' USING ERRCODE='23514'; END $$''')
    for table in ('device_configuration_receipts', 'ingestion_quarantine'):
        op.execute(f'''CREATE TRIGGER immutable_ingestion_evidence BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION t13_immutable_evidence()''')

def downgrade():
    op.drop_index('receipts_binding', table_name='device_configuration_receipts')
    op.drop_table('device_configuration_receipts')
    op.drop_index('quarantine_order', table_name='ingestion_quarantine')
    op.drop_index('quarantine_device', table_name='ingestion_quarantine')
    op.drop_table('ingestion_quarantine')
    op.execute('DROP FUNCTION t13_immutable_evidence()')
