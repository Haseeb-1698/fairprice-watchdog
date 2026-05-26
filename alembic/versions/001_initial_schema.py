"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-05-26 15:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Create scans table
    op.create_table(
        'scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Create listings table
    op.create_table(
        'listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('advertised_price', sa.Float(), nullable=False),
        sa.Column('final_price', sa.Float(), nullable=False),
        sa.Column('location_state', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
    )
    
    # Create fees table
    op.create_table(
        'fees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fee_name', sa.String(), nullable=False),
        sa.Column('fee_amount', sa.Float(), nullable=False),
        sa.Column('fee_type', sa.String(), nullable=False),
        sa.Column('is_junk_fee', sa.Boolean(), nullable=False),
        sa.Column('ftc_clause', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
    )
    
    # Create evidence_snapshots table
    op.create_table(
        'evidence_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('sha256_hash', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
    )
    
    # Create complaints table
    op.create_table(
        'complaints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('complaint_type', sa.String(), nullable=False),
        sa.Column('pdf_path', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
    )
    
    # Create fee_taxonomy table with vector embedding
    op.create_table(
        'fee_taxonomy',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fee_type', sa.String(), nullable=False, unique=True),
        sa.Column('ftc_clause', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_scans_status', 'scans', ['status'])
    op.create_index('ix_scans_created_at', 'scans', ['created_at'])
    op.create_index('ix_listings_scan_id', 'listings', ['scan_id'])
    op.create_index('ix_fees_listing_id', 'fees', ['listing_id'])
    op.create_index('ix_fees_is_junk_fee', 'fees', ['is_junk_fee'])
    op.create_index('ix_evidence_snapshots_scan_id', 'evidence_snapshots', ['scan_id'])
    op.create_index('ix_complaints_scan_id', 'complaints', ['scan_id'])
    op.create_index('ix_fee_taxonomy_fee_type', 'fee_taxonomy', ['fee_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_fee_taxonomy_fee_type', table_name='fee_taxonomy')
    op.drop_index('ix_complaints_scan_id', table_name='complaints')
    op.drop_index('ix_evidence_snapshots_scan_id', table_name='evidence_snapshots')
    op.drop_index('ix_fees_is_junk_fee', table_name='fees')
    op.drop_index('ix_fees_listing_id', table_name='fees')
    op.drop_index('ix_listings_scan_id', table_name='listings')
    op.drop_index('ix_scans_created_at', table_name='scans')
    op.drop_index('ix_scans_status', table_name='scans')
    
    # Drop tables
    op.drop_table('fee_taxonomy')
    op.drop_table('complaints')
    op.drop_table('evidence_snapshots')
    op.drop_table('fees')
    op.drop_table('listings')
    op.drop_table('scans')
    
    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS vector;')

# Made with Bob
