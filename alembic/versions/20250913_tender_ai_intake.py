from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '20250913_tender_ai_intake'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1) users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=True),
    )

    # 2) tenders
    op.create_table(
        'tenders',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(255), nullable=True),
    )

    # 3) tender_files (يعتمد على الجداول السابقة)
    op.create_table(
        'tender_files',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tender_id', sa.Integer, sa.ForeignKey('tenders.id')),
        sa.Column('filename', sa.String(260)),
        sa.Column('mime', sa.String(100)),
        sa.Column('size', sa.Integer),
        sa.Column('storage_key', sa.String(400)),
        sa.Column('uploaded_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.text('now()')),
    )

def downgrade():
    op.drop_table('tender_files')
    op.drop_table('tenders')
    op.drop_table('users')
