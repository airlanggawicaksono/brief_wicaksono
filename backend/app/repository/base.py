from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.config.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> T | None:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self, skip: int = 0, limit: int = 100) -> list[T]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj: T) -> T:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int) -> bool:
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False
