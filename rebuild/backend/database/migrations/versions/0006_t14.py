"""T14 immutable command intent and retained dispatch/result evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0006_t14'
down_revision = '0005_t13'
branch_labels = depends_on = None


def upgrade():
    op.create_table('relay_commands',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('user_identities.id'), nullable=False),
        sa.Column('request_id', sa.Uuid(), nullable=False),
        sa.Column('hatchery_id', sa.Uuid(), nullable=False),
        sa.Column('tank_id', sa.Uuid(), nullable=False),
        sa.Column('device_id', sa.Uuid(), nullable=False),
        sa.Column('binding_id', sa.Uuid(), nullable=False),
        sa.Column('wire', JSONB(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('timed_out_at', sa.DateTime(timezone=True)),
        sa.Column('terminal_event_id', sa.Uuid(), sa.ForeignKey('device_events.id')),
        sa.ForeignKeyConstraint(['binding_id','device_id','tank_id','hatchery_id'],
            ['bindings.id','bindings.device_id','bindings.tank_id','bindings.hatchery_id'], name='command_binding'),
        sa.UniqueConstraint('actor_id','request_id', name='command_idempotency'),
        sa.CheckConstraint("status IN ('queued','published','accepted','applied','rejected','failed','timed_out')", name='command_status'),
        sa.CheckConstraint("expires_at > issued_at AND jsonb_typeof(wire) = 'object'", name='command_wire'))
    op.create_index('commands_pending','relay_commands',['device_id'], unique=True,
        postgresql_where=sa.text("status IN ('queued','published','accepted')"))
    op.create_table('command_attempts',
        sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('command_id',sa.Uuid(),sa.ForeignKey('relay_commands.id'),nullable=False),
        sa.Column('submitted_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column('published_at',sa.DateTime(timezone=True)))
    op.create_index('ix_command_attempts_command_id','command_attempts',['command_id'])
    op.create_table('command_receipts',
        sa.Column('command_id',sa.Uuid(),sa.ForeignKey('relay_commands.id'),primary_key=True),
        sa.Column('event_id',sa.Uuid(),sa.ForeignKey('device_events.id'),primary_key=True,unique=True))
    op.execute('''CREATE FUNCTION preserve_command_intent() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'command evidence is immutable'; END IF;
      IF (to_jsonb(NEW) - ARRAY['status','timed_out_at','terminal_event_id']) IS DISTINCT FROM
         (to_jsonb(OLD) - ARRAY['status','timed_out_at','terminal_event_id']) THEN
        RAISE EXCEPTION 'command intent is immutable';
      END IF;
      IF OLD.timed_out_at IS NOT NULL AND NEW.timed_out_at IS DISTINCT FROM OLD.timed_out_at THEN
        RAISE EXCEPTION 'timeout evidence is immutable'; END IF;
      IF OLD.terminal_event_id IS NOT NULL AND (NEW.terminal_event_id IS DISTINCT FROM OLD.terminal_event_id OR NEW.status IS DISTINCT FROM OLD.status) THEN
        RAISE EXCEPTION 'terminal evidence is immutable'; END IF;
      RETURN NEW;
    END $$''')
    op.execute('CREATE TRIGGER preserve_command_intent BEFORE UPDATE OR DELETE ON relay_commands FOR EACH ROW EXECUTE FUNCTION preserve_command_intent()')
    op.execute('''CREATE FUNCTION preserve_command_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'command receipt is immutable'; END $$''')
    op.execute('CREATE TRIGGER preserve_command_receipt BEFORE UPDATE OR DELETE ON command_receipts FOR EACH ROW EXECUTE FUNCTION preserve_command_receipt()')
    op.execute('''CREATE FUNCTION preserve_command_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'dispatch evidence is immutable'; END IF;
      IF (to_jsonb(NEW) - 'published_at') IS DISTINCT FROM (to_jsonb(OLD) - 'published_at') OR
         (OLD.published_at IS NOT NULL AND NEW.published_at IS DISTINCT FROM OLD.published_at) THEN
        RAISE EXCEPTION 'dispatch evidence is immutable'; END IF;
      RETURN NEW;
    END $$''')
    op.execute('CREATE TRIGGER preserve_command_attempt BEFORE UPDATE OR DELETE ON command_attempts FOR EACH ROW EXECUTE FUNCTION preserve_command_attempt()')


def downgrade():
    op.drop_table('command_receipts')
    op.drop_table('command_attempts')
    op.drop_table('relay_commands')
    op.execute('DROP FUNCTION preserve_command_receipt()')
    op.execute('DROP FUNCTION preserve_command_intent()')
    op.execute('DROP FUNCTION preserve_command_attempt()')
