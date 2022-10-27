## description
this strategy using supertrend & dema144 & dema169 indicators to generate long/short signals.

demaXXX means double exponential moving average and the period is XXX (for hourly k-lines, it means XXX hours)

### when to long / close short?
- supertrend give 'buy' signals
- the close price of current k-line is higher than values of both dema144 and dema169 

### when to short / close long?
- supertrend give 'sell' signals
- the close price of current k-line is lower than values of both dema144 and dema169 

### what are take-profit price and stop-losses price?
- stop-losses price is the low price of current k-line
- the first level of take-profit price is 1:1 of reward ratio, and the second level is 1:2 of reward ratio. it will be better to using 'moving stop-losses strategy'  

## install libs
- install conda first
- install telegram bot:  pip install python-telegram-bot --upgrade

## setup .env
TG_TOKEN={your telegram token}
TG_CHAT_ID={your telegram chat id}

## start 
python supertrend-dema144-dema169.py BTCUSDT 1h

the best choice is adding this command to crontab to run every hour 
