import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from database import get_db
import models
import auth
from services.internal_brain import InternalBrain
from services.vector_memory import vector_memory
from services.ai_core import ai_core_service

logger = logging.getLogger(__name__)

router = APIRouter()
brain = InternalBrain()


@router.post("/learn")
async def learn(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Receive learning feedback for an analysis.
    Payload may contain either `analysis_id` or full `analysis` object, plus `result` ('win'/'loss') and optional `profit`.
    """
    analysis_id = payload.get("analysis_id")
    result_flag = payload.get("result")
    profit = float(payload.get("profit", 0.0) or 0.0)

    if result_flag not in ("win", "loss"):
        raise HTTPException(status_code=400, detail="Invalid result value; expected 'win' or 'loss'.")

    analysis_data = None
    if analysis_id:
        analysis_record = db.query(models.Analysis).filter(models.Analysis.id == int(analysis_id)).first()
        if not analysis_record:
            raise HTTPException(status_code=404, detail="Analysis not found")
        try:
            analysis_data = json.loads(analysis_record.result_json or '{}')
        except Exception:
            analysis_data = None
    elif payload.get('analysis'):
        analysis_data = payload.get('analysis')
    else:
        raise HTTPException(status_code=400, detail="Provide analysis_id or analysis payload")

    if not analysis_data or 'details' not in analysis_data:
        raise HTTPException(status_code=400, detail="Analysis details missing")

    # Determine recommendation used during analysis
    main_rec = analysis_data.get('recommendation')
    details = analysis_data.get('details', [])

    # Compute total weight for strategies that supported the recommendation
    supporting = [d for d in details if d.get('vote') == main_rec]
    total_weight = sum([float(d.get('weight', 1.0)) for d in supporting]) or 0.0

    # Update strategy performance: allocate profit proportionally to weights
    for d in supporting:
        sname = d.get('name')
        w = float(d.get('weight', 1.0))
        share = (w / total_weight) * profit if total_weight > 0 else 0.0
        try:
            brain.update_strategy_performance(strategy_name=sname, outcome='win' if result_flag == 'win' else 'loss', profit=share)
        except Exception as e:
            logger.exception(f"Failed to update performance for strategy {sname}: {e}")

    # If analysis_id was provided, mark analysis result_json with learned flag to avoid duplicates
    if analysis_id and analysis_record:
        try:
            obj = analysis_data
            obj['learned_by_ai'] = True
            analysis_record.result_json = json.dumps(obj, ensure_ascii=False)
            db.commit()
        except Exception as e:
            logger.exception(f"Failed to update analysis record {analysis_id}: {e}")
            db.rollback()

        try:
            visual_description = payload.get('visual_description') or analysis_record.description or ''
            vector_memory.store_analysis(analysis_record.id, visual_description, result_flag, db=db)
        except Exception as e:
            logger.exception(f"Failed to store vector memory for analysis {analysis_id}: {e}")

    # تسجيل تجربة التداول في AI core للتعلم
    try:
        ai_core_service.log_trade_experience(
            analysis_id=analysis_id,
            user_id=current_user.id,
            market=analysis_data.get('market', 'unknown'),
            recommendation=main_rec,
            confidence=analysis_data.get('confidence', 0),
            strategies_used=[d.get('name') for d in supporting],
            chart_features=analysis_data.get('chart_features', {}),
            news_sentiment=analysis_data.get('news_sentiment', 0),
            session=analysis_data.get('session', 'unknown'),
            outcome=result_flag,
            profit=profit,
            notes=payload.get('notes', '')
        )
    except Exception as e:
        logger.exception(f"Failed to log trade experience: {e}")

    return {"status": "ok", "updated_strategies": len(supporting)}


@router.get('/analysis/{analysis_id}')
async def get_analysis(analysis_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    a = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail='Analysis not found')
    # Only owner or admin can view deleted analyses
    if a.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Access denied')
    return {
        'id': a.id,
        'user_id': a.user_id,
        'market': a.market,
        'description': a.description,
        'result_json': a.result_json,
        'is_deleted': bool(getattr(a, 'is_deleted', False)),
        'created_at': a.created_at
    }


@router.post('/analysis/{analysis_id}/delete')
async def soft_delete_analysis(analysis_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    a = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail='Analysis not found')
    if a.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Access denied')
    a.is_deleted = True
    db.commit()
    return {'status': 'soft_deleted'}
