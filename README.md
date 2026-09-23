# Асинхронный сервис платежей

Микросервис принимает платежи через FastAPI, сохраняет платёж и событие outbox
в одной транзакции PostgreSQL, публикует событие в RabbitMQ и асинхронно
эмулирует обработку платежа. Результат отправляется на указанный webhook.

## Запуск

Требуется Docker с поддержкой Compose.

```bash
cp .env.example .env
docker compose up --build
```

По умолчанию сервисы доступны по адресам:

- API: `http://localhost:8000`
- RabbitMQ Management: `http://localhost:15672`

PostgreSQL и AMQP доступны только контейнерам во внутренней Compose-сети и не
публикуются на host.

Учётные данные RabbitMQ для локального окружения: `payments` / `payments`.
API-ключ берётся из `API_KEY` в `.env`.

Compose сначала ожидает PostgreSQL, затем сервис `migrate` применяет Alembic
миграции. Только после успешной миграции запускаются API и consumer.

## Создание платежа

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: replace-with-a-secret-value' \
  -H 'Idempotency-Key: order-123' \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Оплата заказа 123",
    "metadata": {"order_id": "123"},
    "webhook_url": "https://example.com/payment-webhook"
  }'
```

Ответ имеет статус `202 Accepted`:

```json
{
  "payment_id": "f22a0490-416d-4e46-8c4f-f44d711b7471",
  "status": "pending",
  "created_at": "2026-09-23T10:00:00Z"
}
```

Повторный запрос с тем же `Idempotency-Key` возвращает ранее созданный платёж
и не создаёт новое событие.

## Получение платежа

```bash
curl http://localhost:8000/api/v1/payments/f22a0490-416d-4e46-8c4f-f44d711b7471 \
  -H 'X-API-Key: replace-with-a-secret-value'
```

## Обработка сообщений

Outbox publisher отправляет события в очередь `payments.new`. Consumer ждёт
от 2 до 5 секунд и завершает платёж со статусом `succeeded` с вероятностью 90%
или `failed` с вероятностью 10%. После сохранения статуса он отправляет webhook.

При технической ошибке выполняются три попытки с экспоненциальной задержкой.
После третьей ошибки сообщение попадает в `payments.dlq`. Повторная обработка
не изменяет уже рассчитанный результат платежа. После успешной доставки webhook
в БД сохраняется её время, и обычная повторная доставка сообщения пропускается.
При сбое процесса непосредственно после HTTP-ответа webhook всё ещё может быть
доставлен повторно, поэтому получатель должен учитывать заголовок
`Idempotency-Key`.

Повторное использование `Idempotency-Key` с тем же телом возвращает созданный
ранее платёж. Если тело отличается, API отвечает `409 Conflict`.

Интерактивная документация отключена, чтобы все доступные HTTP endpoints были
защищены обязательным заголовком `X-API-Key`.

## Миграции и диагностика

Создать новую миграцию после изменения ORM-моделей:

```bash
docker compose run --rm migrate alembic revision --autogenerate -m "change"
```

Посмотреть логи:

```bash
docker compose logs -f api consumer migrate
```

Запустить unit-тесты локально:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

Остановить сервисы:

```bash
docker compose down
```

Удалить также данные PostgreSQL и RabbitMQ:

```bash
docker compose down -v
```
