import os
import redis

r = redis.from_url(
    os.environ["REDIS_URL"],
    decode_responses=True
)