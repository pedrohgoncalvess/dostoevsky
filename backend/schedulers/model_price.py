import asyncio
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from database.connection import DatabaseConnection
from database.models.ai import Model, ModelPrice
from database.operations.ai import ModelPriceRepository, ModelRepository
from utils import get_env_var


SCHEDULE_INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours
MODELS_ENDPOINT = "/api/v1/models"


async def start_model_price_scheduler() -> None:
    while True:
        try:
            sleep_seconds = await _calculate_sleep_seconds()
            if sleep_seconds > 0:
                await asyncio.sleep(sleep_seconds)

            await _sync_model_prices()
        except Exception:
            # Log and retry after the normal interval to avoid tight crash loops.
            pass

        await asyncio.sleep(SCHEDULE_INTERVAL_SECONDS)


async def _calculate_sleep_seconds() -> int:
    async with DatabaseConnection() as conn:
        repository = ModelPriceRepository(conn)
        last_price = await repository.find_last_inserted()

    if not last_price:
        return 0

    next_run = last_price.valid_from + timedelta(seconds=SCHEDULE_INTERVAL_SECONDS)
    now = datetime.utcnow()
    delta = (next_run - now).total_seconds()
    return max(0, int(delta))


async def _sync_model_prices() -> None:
    base_url = get_env_var("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
    api_key = get_env_var("OPENROUTER_API_KEY")

    if not api_key:
        return

    async with DatabaseConnection() as conn:
        model_repository = ModelRepository(conn)
        price_repository = ModelPriceRepository(conn)
        models = await model_repository.find_all(limit=1000)

        async with httpx.AsyncClient(timeout=60) as client:
            for model in models:
                try:
                    model_data = await _fetch_model_data(
                        client, base_url, api_key, model.external_id
                    )
                    if model_data is None:
                        continue

                    pricing = _extract_pricing(model_data)
                    if pricing is not None:
                        price = ModelPrice(
                            model_id=model.id,
                            input_price=pricing["input_price"],
                            output_price=pricing["output_price"],
                        )
                        await price_repository.insert(price)

                    await _sync_supported_voices(conn, model, model_data)
                except Exception:
                    # Skip individual model failures so one bad response does not break the batch.
                    continue


async def _fetch_model_data(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    external_id: str,
) -> dict[str, Any] | None:
    url = f"{base_url.rstrip('/')}{MODELS_ENDPOINT}/{external_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = await client.get(url, headers=headers)
    response.raise_for_status()

    data: dict[str, Any] = response.json()
    return data.get("data")


def _extract_pricing(model_data: dict[str, Any]) -> dict[str, Decimal] | None:
    pricing = model_data.get("pricing")
    if not pricing:
        return None

    input_price = _parse_price_per_token(pricing.get("prompt"))
    output_price = _parse_price_per_token(pricing.get("completion"))

    if input_price is None and output_price is None:
        return None

    return {
        "input_price": input_price or Decimal("0"),
        "output_price": output_price or Decimal("0"),
    }


async def _sync_supported_voices(
    conn,
    model: Model,
    model_data: dict[str, Any],
) -> None:
    if not model.for_tts:
        return

    supported_voices = model_data.get("supported_voices")
    if supported_voices is None:
        return

    api_voices = sorted(set(str(voice) for voice in supported_voices))
    db_voices = sorted(set(str(voice) for voice in (model.voices or [])))

    if api_voices == db_voices:
        return

    model.voices = api_voices
    await conn.commit()


def _parse_price_per_token(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)) * Decimal("1000000")
    except (InvalidOperation, TypeError, ValueError):
        return None
