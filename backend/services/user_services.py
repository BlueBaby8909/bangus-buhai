from fastapi import HTTPException
from models.user_profile import CreateUser, User
from sqlmodel import Session, select


def create_user(user: CreateUser, db: Session):
    existing = db.exec(select(User).where(User.email == user.email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    db_user = User.model_validate(user)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users(db: Session, skip: int = 0, limit: int = 10):
    users = db.exec(select(User).offset(skip).limit(limit)).all()
    return users


def get_user(user_id: int, db: Session):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def update_user(user_id: int, user_data: CreateUser, db: Session):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.sqlmodel_update(user_data.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(user)
    return user


def delete_user(user_id: int, db: Session):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
