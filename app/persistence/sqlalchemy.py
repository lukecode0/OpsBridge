from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, create_engine, delete, desc, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.domain.intake import DeliveryAttempt, EventRecord, StoredRequest


class Base(DeclarativeBase):
    pass


class RequestModel(Base):
    __tablename__ = "opsbridge_requests"

    request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(120))
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EventModel(Base):
    __tablename__ = "opsbridge_events"

    event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DeliveryAttemptModel(Base):
    __tablename__ = "opsbridge_delivery_attempts"

    attempt_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(32), index=True)
    target: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_number: Mapped[int]
    previous_attempt_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class SQLAlchemyIntakeRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_url(cls, database_url: str) -> "SQLAlchemyIntakeRepository":
        engine = create_engine(database_url, future=True)
        Base.metadata.create_all(engine)
        return cls(sessionmaker(engine, expire_on_commit=False, future=True))

    @property
    def requests(self) -> list[StoredRequest]:
        return self.list_requests()

    @property
    def events(self) -> list[EventRecord]:
        with self.session_factory() as session:
            records = session.scalars(select(EventModel).order_by(EventModel.created_at)).all()
        return [self._to_event(record) for record in records]

    @property
    def delivery_attempts(self) -> list[DeliveryAttempt]:
        with self.session_factory() as session:
            records = session.scalars(
                select(DeliveryAttemptModel).order_by(DeliveryAttemptModel.created_at)
            ).all()
        return [self._to_attempt(record) for record in records]

    def save_request(self, request: StoredRequest) -> None:
        with self.session_factory.begin() as session:
            session.add(RequestModel(**asdict(request)))

    def save_event(self, event: EventRecord) -> None:
        with self.session_factory.begin() as session:
            session.add(EventModel(**asdict(event)))

    def save_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
        with self.session_factory.begin() as session:
            session.add(DeliveryAttemptModel(**asdict(attempt)))

    def get_request(self, request_id: str) -> StoredRequest:
        with self.session_factory() as session:
            record = session.get(RequestModel, request_id)
        if record is None:
            raise KeyError(f"Unknown request_id: {request_id}")
        return self._to_request(record)

    def get_delivery_attempt(self, attempt_id: str) -> DeliveryAttempt:
        with self.session_factory() as session:
            record = session.get(DeliveryAttemptModel, attempt_id)
        if record is None:
            raise KeyError(f"Unknown attempt_id: {attempt_id}")
        return self._to_attempt(record)

    def get_latest_attempt_for_request(self, request_id: str) -> DeliveryAttempt:
        with self.session_factory() as session:
            record = session.scalars(
                select(DeliveryAttemptModel)
                .where(DeliveryAttemptModel.request_id == request_id)
                .order_by(
                    desc(DeliveryAttemptModel.created_at),
                    desc(DeliveryAttemptModel.attempt_number),
                )
            ).first()
        if record is None:
            raise KeyError(f"No attempts for request_id: {request_id}")
        return self._to_attempt(record)

    def update_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
        with self.session_factory.begin() as session:
            record = session.get(DeliveryAttemptModel, attempt.attempt_id)
            if record is None:
                raise KeyError(f"Unknown attempt_id: {attempt.attempt_id}")
            record.request_id = attempt.request_id
            record.target = attempt.target
            record.status = attempt.status
            record.created_at = attempt.created_at
            record.completed_at = attempt.completed_at
            record.error_message = attempt.error_message
            record.attempt_number = attempt.attempt_number
            record.previous_attempt_id = attempt.previous_attempt_id

    def list_delivery_attempts_for_request(self, request_id: str) -> list[DeliveryAttempt]:
        with self.session_factory() as session:
            records = session.scalars(
                select(DeliveryAttemptModel)
                .where(DeliveryAttemptModel.request_id == request_id)
                .order_by(DeliveryAttemptModel.created_at, DeliveryAttemptModel.attempt_number)
            ).all()
        return [self._to_attempt(record) for record in records]

    def list_events_for_request(self, request_id: str) -> list[EventRecord]:
        with self.session_factory() as session:
            records = session.scalars(
                select(EventModel)
                .where(EventModel.request_id == request_id)
                .order_by(EventModel.created_at)
            ).all()
        return [self._to_event(record) for record in records]

    def list_requests(self) -> list[StoredRequest]:
        with self.session_factory() as session:
            records = session.scalars(
                select(RequestModel).order_by(desc(RequestModel.received_at))
            ).all()
        return [self._to_request(record) for record in records]

    def request_identifier_in_use(self, identifier: str) -> bool:
        with self.session_factory() as session:
            record = session.scalar(
                select(RequestModel.request_id).where(
                    or_(
                        RequestModel.external_id == identifier,
                        RequestModel.request_id == identifier,
                    )
                )
            )
        return record is not None

    def reset(self) -> None:
        with self.session_factory.begin() as session:
            session.execute(delete(EventModel))
            session.execute(delete(DeliveryAttemptModel))
            session.execute(delete(RequestModel))

    @staticmethod
    def _to_request(record: RequestModel) -> StoredRequest:
        return StoredRequest(
            request_id=record.request_id,
            source=record.source,
            external_id=record.external_id,
            payload=record.payload,
            received_at=record.received_at,
        )

    @staticmethod
    def _to_event(record: EventModel) -> EventRecord:
        return EventRecord(
            event_id=record.event_id,
            request_id=record.request_id,
            event_type=record.event_type,
            payload=record.payload,
            created_at=record.created_at,
        )

    @staticmethod
    def _to_attempt(record: DeliveryAttemptModel) -> DeliveryAttempt:
        return DeliveryAttempt(
            attempt_id=record.attempt_id,
            request_id=record.request_id,
            target=record.target,
            status=record.status,
            created_at=record.created_at,
            completed_at=record.completed_at,
            error_message=record.error_message,
            attempt_number=record.attempt_number,
            previous_attempt_id=record.previous_attempt_id,
        )
