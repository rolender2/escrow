from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List, Optional

import models, schemas, auth, database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = schemas.TokenData(username=username, role=payload.get("role"))
        except JWTError:
            raise credentials_exception
        
        user = db.query(models.User).filter(models.User.username == token_data.username).first()
        if user is None:
            raise credentials_exception
        return user
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auth Error: {str(e)}")

class RoleChecker:
    def __init__(self, allowed_roles: List[models.UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Operation not permitted for role {user.role}"
            )
        return user

def require_role(roles: List[models.UserRole]):
    return RoleChecker(roles)

# State & Hash Validation Helpers
def validate_escrow_state(escrow: models.Escrow, allowed_states: List[models.EscrowState]):
    if escrow.state not in allowed_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state {escrow.state}. Action requires {allowed_states}"
        )

def validate_agreement_hash(escrow: models.Escrow, incoming_version: int):
    # Hash Binding: Ensure action is performed on the correct version
    # Note: For MVP we just check version integer, but ideally we verify the hash too if passed.
    if escrow.version != incoming_version:
         raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch. Current: v{escrow.version}, Request: v{incoming_version}"
        )

def validate_one_time_custody(escrow: models.Escrow):
    # One-Time Gate: Funds can only be confirmed in CREATED state
    if escrow.state != models.EscrowState.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Funds already confirmed or state invalid."
        )
