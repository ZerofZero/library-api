# auth.py
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key 헤더가 필요합니다")
    if api_key not in settings.api_keys_list:
        raise HTTPException(status_code=403, detail="유효하지 않은 API 키입니다")
    return api_key


def verify_librarian_key(api_key: str = Depends(api_key_header)):
    if api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key 헤더가 필요합니다")
    if api_key not in settings.librarian_keys_list:
        raise HTTPException(status_code=403, detail="사서 권한이 필요합니다")
    return api_key