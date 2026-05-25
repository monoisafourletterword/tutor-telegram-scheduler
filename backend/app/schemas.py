from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class StudentBase(BaseModel):
    name: str
    telegram_id: str
    phone: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class LessonBase(BaseModel):
    student_id: int
    subject: Optional[str] = None
    lesson_datetime: datetime
    platform: Optional[str] = None
    meeting_link: Optional[str] = None

class LessonCreate(LessonBase):
    pass

class LessonResponse(LessonBase):
    id: int
    reminder_sent: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageTemplateBase(BaseModel):
    name: str
    text: str
    send_before_minutes: int = 30

class MessageTemplateCreate(MessageTemplateBase):
    pass

class MessageTemplateResponse(MessageTemplateBase):
    id: int
    
    class Config:
        from_attributes = True