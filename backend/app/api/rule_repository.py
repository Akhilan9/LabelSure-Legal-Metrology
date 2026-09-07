from fastapi import APIRouter, Depends, Request
from app.api.dependencies import get_current_user
from app.rules.loader import MANIFEST, load_ruleset
router = APIRouter(prefix='/rules', tags=['Rules repository'])
@router.get('')
def repository(request: Request, user=Depends(get_current_user)):
    return {'configured': request.app.state.settings.ruleset_id,
            'items': [load_ruleset(name, version).model_dump(mode='json') for name,version in MANIFEST if name != 'labelsure_prototype']}
