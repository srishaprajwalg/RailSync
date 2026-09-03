"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-02 21:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Corridors
    op.create_table(
        'corridors',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1024), nullable=True),
        sa.Column('total_length_km', sa.Float(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_corridors_code', 'corridors', ['code'], unique=True)

    # 2. Sections
    op.create_table(
        'sections',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('start_chainage', sa.Float(), nullable=False),
        sa.Column('end_chainage', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(length=16), nullable=False, server_default='BOTH'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sections_corridor_id', 'sections', ['corridor_id'])
    op.create_index('ix_sections_corridor_chainage', 'sections', ['corridor_id', 'start_chainage', 'end_chainage'])

    # 3. Stations
    op.create_table(
        'stations',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('section_id', sa.String(length=64), nullable=True),
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('chainage_km', sa.Float(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stations_code', 'stations', ['code'])
    op.create_index('ix_stations_chainage_km', 'stations', ['chainage_km'])
    op.create_index('ix_stations_section_id', 'stations', ['section_id'])

    # 4. Assets
    op.create_table(
        'assets',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('asset_code', sa.String(length=64), nullable=False),
        sa.Column('asset_type', sa.String(length=32), nullable=False),
        sa.Column('department', sa.String(length=32), nullable=False),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('section_id', sa.String(length=64), nullable=True),
        sa.Column('station_id', sa.String(length=64), nullable=True),
        sa.Column('start_chainage', sa.Float(), nullable=False),
        sa.Column('end_chainage', sa.Float(), nullable=False),
        sa.Column('installation_date', sa.Date(), nullable=True),
        sa.Column('age_years', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('criticality', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='OPERATIONAL'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assets_asset_code', 'assets', ['asset_code'], unique=True)
    op.create_index('ix_assets_asset_type', 'assets', ['asset_type'])
    op.create_index('ix_assets_department', 'assets', ['department'])
    op.create_index('ix_assets_corridor_id', 'assets', ['corridor_id'])
    op.create_index('ix_assets_section_id', 'assets', ['section_id'])
    op.create_index('ix_assets_station_id', 'assets', ['station_id'])
    op.create_index('ix_assets_start_chainage', 'assets', ['start_chainage'])
    op.create_index('ix_assets_end_chainage', 'assets', ['end_chainage'])
    op.create_index('ix_assets_corridor_chainage', 'assets', ['corridor_id', 'start_chainage', 'end_chainage'])
    op.create_index('ix_assets_dept_type', 'assets', ['department', 'asset_type'])

    # 5. Trains
    op.create_table(
        'trains',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('train_number', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('operator', sa.String(length=64), nullable=True),
        sa.Column('source_type', sa.String(length=32), nullable=False, server_default='REAL'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trains_train_number', 'trains', ['train_number'], unique=True)
    op.create_index('ix_trains_category', 'trains', ['category'])

    # 6. Train Runs
    op.create_table(
        'train_runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('train_id', sa.String(length=64), nullable=False),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('service_date', sa.Date(), nullable=True),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('day_offset', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_train_runs_train_id', 'train_runs', ['train_id'])
    op.create_index('ix_train_runs_corridor_id', 'train_runs', ['corridor_id'])
    op.create_index('ix_train_runs_corridor_direction', 'train_runs', ['corridor_id', 'direction'])

    # 7. Train Movements
    op.create_table(
        'train_movements',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('train_run_id', sa.String(length=64), nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=True),
        sa.Column('station_code', sa.String(length=16), nullable=False),
        sa.Column('arrival_time', sa.String(length=16), nullable=True),
        sa.Column('departure_time', sa.String(length=16), nullable=True),
        sa.Column('arrival_mins', sa.Integer(), nullable=False),
        sa.Column('departure_mins', sa.Integer(), nullable=False),
        sa.Column('chainage_km', sa.Float(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['train_run_id'], ['train_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_train_movements_train_run_id', 'train_movements', ['train_run_id'])
    op.create_index('ix_train_movements_station_id', 'train_movements', ['station_id'])
    op.create_index('ix_train_movements_arrival_mins', 'train_movements', ['arrival_mins'])
    op.create_index('ix_train_movements_departure_mins', 'train_movements', ['departure_mins'])
    op.create_index('ix_train_movements_window', 'train_movements', ['train_run_id', 'arrival_mins', 'departure_mins'])

    # 8. Freight Forecasts
    op.create_table(
        'freight_forecasts',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('start_chainage', sa.Float(), nullable=False),
        sa.Column('end_chainage', sa.Float(), nullable=False),
        sa.Column('earliest_entry_mins', sa.Integer(), nullable=False),
        sa.Column('latest_exit_mins', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.85'),
        sa.Column('forecast_source', sa.String(length=64), nullable=False, server_default='SYNTHETIC_SIMULATION'),
        sa.Column('source_type', sa.String(length=32), nullable=False, server_default='SYNTHETIC'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_freight_forecasts_corridor_id', 'freight_forecasts', ['corridor_id'])
    op.create_index('ix_freight_forecasts_earliest_entry_mins', 'freight_forecasts', ['earliest_entry_mins'])
    op.create_index('ix_freight_forecasts_latest_exit_mins', 'freight_forecasts', ['latest_exit_mins'])
    op.create_index('ix_freight_corridor_time', 'freight_forecasts', ['corridor_id', 'earliest_entry_mins', 'latest_exit_mins'])

    # 9. Maintenance Requests
    op.create_table(
        'maintenance_requests',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=64), nullable=True),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('section_id', sa.String(length=64), nullable=True),
        sa.Column('department', sa.String(length=32), nullable=False),
        sa.Column('request_type', sa.String(length=64), nullable=False),
        sa.Column('defect_type', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('required_by', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='OPEN'),
        sa.Column('severity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('criticality', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('start_chainage', sa.Float(), nullable=False),
        sa.Column('end_chainage', sa.Float(), nullable=False),
        sa.Column('line_direction', sa.String(length=16), nullable=False, server_default='Up'),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('deadline_mins', sa.Integer(), nullable=False, server_default='1440'),
        sa.Column('overdue_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('required_resource', sa.String(length=64), nullable=True),
        sa.Column('priority_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('priority_category', sa.String(length=32), nullable=False, server_default='Low'),
        sa.Column('source_type', sa.String(length=32), nullable=False, server_default='SYNTHETIC'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_maintenance_requests_asset_id', 'maintenance_requests', ['asset_id'])
    op.create_index('ix_maintenance_requests_corridor_id', 'maintenance_requests', ['corridor_id'])
    op.create_index('ix_maintenance_requests_section_id', 'maintenance_requests', ['section_id'])
    op.create_index('ix_maintenance_requests_department', 'maintenance_requests', ['department'])
    op.create_index('ix_maintenance_requests_status', 'maintenance_requests', ['status'])
    op.create_index('ix_maintenance_requests_priority_score', 'maintenance_requests', ['priority_score'])
    op.create_index('ix_maintenance_requests_start_chainage', 'maintenance_requests', ['start_chainage'])
    op.create_index('ix_maintenance_requests_end_chainage', 'maintenance_requests', ['end_chainage'])
    op.create_index('ix_maint_corridor_dept_status', 'maintenance_requests', ['corridor_id', 'department', 'status'])
    op.create_index('ix_maint_chainage', 'maintenance_requests', ['corridor_id', 'start_chainage', 'end_chainage'])

    # 10. Maintenance History
    op.create_table(
        'maintenance_history',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=64), nullable=False),
        sa.Column('maintenance_request_id', sa.String(length=64), nullable=True),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('failure_type', sa.String(length=64), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('failure', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('recurrence', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('team', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_requests.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_maintenance_history_asset_id', 'maintenance_history', ['asset_id'])
    op.create_index('ix_maintenance_history_maintenance_request_id', 'maintenance_history', ['maintenance_request_id'])
    op.create_index('ix_history_asset_time', 'maintenance_history', ['asset_id', 'created_at'])

    # 11. ML Predictions
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('maintenance_request_id', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=64), nullable=True),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False),
        sa.Column('prediction_type', sa.String(length=32), nullable=False),
        sa.Column('prediction', sa.String(length=64), nullable=False),
        sa.Column('probability', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('features_snapshot', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ml_predictions_maintenance_request_id', 'ml_predictions', ['maintenance_request_id'])
    op.create_index('ix_ml_predictions_asset_id', 'ml_predictions', ['asset_id'])
    op.create_index('ix_ml_predictions_model_name', 'ml_predictions', ['model_name'])
    op.create_index('ix_ml_predictions_model_version', 'ml_predictions', ['model_version'])
    op.create_index('ix_ml_predictions_request_model', 'ml_predictions', ['maintenance_request_id', 'model_name', 'model_version'])

    # 12. Priority Decisions
    op.create_table(
        'priority_decisions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('maintenance_request_id', sa.String(length=64), nullable=False),
        sa.Column('priority_score', sa.Integer(), nullable=False),
        sa.Column('priority_category', sa.String(length=32), nullable=False),
        sa.Column('ml_risk_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('severity_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('criticality_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('urgency_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overdue_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('operational_impact_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('engine_version', sa.String(length=32), nullable=False, server_default='v1.0-explainable'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_priority_decisions_maintenance_request_id', 'priority_decisions', ['maintenance_request_id'])

    # 13. Optimization Runs
    op.create_table(
        'optimization_runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('horizon_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('horizon_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('horizon_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('solver', sa.String(length=64), nullable=False, server_default='Google OR-Tools CP-SAT'),
        sa.Column('solver_version', sa.String(length=32), nullable=False, server_default='9.15'),
        sa.Column('objective_version', sa.String(length=32), nullable=False, server_default='v2.0-hierarchical'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='COMPLETED'),
        sa.Column('solve_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metrics_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_optimization_runs_corridor_id', 'optimization_runs', ['corridor_id'])

    # 14. Planned Blocks
    op.create_table(
        'planned_blocks',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('optimization_run_id', sa.String(length=64), nullable=False),
        sa.Column('corridor_id', sa.String(length=64), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_time_mins', sa.Integer(), nullable=False),
        sa.Column('end_time_mins', sa.Integer(), nullable=False),
        sa.Column('start_chainage', sa.Float(), nullable=False),
        sa.Column('end_chainage', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PLANNED'),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['corridor_id'], ['corridors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['optimization_run_id'], ['optimization_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_planned_blocks_optimization_run_id', 'planned_blocks', ['optimization_run_id'])
    op.create_index('ix_planned_blocks_corridor_id', 'planned_blocks', ['corridor_id'])
    op.create_index('ix_planned_blocks_start_time_mins', 'planned_blocks', ['start_time_mins'])
    op.create_index('ix_planned_blocks_end_time_mins', 'planned_blocks', ['end_time_mins'])
    op.create_index('ix_planned_blocks_corridor_time', 'planned_blocks', ['corridor_id', 'start_time_mins', 'end_time_mins'])

    # 15. Block Tasks
    op.create_table(
        'block_tasks',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('block_id', sa.String(length=64), nullable=False),
        sa.Column('maintenance_request_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['block_id'], ['planned_blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_block_tasks_block_id', 'block_tasks', ['block_id'])
    op.create_index('ix_block_tasks_maintenance_request_id', 'block_tasks', ['maintenance_request_id'])

    # 16. Schedule Decisions
    op.create_table(
        'schedule_decisions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('block_id', sa.String(length=64), nullable=False),
        sa.Column('maintenance_request_id', sa.String(length=64), nullable=False),
        sa.Column('selected_start_mins', sa.Integer(), nullable=False),
        sa.Column('selected_end_mins', sa.Integer(), nullable=False),
        sa.Column('why_selected', sa.Text(), nullable=False),
        sa.Column('train_constraints', sa.Text(), nullable=True),
        sa.Column('spatial_constraints', sa.Text(), nullable=True),
        sa.Column('department_coordination', sa.Text(), nullable=True),
        sa.Column('priority_reason', sa.Text(), nullable=True),
        sa.Column('solver_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['block_id'], ['planned_blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_schedule_decisions_block_id', 'schedule_decisions', ['block_id'])
    op.create_index('ix_schedule_decisions_maintenance_request_id', 'schedule_decisions', ['maintenance_request_id'])

    # 17. Maintenance Outcomes
    op.create_table(
        'maintenance_outcomes',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('maintenance_request_id', sa.String(length=64), nullable=False),
        sa.Column('planned_block_id', sa.String(length=64), nullable=True),
        sa.Column('actual_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_start_mins', sa.Integer(), nullable=True),
        sa.Column('actual_end_mins', sa.Integer(), nullable=True),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('completion_status', sa.String(length=32), nullable=False, server_default='COMPLETED'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('failure', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('recurrence', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('train_delay_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trains_impacted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deviation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['planned_block_id'], ['planned_blocks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_maintenance_outcomes_maintenance_request_id', 'maintenance_outcomes', ['maintenance_request_id'])
    op.create_index('ix_maintenance_outcomes_planned_block_id', 'maintenance_outcomes', ['planned_block_id'])


def downgrade() -> None:
    op.drop_table('maintenance_outcomes')
    op.drop_table('schedule_decisions')
    op.drop_table('block_tasks')
    op.drop_table('planned_blocks')
    op.drop_table('optimization_runs')
    op.drop_table('priority_decisions')
    op.drop_table('ml_predictions')
    op.drop_table('maintenance_history')
    op.drop_table('maintenance_requests')
    op.drop_table('freight_forecasts')
    op.drop_table('train_movements')
    op.drop_table('train_runs')
    op.drop_table('trains')
    op.drop_table('assets')
    op.drop_table('stations')
    op.drop_table('sections')
    op.drop_table('corridors')
