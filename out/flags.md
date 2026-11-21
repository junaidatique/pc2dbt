# Flags for FLOWLINE_DEMO_JAFFLESHOP.xml

Behaviour copied from the XML as-is (decision D1), and what the converter left out.
Line numbers refer to the PowerCenter XML.

## Flags

### m_fl_js_staging_full/stg_locations

- **error_default** L235: TAX_RATE has an ERROR() default: a row with an empty TAX_RATE is skipped
- **router_default** L277: RTR_REGION: the default group is not connected, so rows that match no group are dropped

### m_fl_js_staging_full/stg_orders

- **century** L110: two-digit year: DuckDB reads 00-68 as 20xx and 69-99 as 19xx; PowerCenter's rule may differ
- **crossed** L608: SRT_ORDERS.SUBTOTAL goes into STG_ORDERS.SUBTOTAL_CENTS, as the connector says
- **rounds** L608: SUBTOTAL (double) is rounded to 0 decimal places by the target column SUBTOTAL_CENTS decimal(15,0) (decision Q11)
- **crossed** L609: SRT_ORDERS.TAX_PAID goes into STG_ORDERS.TAX_PAID_CENTS, as the connector says
- **rounds** L609: TAX_PAID (double) is rounded to 0 decimal places by the target column TAX_PAID_CENTS decimal(15,0) (decision Q11)
- **crossed** L610: SRT_ORDERS.ORDER_TOTAL goes into STG_ORDERS.ORDER_TOTAL_CENTS, as the connector says
- **crossed** L611: SRT_ORDERS.SUBTOTAL_CENTS goes into STG_ORDERS.SUBTOTAL, as the connector says
- **rounds** L611: SUBTOTAL_CENTS (double) is rounded to 0 decimal places by the target column SUBTOTAL decimal(15,0) (decision Q11)
- **crossed** L612: SRT_ORDERS.TAX_PAID_CENTS goes into STG_ORDERS.TAX_PAID, as the connector says
- **rounds** L612: TAX_PAID_CENTS (double) is rounded to 0 decimal places by the target column TAX_PAID decimal(15,0) (decision Q11)
- **crossed** L613: SRT_ORDERS.ORDER_TOTAL_CENTS goes into STG_ORDERS.ORDER_TOTAL, as the connector says

### m_fl_js_staging_full/stg_order_items

- **error_default** L455: ORDER_ID has an ERROR() default: a row with an empty ORDER_ID is skipped

### m_fl_js_staging_full/stg_products

- **crossed** L620: EXP_PRODUCTS.PRODUCT_PRICE goes into STG_PRODUCTS.PRODUCT_PRICE_CENTS, as the connector says
- **rounds** L620: PRODUCT_PRICE (double) is rounded to 0 decimal places by the target column PRODUCT_PRICE_CENTS decimal(15,0) (decision Q11)
- **crossed** L621: EXP_PRODUCTS.PRODUCT_PRICE_CENTS goes into STG_PRODUCTS.PRODUCT_PRICE, as the connector says
- **rounds** L621: PRODUCT_PRICE_CENTS (double) is rounded to 2 decimal places by the target column PRODUCT_PRICE decimal(12,2) (decision Q11)

### m_fl_js_staging_full/stg_supplies

- **rounds** L627: SUPPLY_COST (double) is rounded to 2 decimal places by the target column SUPPLY_COST decimal(12,2) (decision Q11)
- **rounds** L628: SUPPLY_COST_CENTS (double) is rounded to 2 decimal places by the target column SUPPLY_COST_CENTS decimal(12,2) (decision Q11)

## Left out

- L535: Pre SQL on target STG_CUSTOMERS: TRUNCATE TABLE STG.STG_CUSTOMERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L538: Pre SQL on target STG_LOCATIONS: TRUNCATE TABLE STG.STG_LOCATIONS. Why: a dbt table is rebuilt on every run (decision Q9).
- L541: Pre SQL on target STG_ORDERS: TRUNCATE TABLE STG.STG_ORDERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L544: Pre SQL on target STG_ORDER_ITEMS: TRUNCATE TABLE STG.STG_ORDER_ITEMS. Why: a dbt table is rebuilt on every run (decision Q9).
- L547: Pre SQL on target STG_PRODUCTS: TRUNCATE TABLE STG.STG_PRODUCTS. Why: a dbt table is rebuilt on every run (decision Q9).
- L550: Pre SQL on target STG_SUPPLIES: TRUNCATE TABLE STG.STG_SUPPLIES. Why: a dbt table is rebuilt on every run (decision Q9).
- L4054: Workflow wf_FL_JAFFLESHOP_DEMO (run order, links and failure handling). Why: dbt orders models from ref(); behaviour on failure is out of scope (decisions Q5, Q17).
- L4058: Command task cmd_FL_JS_CREATE_RPT_VIEWS (its command is never read). Why: not part of any mapping (decision Q17).
- L811: Session s_FL_JS_STAGING_FULL (connections and load settings). Why: connections come from the dbt profile; load settings from materialization (decision Q17).
