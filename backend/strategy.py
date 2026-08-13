import time
from typing import Optional

class EMAState:
    def __init__(self, period: int):
        self.period = period
        self.alpha = 2 / (period + 1)
        self.value: Optional[float] = None

    def update(self, price: float) -> float:
        if self.value is None:
            self.value = price
        else:
            self.value = self.alpha * price + (1 - self.alpha) * self.value
        return self.value


class EMAStrategy:
    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short = EMAState(short_period)
        self.long = EMAState(long_period)
        self.last_signal = "HOLD"

    def process_tick(self, tick: dict) -> dict:
        # tick is expected to contain 'quote' as price and 'epoch' as timestamp
        price = float(tick.get('quote'))
        ts = tick.get('epoch', int(time.time()))

        short_val = self.short.update(price)
        long_val = self.long.update(price)

        signal = "HOLD"
        if short_val > long_val:
            signal = "BUY"
        elif short_val < long_val:
            signal = "SELL"

        # only emit when signal changes to reduce chatter (optional)
        if signal != self.last_signal:
            self.last_signal = signal

        return {
            'type': 'signal',
            'price': price,
            'ts': ts,
            'signal': signal,
            'ema_short': short_val,
            'ema_long': long_val
        }
