from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("accounting_processes.id", ondelete="CASCADE"))
    file_type = Column(String, nullable=False)  # kushki | banregio
    original_name = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    status = Column(String, default="uploaded")  # uploaded | parsed | error
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    process = relationship("AccountingProcess", back_populates="files")
