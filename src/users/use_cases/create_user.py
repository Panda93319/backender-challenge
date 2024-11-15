from typing import Any
import structlog
from core.base_model import Model
from logs.models import OutboxLog
from core.use_case import UseCase, UseCaseRequest, UseCaseResponse
from users.models import User
from django.db import transaction as db_transaction
from sentry_sdk import start_transaction

logger = structlog.get_logger(__name__)


class UserCreated(Model):
    email: str
    first_name: str
    last_name: str


class CreateUserRequest(UseCaseRequest):
    email: str
    first_name: str = ''
    last_name: str = ''


class CreateUserResponse(UseCaseResponse):
    result: User | None = None
    error: str = ''


class CreateUser(UseCase):    
    def _get_context_vars(self, request: UseCaseRequest) -> dict[str, Any]:
        return {
            'email': request.email,
            'first_name': request.first_name,
            'last_name': request.last_name,
        }
    @db_transaction.atomic
    def _execute(self, request: CreateUserRequest) -> CreateUserResponse:
        with start_transaction(op="use_case", name="CreateUser") as transaction:
            logger.info("Creating a new user", email=request.email, transaction_id=transaction.trace_id)
            user, created = User.objects.get_or_create(
                email=request.email,
                defaults={
                    'first_name': request.first_name, 'last_name': request.last_name,
                },
            )
            if created:
                logger.info('user has been created')
                self._log(user)
                return CreateUserResponse(result=user)
            logger.error("User creation failed", email=request.email, transaction_id=transaction.trace_id)
            return CreateUserResponse(error='User with this email already exists')

    def _log(self, user: User) -> None:
        OutboxLog.objects.create(
            event_type="user_created",
            environment="Local",
            event_context={"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
        )

