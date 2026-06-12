"""enviado_nutri_em nos registros do paciente

Revision ID: b8c4e1f2a901
Revises: 3a53e39a7183
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8c4e1f2a901'
down_revision = '3a53e39a7183'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('refeicoes', sa.Column('enviado_nutri_em', sa.DateTime(), nullable=True))
    op.add_column('sono', sa.Column('enviado_nutri_em', sa.DateTime(), nullable=True))
    op.add_column('exercicios', sa.Column('enviado_nutri_em', sa.DateTime(), nullable=True))
    op.create_index('ix_refeicoes_enviado_nutri_em', 'refeicoes', ['enviado_nutri_em'])
    op.create_index('ix_sono_enviado_nutri_em', 'sono', ['enviado_nutri_em'])
    op.create_index('ix_exercicios_enviado_nutri_em', 'exercicios', ['enviado_nutri_em'])
    # Registros antigos: considerar já enviados ao nutricionista
    op.execute("UPDATE refeicoes SET enviado_nutri_em = criado_em WHERE enviado_nutri_em IS NULL")
    op.execute("UPDATE sono SET enviado_nutri_em = criado_em WHERE enviado_nutri_em IS NULL")
    op.execute("UPDATE exercicios SET enviado_nutri_em = criado_em WHERE enviado_nutri_em IS NULL")


def downgrade():
    op.drop_index('ix_exercicios_enviado_nutri_em', table_name='exercicios')
    op.drop_index('ix_sono_enviado_nutri_em', table_name='sono')
    op.drop_index('ix_refeicoes_enviado_nutri_em', table_name='refeicoes')
    op.drop_column('exercicios', 'enviado_nutri_em')
    op.drop_column('sono', 'enviado_nutri_em')
    op.drop_column('refeicoes', 'enviado_nutri_em')
