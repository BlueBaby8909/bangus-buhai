from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from .schemas import LoginRequest, OperatorResponse, operator_response
from .service import Operator

router = APIRouter(prefix="/api/v1", tags=["accounts"])


def account_service(request: Request):
    return request.app.state.account_runtime.get()


def current_operator(request: Request) -> Operator:
    service = account_service(request)
    return service.authenticate(request.cookies.get(service.settings.cookie_name),
        touch=request.headers.get('X-BB-Passive') != '1')


def hatchery_operator(hatchery_id: UUID, operator: Operator = Depends(current_operator)) -> Operator:
    """Reusable path-scoped guard for future registry/history endpoints."""
    return operator.require_hatchery(hatchery_id)


@router.post("/auth/login", response_model=OperatorResponse)
def login(body: LoginRequest, request: Request, response: Response):
    service = account_service(request)
    token, operator = service.login(body.email, body.password.get_secret_value(),
                                    request.client.host if request.client else "unknown")
    response.set_cookie(service.settings.cookie_name, token, max_age=8 * 3600,
                        httponly=True, secure=not service.settings.development, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return operator_response(operator)


@router.get("/me", response_model=OperatorResponse)
def me(response: Response, operator: Operator = Depends(current_operator)):
    response.headers["Cache-Control"] = "no-store"
    return operator_response(operator)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    service = account_service(request)
    service.logout(request.cookies.get(service.settings.cookie_name))
    response.delete_cookie(service.settings.cookie_name, path="/", httponly=True,
                           secure=not service.settings.development, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
