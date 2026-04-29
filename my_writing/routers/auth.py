from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import create_token, is_password_set, set_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PasswordPayload(BaseModel):
    password: str


@router.get("/status")
def auth_status():
    return {"passwordSet": is_password_set()}


@router.post("/setup")
def setup(payload: PasswordPayload):
    if is_password_set():
        raise HTTPException(status_code=400, detail="密码已设置，请直接登录")
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少 4 位")
    set_password(payload.password)
    return {"token": create_token()}


@router.post("/login")
def login(payload: PasswordPayload):
    if not is_password_set():
        raise HTTPException(status_code=400, detail="请先设置密码")
    if not verify_password(payload.password):
        raise HTTPException(status_code=401, detail="密码错误")
    return {"token": create_token()}
