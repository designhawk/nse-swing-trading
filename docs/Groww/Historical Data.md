Historical Data - Groww API

[](https://groww.in/)
[![Groww Logo](https://groww.in/favicon32x32-groww.ico)Groww API](/trade-api)

[](https://groww.in/)
[![Groww Logo](https://groww.in/favicon32x32-groww.ico)Groww API](/trade-api)

Python SDK Docs

Documentation for Python SDK

Search

⌘K

[Documentation](https://groww.in/trade-api/docs)

[Introduction](https://groww.in/trade-api/docs/python-sdk)
[Instruments](https://groww.in/trade-api/docs/python-sdk/instruments)
[Orders](https://groww.in/trade-api/docs/python-sdk/orders)
[Smart Orders](https://groww.in/trade-api/docs/python-sdk/smart-orders)
[Portfolio](https://groww.in/trade-api/docs/python-sdk/portfolio)
[Margin](https://groww.in/trade-api/docs/python-sdk/margin)
[Live Data](https://groww.in/trade-api/docs/python-sdk/live-data)
[Historical Data](https://groww.in/trade-api/docs/python-sdk/historical-data)
[Backtesting](https://groww.in/trade-api/docs/python-sdk/backtesting)
[Feed](https://groww.in/trade-api/docs/python-sdk/feed)
[User](https://groww.in/trade-api/docs/python-sdk/user)
[Annexures](https://groww.in/trade-api/docs/python-sdk/annexures)
[Exceptions](https://groww.in/trade-api/docs/python-sdk/exceptions)
[Changelog](https://groww.in/trade-api/docs/python-sdk/changelog)

On this page

Historical Data
===============

This guide describes how to fetch historical data of instruments easily using the SDK.

[Get Historical Candle Data](#get-historical-candle-data)
---------------------------------------------------------

> **Note**
> 
> This method is deprecated and will be removed in future releases. Please use `get_historical_candles` method instead. See [here](https://groww.in/trade-api/docs/python-sdk/backtesting#get-historical-candle-data) for more details.

### [Python SDK Usage](#python-sdk-usage)

Fetch historical candle data for an instrument using this `get_historical_candle_data` method.

```
from growwapi import GrowwAPI
import time
 
# Groww API Credentials (Replace with your actual credentials)
API_AUTH_TOKEN = "your_token"
 
# Initialize Groww API
groww = GrowwAPI(API_AUTH_TOKEN)
 
# you can give time programatically.
end_time_in_millis = int(time.time() * 1000) # epoch time in milliseconds
start_time_in_millis = end_time_in_millis - (24 * 60 * 60 * 1000) # last 24 hours
 
# OR
 
# you can give start time and end time in yyyy-MM-dd HH:mm:ss format.
end_time = "2025-02-27 14:00:00"
start_time = "2025-02-27 10:00:00"
 
historical_data_response = groww.get_historical_candle_data(
    trading_symbol="RELIANCE",
    exchange=groww.EXCHANGE_NSE,
    segment=groww.SEGMENT_CASH,
    start_time=start_time,
    end_time=end_time,
    interval_in_minutes=5 # Optional: Interval in minutes for the candle data
)
print(historical_data_response)
```


#### [Request Schema](#request-schema)



* Name: exchange *
  * Type: string
  * Description: Stock exchange
* Name: segment *
  * Type: string
  * Description: Segment of the instrument such as CASH, FNO etc.
* Name: trading_symbol *
  * Type: string
  * Description: Trading Symbol of the instrument as defined by the exchange
* Name: start_time *
  * Type: string
  * Description: Time in YYYY-MM-DD HH:mm:ss or epoch milliseconds format from which data is required
* Name: end_time *
  * Type: string
  * Description: Time in YYYY-MM-DD HH:mm:ss or epoch milliseconds format till when data is required
* Name: interval_in_minutes
  * Type: string
  * Description: Interval in minutes for which data is required


`*`required parameters

### [Response Payload](#response-payload)

All prices in rupees

```
{
  "candles": [
    [
      1633072800, // candle timestamp in epoch second
      150, // open price
      155, // high price
      145, // low price
      152, // close price
      10000 // volume
    ]
  ],
  "start_time": 2025-01-01 15:30:00,
  "end_time": 2025-01-01 15:30:00,
  "interval_in_minutes": 5
}
```


#### [Response Schema](#response-schema)



* Name: candles
  * Type: array[array]
  * Description: This contains the list of candles. Each candle has candle timestamp (epoch second), open (float), high (float), low (float), close (float) , volume (int) in that order.
* Name: start_time
  * Type: string
  * Description: Start time in yyyy-MM-dd HH:mm:ss
* Name: end_time
  * Type: string
  * Description: End time in yyyy-MM-dd HH:mm:ss
* Name: interval_in_minutes
  * Type: int
  * Description: Interval in minutes



|Candle Interval   |Max Duration per Request|Historical Data Available|
|------------------|------------------------|-------------------------|
|1 min             |7 days                  |Last 3 months            |
|5 min             |15 days                 |Last 3 months            |
|10 min            |30 days                 |Last 3 months            |
|1 hour (60 min)   |150 days                |Last 3 months            |
|4 hours (240 min) |365 days                |Last 3 months            |
|1 day (1440 min)  |1080 days (~3 years)    |Full history             |
|1 week (10080 min)|No Limit                |Full history             |


[

Previous

Live Data

](https://groww.in/trade-api/docs/python-sdk/live-data)
[

Next

Backtesting

](https://groww.in/trade-api/docs/python-sdk/backtesting)

### On this page

[Get Historical Candle Data](#get-historical-candle-data)