from typing import Optional
from sqlalchemy.orm import Session

from config.database import db_manager, User
from src.utils.logger import logger


class UserDatabase:
    """Database operations for users"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_or_create_user(self, name: str, role: str) -> int:
        """
        Tìm hoặc tạo user trong database
        
        Args:
            name: Tên người dùng
            role: 'candidate' hoặc 'interviewer'
        
        Returns:
            user_id: ID của user
        """
        session: Session = self.db_manager.get_session()
        
        try:
            # Tìm user theo tên và role
            user = session.query(User).filter(
                User.name == name,
                User.role == role
            ).first()
            
            if user:
                logger.info(f"Found existing {role}: {name} (ID: {user.id})")
                return user.id
            
            # Tạo user mới
            new_user = User(name=name, role=role)
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            logger.info(f"Created new {role}: {name} (ID: {new_user.id})")
            return new_user.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Lấy thông tin user theo ID"""
        session: Session = self.db_manager.get_session()
        
        try:
            user = session.query(User).filter(User.id == user_id).first()
            
            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "role": user.role,
                    "created_at": user.created_at.isoformat()
                }
            return None
        finally:
            session.close()
    
    def get_user_by_name_and_role(self, name: str, role: str) -> Optional[dict]:
        """Lấy thông tin user theo tên và role"""
        session: Session = self.db_manager.get_session()
        
        try:
            user = session.query(User).filter(
                User.name == name,
                User.role == role
            ).first()
            
            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "role": user.role,
                    "created_at": user.created_at.isoformat()
                }
            return None
        finally:
            session.close()
