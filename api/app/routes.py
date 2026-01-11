from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, services
from app.database import get_db
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["scenarios"])

@router.post("/scenario/init", response_model=schemas.ScenarioResponse)
def init_scenario(
    request: schemas.ScenarioInitRequest,
    db: Session = Depends(get_db)
):
    """Initialize new scenario"""
    return services.ScenarioService.init_scenario(db, request)

@router.get("/scenario/{scenario_uuid}", response_model=schemas.ScenarioResponse)
def get_scenario(
    scenario_uuid: str,
    db: Session = Depends(get_db)
):
    """Get scenario details"""
    scenario = services.ScenarioService.get_scenario(db, scenario_uuid)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

@router.get("/prediction/{scenario_uuid}", response_model=schemas.PredictionResponse)
def get_predictions(
    scenario_uuid: str,
    db: Session = Depends(get_db)
):
    """Get predictions for scenario"""
    result = services.ScenarioService.get_predictions(db, scenario_uuid)
    if not result:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return result
