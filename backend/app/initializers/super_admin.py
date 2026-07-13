from database.connection import DatabaseConnection
from database.models.base import User
from database.operations.base import UserRepository
from app.users.services import get_password_hash
from log import logger
from utils import get_env_var


DEFAULT_SUPER_ADMIN_USERNAME = "admin@dostoevsky.com"
DEFAULT_SUPER_ADMIN_PASSWORD = "admin"


async def initialize_super_admin() -> None:
    username = get_env_var("SUPER_ADMIN_USERNAME") or DEFAULT_SUPER_ADMIN_USERNAME
    password = get_env_var("SUPER_ADMIN_PASSWORD") or DEFAULT_SUPER_ADMIN_PASSWORD

    if username == DEFAULT_SUPER_ADMIN_USERNAME and password == DEFAULT_SUPER_ADMIN_PASSWORD:
        await logger.info(
            "SuperAdmin",
            "Default credentials in use",
            "SUPER_ADMIN_USERNAME and SUPER_ADMIN_PASSWORD are using default values. "
            "Change them in production or shared environments.",
        )

    async with DatabaseConnection() as conn:
        user_repository = UserRepository(conn)

        existing_super_admin = await user_repository.find_by_email(username)
        if existing_super_admin:
            return

        existing_users = await user_repository.find_all(limit=1)
        if existing_users:
            return

        super_admin = User(
            name="Super Admin",
            email=username,
            password=get_password_hash(password),
            is_verified=True,
            is_admin=True,
        )
        await user_repository.insert(super_admin)
        await logger.info(
            "SuperAdmin",
            "Super admin created",
            f"Created super admin user: {username}",
        )
