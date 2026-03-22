Margin - Groww API

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

Margin
======

This guide describes how to calculate required margin for orders and get available user margin using the SDK.

[Get Available User Margin](#get-available-user-margin)
-------------------------------------------------------

Easily retrieve your available margin details for equity, F&O, and commodity segments using this `get_available_margin_details` method.

### [Python SDK Usage](#python-sdk-usage)

```
from growwapi import GrowwAPI
 
# Groww API Credentials (Replace with your actual credentials)
API_AUTH_TOKEN = "your_token"
 
# Initialize Groww API
groww = GrowwAPI(API_AUTH_TOKEN)
 
available_margin_details_response = groww.get_available_margin_details()
print(available_margin_details_response)
```


### [Response Payload](#response-payload)

All prices in rupees.

```
{
  "clear_cash": 96.21,
  "net_margin_used": 1.8,
  "brokerage_and_charges": 0.0,
  "collateral_used": 0.0,
  "collateral_available": 0.0,
  "adhoc_margin": 0.0,
  "fno_margin_details": {
    "net_fno_margin_used": 0.0,
    "span_margin_used": 0.0,
    "exposure_margin_used": 0.0,
    "future_balance_available": 94.41,
    "option_buy_balance_available": 94.41,
    "option_sell_balance_available": 94.41
  },
  "equity_margin_details": {
    "net_equity_margin_used": -1.8,
    "cnc_margin_used": -1.8,
    "mis_margin_used": 0.0,
    "cnc_balance_available": 94.41,
    "mis_balance_available": 94.41
  },
  "commodity_margin_details": {
    "commodity_span_margin": 7000,
    "commodity_exposure_margin": 4000,
    "commodity_tender_margin": 2000,
    "commodity_special_margin": 1000,
    "commodity_additional_margin": 3000,
    "commodity_unrealised_m2m": 1500,
    "commodity_realised_m2m": 2500
  }
}
```


> **Note:** Commodity orders require SPAN and Exposure margins. The margin requirement varies by:
> 
> *   Product type (MIS for intraday, NRML for carry forward)
> *   Contract value and volatility
> *   Exchange regulations

#### [Response Schema](#response-schema)


|Name                         |Type |Description                                                  |
|-----------------------------|-----|-------------------------------------------------------------|
|clear_cash                   |float|Clear cash available                                         |
|net_margin_used              |float|Net margin used                                              |
|brokerage_and_charges        |float|Brokerage and charges                                        |
|collateral_used              |float|Collateral used                                              |
|collateral_available         |float|Collateral available                                         |
|adhoc_margin                 |float|Adhoc margin available                                       |
|net_fno_margin_used          |float|Net FnO margin used                                          |
|span_margin_used             |float|Span Margin Used (for F&O)                                   |
|exposure_margin_used         |float|Exposure Margin Used (for F&O)                               |
|future_balance_available     |float|Future Balance Available                                     |
|option_buy_balance_available |float|Option Buy Balance Available                                 |
|option_sell_balance_available|float|Option Sell Balance Available                                |
|net_equity_margin_used       |float|Net equity margin used                                       |
|cnc_margin_used              |float|CNC margin used                                              |
|mis_margin_used              |float|MIS margin used                                              |
|cnc_balance_available        |float|CNC balance available                                        |
|mis_balance_available        |float|MIS balance available                                        |
|commodity_span_margin        |float|SPAN margin used for commodity trading                       |
|commodity_exposure_margin    |float|Exposure margin used for commodity trading                   |
|commodity_tender_margin      |float|Tender margin for commodity contracts nearing delivery       |
|commodity_special_margin     |float|Special margin levied during high volatility in commodities  |
|commodity_additional_margin  |float|Additional margin requirements for commodity positions       |
|commodity_unrealised_m2m     |float|Unrealised mark-to-market profit/loss for commodity positions|
|commodity_realised_m2m       |float|Realised mark-to-market profit/loss for commodity positions  |


* * *

[Required Margin For Order](#required-margin-for-order)
-------------------------------------------------------

Calculate the required margin for a single order or basket of orders using this `get_order_margin_details` method. Basket orders are only supported for `FNO` Segment.

### [Python SDK Usage](#python-sdk-usage-1)

```
from growwapi import GrowwAPI
 
# Groww API Credentials (Replace with your actual credentials)
API_AUTH_TOKEN = "your_token"
 
# Initialize Groww API
groww = GrowwAPI(API_AUTH_TOKEN)
 
order_details = [
    
    {
        "trading_symbol": "RELIANCE",
        "transaction_type": groww.TRANSACTION_TYPE_BUY,
        "quantity": 1,
        "price": 2500, # Optional: Price (include for limit orders; omit or adjust if not applicable).
        "order_type": groww.ORDER_TYPE_LIMIT,
        "product": groww.PRODUCT_CNC,
        "exchange": groww.EXCHANGE_NSE
    }
]
order_margin_details_response = groww.get_order_margin_details(
  segment=groww.SEGMENT_CASH,
  orders=order_details,
)
print(order_margin_details_response)
```


#### [Request Schema](#request-schema)


|Name              |Type   |Description                                                |
|------------------|-------|-----------------------------------------------------------|
|trading_symbol *  |string |Trading Symbol of the instrument as defined by the exchange|
|quantity *        |integer|Quantity of instrument to order                            |
|price             |decimal|Price of the instrument in rupees case of Limit order      |
|exchange *        |string |Stock exchange                                             |
|segment *         |string |Segment of the instrument such as CASH, FNO and COMMODITY. |
|product *         |string |Product type                                               |
|order_type *      |string |Order type                                                 |
|transaction_type *|string |Transaction type of the trade                              |


`*`required parameters

### [Response Payload](#response-payload-1)

All prices in rupees.

```
{
  "exposure_required": 0.0, 
  "span_required": 0.0, 
  "option_buy_premium": 0.0, 
  "brokerage_and_charges": 0.2, 
  "total_requirement": 100.2, 
  "cash_cnc_margin_required": 100.0,
  "physical_delivery_margin_requirement": 0.0
}
```


#### [Response Schema](#response-schema-1)



* Name: exposure_required
  * Type: float
  * Description: Margin required to cover the exposure for the trade.
* Name: span_required
  * Type: float
  * Description: SPAN margin required for F&O trades (not applicable for equity cash segment). 
* Name: option_buy_premium
  * Type: float
  * Description: Premium amount required for buying options contracts.
* Name: brokerage_and_charges
  * Type: float
  * Description: Total brokerage and other exchange-related charges for the order.
* Name: total_requirement
  * Type: float
  * Description: Total margin requirement including all charges and margin components.
* Name: cash_cnc_margin_required
  * Type: float
  * Description: Margin required for CNC (Cash & Carry) orders in the cash segment.
* Name: cash_mis_margin_required
  * Type: float
  * Description: Margin required for MIS (Margin Intraday Square-off) orders in the cash segment.
* Name: physical_delivery_margin_requirement
  * Type: float
  * Description: Additional margin required for physical settlement of derivative contracts.


[

Previous

Portfolio

](https://groww.in/trade-api/docs/python-sdk/portfolio)
[

Next

Live Data

](https://groww.in/trade-api/docs/python-sdk/live-data)

### On this page

[Get Available User Margin](#get-available-user-margin)
[Required Margin For Order](#required-margin-for-order)