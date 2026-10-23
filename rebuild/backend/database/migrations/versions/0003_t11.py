"""T11 registry lifecycle, trusted inventory and secure self-service claiming."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_t11"
down_revision = "0002_t10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('device_configurations',
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('revision', sa.BigInteger(), nullable=False),
    sa.Column('document', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('digest', sa.String(length=64), nullable=False),
    sa.Column('confirmed_revision', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("length(digest) = 64 AND jsonb_typeof(document) = 'object'", name='configuration_content'),
    sa.CheckConstraint('revision >= 1 AND confirmed_revision BETWEEN 0 AND revision', name='configuration_revision'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('device_id')
    )
    op.create_table('device_inventory',
    sa.Column('external_id', sa.String(length=15), nullable=False),
    sa.Column('certificate', sa.Text(), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('key_fingerprint', sa.String(length=64), nullable=False),
    sa.Column('claim_hash', sa.String(length=64), nullable=True),
    sa.Column('device_id', sa.Uuid(), nullable=True),
    sa.Column('prepared_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("external_id ~ '^BB-[0-9A-F]{12}$'", name='inventory_device_id'),
    sa.CheckConstraint('length(fingerprint) = 64 AND length(key_fingerprint) = 64 AND (claim_hash IS NULL OR length(claim_hash) = 64)', name='inventory_hashes'),
    sa.CheckConstraint('verified_at IS NULL OR device_id IS NOT NULL', name='inventory_verification'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('external_id'),
    sa.UniqueConstraint('claim_hash'),
    sa.UniqueConstraint('key_fingerprint'),
    sa.UniqueConstraint('device_id'),
    sa.UniqueConstraint('fingerprint')
    )
    op.create_table('device_claims',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('external_id', sa.String(length=15), nullable=False),
    sa.Column('hatchery_id', sa.Uuid(), nullable=False),
    sa.Column('tank_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('state', sa.String(length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint("state IN ('pending_proof','awaiting_confirmation','complete','expired','cancelled')", name='claim_state'),
    sa.CheckConstraint('expires_at > created_at', name='claim_lifetime'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['external_id'], ['device_inventory.external_id'], ),
    sa.ForeignKeyConstraint(['hatchery_id'], ['hatcheries.id'], ),
    sa.ForeignKeyConstraint(['tank_id', 'hatchery_id'], ['tanks.id', 'tanks.hatchery_id'], name='claim_tank_owner'),
    sa.ForeignKeyConstraint(['user_id'], ['user_identities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_claims_external_id'), 'device_claims', ['external_id'], unique=False)
    op.create_index(op.f('ix_device_claims_hatchery_id'), 'device_claims', ['hatchery_id'], unique=False)
    op.create_index('one_pending_claim_per_device', 'device_claims', ['external_id'], unique=True, postgresql_where=sa.text("state = 'pending_proof'"))
    op.create_table('registry_audit',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('actor_type', sa.String(length=16), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('hatchery_id', sa.Uuid(), nullable=True),
    sa.Column('external_id', sa.String(length=15), nullable=True),
    sa.Column('resource_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=48), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint("actor_type IN ('owner','operator','device')", name='registry_actor'),
    sa.ForeignKeyConstraint(['external_id'], ['device_inventory.external_id'], ),
    sa.ForeignKeyConstraint(['hatchery_id'], ['hatcheries.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user_identities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_registry_audit_hatchery_id'), 'registry_audit', ['hatchery_id'], unique=False)
    op.create_table('device_challenges',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('external_id', sa.String(length=15), nullable=False),
    sa.Column('purpose', sa.String(length=8), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('claim_id', sa.Uuid(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name='challenge_payload'),
    sa.CheckConstraint("purpose IN ('sync','confirm')", name='challenge_purpose'),
    sa.ForeignKeyConstraint(['claim_id'], ['device_claims.id'], ),
    sa.ForeignKeyConstraint(['external_id'], ['device_inventory.external_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_challenges_external_id'), 'device_challenges', ['external_id'], unique=False)
    op.add_column('devices', sa.Column('display_name', sa.String(length=200), nullable=True))
    op.add_column('devices', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('devices', sa.Column('version', sa.Integer(), server_default='1', nullable=False))
    op.add_column('tanks', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tanks', sa.Column('version', sa.Integer(), server_default='1', nullable=False))
    op.create_check_constraint('tank_version', 'tanks', 'version >= 1')
    op.create_check_constraint('device_version', 'devices', 'version >= 1')
    op.create_check_constraint('device_name', 'devices', 'display_name IS NULL OR length(trim(display_name)) BETWEEN 1 AND 200')
    op.create_foreign_key('claim_device_owner', 'device_claims', 'devices', ['device_id', 'hatchery_id'], ['id', 'hatchery_id'])
    op.execute("""
        CREATE FUNCTION t11_immutable_audit() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Registry audit is append-only' USING ERRCODE = '23514';
        END $$
    """)
    op.execute("""
        CREATE TRIGGER immutable_registry_audit BEFORE UPDATE OR DELETE ON registry_audit
        FOR EACH ROW EXECUTE FUNCTION t11_immutable_audit()
    """)


def downgrade():
    op.drop_constraint('tank_version', 'tanks', type_='check')
    op.drop_constraint('device_version', 'devices', type_='check')
    op.drop_constraint('device_name', 'devices', type_='check')
    op.drop_constraint('claim_device_owner', 'device_claims', type_='foreignkey')
    op.execute('DROP TRIGGER immutable_registry_audit ON registry_audit')
    op.execute('DROP FUNCTION t11_immutable_audit()')
    op.drop_column('tanks', 'version')
    op.drop_column('tanks', 'archived_at')
    op.drop_column('devices', 'version')
    op.drop_column('devices', 'archived_at')
    op.drop_column('devices', 'display_name')
    op.drop_index(op.f('ix_device_challenges_external_id'), table_name='device_challenges')
    op.drop_table('device_challenges')
    op.drop_index(op.f('ix_registry_audit_hatchery_id'), table_name='registry_audit')
    op.drop_table('registry_audit')
    op.drop_index('one_pending_claim_per_device', table_name='device_claims', postgresql_where=sa.text("state = 'pending_proof'"))
    op.drop_index(op.f('ix_device_claims_hatchery_id'), table_name='device_claims')
    op.drop_index(op.f('ix_device_claims_external_id'), table_name='device_claims')
    op.drop_table('device_claims')
    op.drop_table('device_inventory')
    op.drop_table('device_configurations')
