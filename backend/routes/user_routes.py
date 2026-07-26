from fastapi import APIRouter, Depends, Query, status
from models.user_profile import CreateUser, User
import services.user_services as service
from sqlmodel import Session
from database.db import get_session

router = APIRouter()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: CreateUser, db: Session = Depends(get_session)):
    return service.create_user(user=user, db=db)


@router.get("/", response_model=list[User], status_code=status.HTTP_200_OK)
def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    return service.get_all_users(skip=skip, limit=limit, db=db)


@router.get("/{user_id}", response_model=User, status_code=status.HTTP_200_OK)
def get_user(user_id: int, db: Session = Depends(get_session)):
    return service.get_user(user_id=user_id, db=db)


@router.put("/{user_id}", response_model=User, status_code=status.HTTP_200_OK)
def update_user(user_id: int, user_data: CreateUser, db: Session = Depends(get_session)):
    return service.update_user(user_id=user_id, user_data=user_data, db=db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_session)):
    return service.delete_user(user_id=user_id, db=db)
