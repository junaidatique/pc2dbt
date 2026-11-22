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
- **rounds** L608: SUBTOTAL is computed as SUBTOTAL_IN/100 (L111), a double at run time because high precision is off, and is rounded to 0 decimal places by the target column SUBTOTAL_CENTS decimal(15,0) (decision Q11)
- **crossed** L609: SRT_ORDERS.TAX_PAID goes into STG_ORDERS.TAX_PAID_CENTS, as the connector says
- **rounds** L609: TAX_PAID is computed as TAX_PAID_IN/100 (L112), a double at run time because high precision is off, and is rounded to 0 decimal places by the target column TAX_PAID_CENTS decimal(15,0) (decision Q11)
- **crossed** L610: SRT_ORDERS.ORDER_TOTAL goes into STG_ORDERS.ORDER_TOTAL_CENTS, as the connector says
- **rounds** L610: ORDER_TOTAL is computed as ORDER_TOTAL_IN/100 (L113), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column ORDER_TOTAL_CENTS decimal(12,2) (decision Q11)
- **crossed** L611: SRT_ORDERS.SUBTOTAL_CENTS goes into STG_ORDERS.SUBTOTAL, as the connector says
- **rounds** L611: SUBTOTAL_CENTS (double) is rounded to 0 decimal places by the target column SUBTOTAL decimal(15,0) (decision Q11)
- **crossed** L612: SRT_ORDERS.TAX_PAID_CENTS goes into STG_ORDERS.TAX_PAID, as the connector says
- **rounds** L612: TAX_PAID_CENTS (double) is rounded to 0 decimal places by the target column TAX_PAID decimal(15,0) (decision Q11)
- **crossed** L613: SRT_ORDERS.ORDER_TOTAL_CENTS goes into STG_ORDERS.ORDER_TOTAL, as the connector says

### m_fl_js_staging_full/stg_order_items

- **error_default** L455: ORDER_ID has an ERROR() default: a row with an empty ORDER_ID is skipped

### m_fl_js_staging_full/stg_products

- **crossed** L620: EXP_PRODUCTS.PRODUCT_PRICE goes into STG_PRODUCTS.PRODUCT_PRICE_CENTS, as the connector says
- **rounds** L620: PRODUCT_PRICE is computed as PRICE/100 (L201), a double at run time because high precision is off, and is rounded to 0 decimal places by the target column PRODUCT_PRICE_CENTS decimal(15,0) (decision Q11)
- **crossed** L621: EXP_PRODUCTS.PRODUCT_PRICE_CENTS goes into STG_PRODUCTS.PRODUCT_PRICE, as the connector says
- **rounds** L621: PRODUCT_PRICE_CENTS (double) is rounded to 2 decimal places by the target column PRODUCT_PRICE decimal(12,2) (decision Q11)

### m_fl_js_staging_full/stg_supplies

- **rounds** L627: SUPPLY_COST is computed as COST/100 (L503), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column SUPPLY_COST decimal(12,2) (decision Q11)
- **rounds** L628: SUPPLY_COST_CENTS (double) is rounded to 2 decimal places by the target column SUPPLY_COST_CENTS decimal(12,2) (decision Q11)

### m_fl_js_marts_core/customers

- **master_outer** L3664: JNR_CUSTOMERS_ORDERS is a Master Outer Join: it keeps every row from AGG_ORDERS_BY_CUSTOMER (detail) and only the rows from SQ_STG_CUSTOMERS (master) that match; SQ_STG_CUSTOMERS rows with no match are dropped

### m_fl_js_marts_core/orders

- **master_outer** L3446: JNR_ITEMS_SUPPLIES is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT2 (detail) and only the rows from JNR_ITEMS_PRODUCTS (master) that match; JNR_ITEMS_PRODUCTS rows with no match are dropped
- **master_outer** L3519: JNR_ORDERS_ITEMS_AGG is a Master Outer Join: it keeps every row from AGG_ITEMS_BY_ORDER (detail) and only the rows from SQ_STG_ORDERS1 (master) that match; SQ_STG_ORDERS1 rows with no match are dropped
- **sort_order** L3554: SRT_BY_CUSTOMER is kept only to put rows in order for EXP_CUSTOMER_ORDER_NUM (decisions Q12, Q13): sort keys CUSTOMER_ID, ORDERED_AT_DAY, ORDER_ID; case is ignored (Case Sensitive = NO, L3567), so strings sort by lower(); NULLs sort low (Null Treated Low = YES, L3571)
- **counter** L3589: v_PREV_CUSTOMER_ID is set to this row's CUSTOMER_ID (L3588) before v_ORDER_SEQUENCE compares them, so the comparison is true on every row where CUSTOMER_ID is not NULL: one running number over all rows in SRT_BY_CUSTOMER's order that never restarts per CUSTOMER_ID, back to 1 on a row whose CUSTOMER_ID is NULL
- **rounds** L3783: SUBTOTAL is computed as SUBTOTAL_CENTS/100 (L3534), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column SUBTOTAL decimal(12,2) (decision Q11)
- **rounds** L3784: TAX_PAID is computed as TAX_PAID_CENTS/100 (L3535), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column TAX_PAID decimal(12,2) (decision Q11)
- **rounds** L3785: ORDER_TOTAL is computed as ORDER_TOTAL_CENTS/100 (L3536), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column ORDER_TOTAL decimal(12,2) (decision Q11)

### m_fl_js_marts_core/order_items

- **master_outer** L3319: JNR_ADD_SUPPLY_COST is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT (detail) and only the rows from JNR_ADD_PRODUCTS (master) that match; JNR_ADD_PRODUCTS rows with no match are dropped

### m_fl_js_marts_core/products

- **rounds** L3805: PRODUCT_PRICE_CENTS (double) is rounded to 0 decimal places by the target column PRODUCT_PRICE_CENTS decimal(15,0) (decision Q11)

## Left out

- L535: Pre SQL on target STG_CUSTOMERS: TRUNCATE TABLE STG.STG_CUSTOMERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L538: Pre SQL on target STG_LOCATIONS: TRUNCATE TABLE STG.STG_LOCATIONS. Why: a dbt table is rebuilt on every run (decision Q9).
- L541: Pre SQL on target STG_ORDERS: TRUNCATE TABLE STG.STG_ORDERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L544: Pre SQL on target STG_ORDER_ITEMS: TRUNCATE TABLE STG.STG_ORDER_ITEMS. Why: a dbt table is rebuilt on every run (decision Q9).
- L547: Pre SQL on target STG_PRODUCTS: TRUNCATE TABLE STG.STG_PRODUCTS. Why: a dbt table is rebuilt on every run (decision Q9).
- L550: Pre SQL on target STG_SUPPLIES: TRUNCATE TABLE STG.STG_SUPPLIES. Why: a dbt table is rebuilt on every run (decision Q9).
- L3691: Pre SQL on target CUSTOMERS: TRUNCATE TABLE MART.CUSTOMERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3694: Pre SQL on target ORDERS: TRUNCATE TABLE MART.ORDERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3697: Pre SQL on target ORDER_ITEMS: TRUNCATE TABLE MART.ORDER_ITEMS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3700: Pre SQL on target PRODUCTS: TRUNCATE TABLE MART.PRODUCTS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3703: Pre SQL on target SUPPLIES: TRUNCATE TABLE MART.SUPPLIES. Why: a dbt table is rebuilt on every run (decision Q9).
- L4054: Workflow wf_FL_JAFFLESHOP_DEMO (run order, links and failure handling). Why: dbt orders models from ref(); behaviour on failure is out of scope (decisions Q5, Q17).
- L4058: Command task cmd_FL_JS_CREATE_RPT_VIEWS (its command is never read). Why: not part of any mapping (decision Q17).
- L811: Session s_FL_JS_STAGING_FULL (connections and load settings). Why: connections come from the dbt profile; load settings from materialization (decision Q17).
- L4064: Session s_FL_JS_MARTS_CORE (connections and load settings). Why: connections come from the dbt profile; load settings from materialization (decision Q17).
