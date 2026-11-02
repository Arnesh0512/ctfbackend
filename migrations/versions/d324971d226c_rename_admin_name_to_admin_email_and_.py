"""rename_admin_name_to_admin_email_and_add_role_triggers

Revision ID: d324971d226c
Revises: fc263c31c5dd
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd324971d226c'
down_revision: str | None = 'fc263c31c5dd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Rename column in admins table
    op.alter_column('admins', 'admin_name', new_column_name='admin_email')

    # 2. Trigger for syncing role='admin' to auth.users on insert/update in public.admins
    op.execute("""
    CREATE OR REPLACE FUNCTION public.sync_admin_user_role()
    RETURNS TRIGGER AS $$
    BEGIN
      UPDATE auth.users
      SET raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"role": "admin"}'::jsonb,
          raw_user_meta_data = coalesce(raw_user_meta_data, '{}'::jsonb) || jsonb_build_object('role', 'admin', 'admin_id', NEW.admin_id)
      WHERE id = NEW.admin_id;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_sync_admin_role ON public.admins;")

    op.execute("""
    CREATE TRIGGER trg_sync_admin_role
    AFTER INSERT OR UPDATE ON public.admins
    FOR EACH ROW
    EXECUTE FUNCTION public.sync_admin_user_role();
    """)

    # 3. Trigger for syncing role='team' to auth.users on insert/update in public.teams
    op.execute("""
    CREATE OR REPLACE FUNCTION public.sync_team_user_role()
    RETURNS TRIGGER AS $$
    BEGIN
      UPDATE auth.users
      SET raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"role": "team"}'::jsonb,
          raw_user_meta_data = coalesce(raw_user_meta_data, '{}'::jsonb) || jsonb_build_object('role', 'team', 'team_id', NEW.team_id)
      WHERE id = NEW.team_id;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_sync_team_role ON public.teams;")

    op.execute("""
    CREATE TRIGGER trg_sync_team_role
    AFTER INSERT OR UPDATE ON public.teams
    FOR EACH ROW
    EXECUTE FUNCTION public.sync_team_user_role();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_sync_team_role ON public.teams;")
    op.execute("DROP FUNCTION IF EXISTS public.sync_team_user_role();")
    op.execute("DROP TRIGGER IF EXISTS trg_sync_admin_role ON public.admins;")
    op.execute("DROP FUNCTION IF EXISTS public.sync_admin_user_role();")
    op.alter_column('admins', 'admin_email', new_column_name='admin_name')
