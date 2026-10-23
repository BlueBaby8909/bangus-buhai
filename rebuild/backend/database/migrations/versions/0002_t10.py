"""Operator identities, durable browser sessions and shared login throttling."""
from alembic import op
import sqlalchemy as sa

revision = "0002_t10"
down_revision = "0001_t09"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_identities", sa.Column("provider_issuer", sa.String(512)))
    op.add_column("user_identities", sa.Column("provider_subject", sa.Uuid()))
    op.add_column("user_identities", sa.Column("email", sa.String(320)))
    op.add_column("user_identities", sa.Column("active", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_unique_constraint("user_provider_identity", "user_identities", ["provider_issuer", "provider_subject"])
    op.create_check_constraint("user_provider_pair", "user_identities", "(provider_issuer IS NULL) = (provider_subject IS NULL)")
    op.create_check_constraint("active_user_mapped", "user_identities", "NOT active OR provider_subject IS NOT NULL")
    op.drop_constraint("membership_role", "memberships", type_="check")
    # Explicit owner-approved simplification: keep every user/hatchery association.
    op.execute("UPDATE memberships SET role = 'operator'")
    op.create_check_constraint("membership_role", "memberships", "role = 'operator'")
    op.add_column("memberships", sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_table("auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("provider_session_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_tokens", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("expires_at > created_at", name="auth_session_lifetime"),
        sa.CheckConstraint("length(token_hash) = 64", name="auth_session_hash"))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_table("auth_login_buckets",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.CheckConstraint("attempts BETWEEN 1 AND 11", name="login_bucket_count"))


def downgrade():
    op.drop_table("auth_login_buckets")
    op.drop_table("auth_sessions")
    op.drop_column("memberships", "active")
    op.drop_constraint("membership_role", "memberships", type_="check")
    op.create_check_constraint("membership_role", "memberships", "role IN ('admin','operator','viewer')")
    # Legacy labels intentionally remain operator; original labels cannot be inferred.
    op.drop_constraint("active_user_mapped", "user_identities", type_="check")
    op.drop_constraint("user_provider_pair", "user_identities", type_="check")
    op.drop_constraint("user_provider_identity", "user_identities", type_="unique")
    for column in ("active", "email", "provider_subject", "provider_issuer"):
        op.drop_column("user_identities", column)
