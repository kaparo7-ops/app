from alembic import op
import sqlalchemy as sa

revision = "20250913_tender_ai_intake"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'tender_files',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tender_id', sa.Integer, sa.ForeignKey('tenders.id'), index=True),
        sa.Column('filename', sa.String(260)),
        sa.Column('mime', sa.String(100)),
        sa.Column('size', sa.Integer),
        sa.Column('storage_key', sa.String(400)),
        sa.Column('uploaded_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.text('now()')),
    )

    op.create_table(
        'tender_ai_analysis',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tender_id', sa.Integer, sa.ForeignKey('tenders.id'), index=True),
        sa.Column('file_id', sa.Integer, sa.ForeignKey('tender_files.id'), nullable=True),
        sa.Column('model', sa.String(100)),
        sa.Column('summary_ar', sa.Text),
        sa.Column('summary_en', sa.Text),
        sa.Column('requirements_tech_json', sa.Text),
        sa.Column('requirements_fin_json', sa.Text),
        sa.Column('questions_json', sa.Text),
        sa.Column('raw_json', sa.Text),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )

def downgrade():
    op.drop_table('tender_ai_analysis')
    op.drop_table('tender_files')
