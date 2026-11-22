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

### m_fl_js_marts_enriched/customer_360

- **master_outer** L1350: JNR_ADD_CUSTOMERS is a Master Outer Join: it keeps every row from SQ_STG_CUSTOMERS (detail) and only the rows from JNR_ADD_PRODUCTS (master) that match; JNR_ADD_PRODUCTS rows with no match are dropped
- **master_outer** L1398: JNR_ADD_LOCATIONS is a Master Outer Join: it keeps every row from SQ_STG_LOCATIONS (detail) and only the rows from JNR_ADD_CUSTOMERS (master) that match; JNR_ADD_CUSTOMERS rows with no match are dropped
- **master_outer** L1476: JNR_ADD_SUPPLIES is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT (detail) and only the rows from JNR_ADD_LOCATIONS (master) that match; JNR_ADD_LOCATIONS rows with no match are dropped
- **master_outer** L1591: JNR_ORDERS_ITEMS_AGG is a Master Outer Join: it keeps every row from AGG_ITEMS_BY_ORDER (detail) and only the rows from SQ_STG_ORDERS1 (master) that match; SQ_STG_ORDERS1 rows with no match are dropped
- **sort_order** L1635: SRT_FOR_CUSTOMER_SEQ is kept only to put rows in order for EXP_CUSTOMER_ORDER_NUM (decisions Q12, Q13): sort keys CUSTOMER_ID, ORDERED_AT_DAY, ORDER_ID; case is ignored (Case Sensitive = NO, L1654), so strings sort by lower(); NULLs sort high (Null Treated Low = NO, L1658)
- **counter** L1706: v_PREV_CUSTOMER_ID is set to this row's CUSTOMER_ID (L1705) before v_ORDER_SEQUENCE compares them, so the comparison is true on every row where CUSTOMER_ID is not NULL: one running number over all rows in SRT_FOR_CUSTOMER_SEQ's order that never restarts per CUSTOMER_ID, back to 1 on a row whose CUSTOMER_ID is NULL
- **router_default** L1741: RTR_ORDER_VALUE_BAND: the default group is not connected, so rows that match no group are dropped
- **master_outer** L2243: JNR_CUSTOMERS is a Master Outer Join: it keeps every row from AGGTRANS (detail) and only the rows from SQ_STG_CUSTOMERS1 (master) that match; SQ_STG_CUSTOMERS1 rows with no match are dropped
- **crossed** L2480: EXP_RFM_SEGMENT.LIFETIME_SPEND goes into CUSTOMER_360.LIFETIME_SPEND_PRETAX, as the connector says
- **crossed** L2481: EXP_RFM_SEGMENT.LIFETIME_SPEND_PRETAX goes into CUSTOMER_360.LIFETIME_TAX_PAID, as the connector says
- **crossed** L2482: EXP_RFM_SEGMENT.LIFETIME_TAX_PAID goes into CUSTOMER_360.LIFETIME_SPEND, as the connector says
- **rounds** L2485: AVG_ORDER_VALUE is computed as IIF(v_ORDERS_CL=0,0,v_SPEND_CL/v_ORDERS_CL) (L2264), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column AVG_ORDER_VALUE decimal(12,2) (decision Q11)
- **parameter** L3104: $$RUN_DATE becomes the dbt var run_date, default 2025-12-31 from the XML (decision Q15); the session's parameter file (L4554) can override it in PowerCenter, so pass the same value with dbt --vars

### m_fl_js_marts_enriched/order_financials

- **master_outer** L1350: JNR_ADD_CUSTOMERS is a Master Outer Join: it keeps every row from SQ_STG_CUSTOMERS (detail) and only the rows from JNR_ADD_PRODUCTS (master) that match; JNR_ADD_PRODUCTS rows with no match are dropped
- **master_outer** L1398: JNR_ADD_LOCATIONS is a Master Outer Join: it keeps every row from SQ_STG_LOCATIONS (detail) and only the rows from JNR_ADD_CUSTOMERS (master) that match; JNR_ADD_CUSTOMERS rows with no match are dropped
- **master_outer** L1476: JNR_ADD_SUPPLIES is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT (detail) and only the rows from JNR_ADD_LOCATIONS (master) that match; JNR_ADD_LOCATIONS rows with no match are dropped
- **master_outer** L1591: JNR_ORDERS_ITEMS_AGG is a Master Outer Join: it keeps every row from AGG_ITEMS_BY_ORDER (detail) and only the rows from SQ_STG_ORDERS1 (master) that match; SQ_STG_ORDERS1 rows with no match are dropped
- **sort_order** L1635: SRT_FOR_CUSTOMER_SEQ is kept only to put rows in order for EXP_CUSTOMER_ORDER_NUM (decisions Q12, Q13): sort keys CUSTOMER_ID, ORDERED_AT_DAY, ORDER_ID; case is ignored (Case Sensitive = NO, L1654), so strings sort by lower(); NULLs sort high (Null Treated Low = NO, L1658)
- **counter** L1706: v_PREV_CUSTOMER_ID is set to this row's CUSTOMER_ID (L1705) before v_ORDER_SEQUENCE compares them, so the comparison is true on every row where CUSTOMER_ID is not NULL: one running number over all rows in SRT_FOR_CUSTOMER_SEQ's order that never restarts per CUSTOMER_ID, back to 1 on a row whose CUSTOMER_ID is NULL
- **router_default** L1741: RTR_ORDER_VALUE_BAND: the default group is not connected, so rows that match no group are dropped
- **rounds** L2494: FOOD_SHARE_OF_LINES is computed as IIF(v_ITEM_LINES_CL = 0, 0, v_FOOD_ITEM_LINES_CL / v_ITEM_LINES_CL) (L1617), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column FOOD_SHARE_OF_LINES decimal(10,4) (decision Q11)
- **rounds** L2495: DRINK_SHARE_OF_LINES is computed as IIF(v_ITEM_LINES_CL = 0, 0, v_DRINK_ITEM_LINES_CL / v_ITEM_LINES_CL) (L1618), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column DRINK_SHARE_OF_LINES decimal(10,4) (decision Q11)
- **rounds** L2502: ORDER_SUBTOTAL (double) is rounded to 2 decimal places by the target column ORDER_SUBTOTAL decimal(12,2) (decision Q11)
- **rounds** L2503: ORDER_TAX_PAID (double) is rounded to 2 decimal places by the target column ORDER_TAX_PAID decimal(12,2) (decision Q11)
- **rounds** L2509: ORDER_GROSS_MARGIN_PCT is computed as IIF(v_ITEM_REVENUE_CL = 0, 0, v_ORDER_GROSS_PROFIT_CL / v_ITEM_REVENUE_CL) (L1613), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column ORDER_GROSS_MARGIN_PCT decimal(10,4) (decision Q11)
- **rounds** L2510: EFFECTIVE_TAX_RATE is computed as IIF(SUBTOTAL = 0, 0, TAX_PAID / SUBTOTAL) (L1614), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column EFFECTIVE_TAX_RATE decimal(10,4) (decision Q11)

### m_fl_js_marts_enriched/order_item_enriched

- **master_outer** L1350: JNR_ADD_CUSTOMERS is a Master Outer Join: it keeps every row from SQ_STG_CUSTOMERS (detail) and only the rows from JNR_ADD_PRODUCTS (master) that match; JNR_ADD_PRODUCTS rows with no match are dropped
- **master_outer** L1398: JNR_ADD_LOCATIONS is a Master Outer Join: it keeps every row from SQ_STG_LOCATIONS (detail) and only the rows from JNR_ADD_CUSTOMERS (master) that match; JNR_ADD_CUSTOMERS rows with no match are dropped
- **master_outer** L1476: JNR_ADD_SUPPLIES is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT (detail) and only the rows from JNR_ADD_LOCATIONS (master) that match; JNR_ADD_LOCATIONS rows with no match are dropped
- **rounds** L2530: ITEM_GROSS_MARGIN_PCT is computed as v_MARGIN_CALC (L1504), which divides in v_MARGIN_CALC (L1513), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column ITEM_GROSS_MARGIN_PCT decimal(10,4) (decision Q11)

### m_fl_js_marts_enriched/product_daily_performance

- **master_outer** L1350: JNR_ADD_CUSTOMERS is a Master Outer Join: it keeps every row from SQ_STG_CUSTOMERS (detail) and only the rows from JNR_ADD_PRODUCTS (master) that match; JNR_ADD_PRODUCTS rows with no match are dropped
- **master_outer** L1398: JNR_ADD_LOCATIONS is a Master Outer Join: it keeps every row from SQ_STG_LOCATIONS (detail) and only the rows from JNR_ADD_CUSTOMERS (master) that match; JNR_ADD_CUSTOMERS rows with no match are dropped
- **master_outer** L1476: JNR_ADD_SUPPLIES is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT (detail) and only the rows from JNR_ADD_LOCATIONS (master) that match; JNR_ADD_LOCATIONS rows with no match are dropped
- **crossed** L2542: EXP_PRODUCT_METRICS.PERISHABLE_SALES_FLAG goes into PRODUCT_DAILY_PERFORMANCE.MARGIN_PCT, as the connector says
- **crossed** L2543: EXP_PRODUCT_METRICS.MARGIN_PCT goes into PRODUCT_DAILY_PERFORMANCE.PERISHABLE_SALES_FLAG, as the connector says
- **rounds** L2543: MARGIN_PCT is computed as IIF(REVENUE=0,0,GROSS_PROFIT/REVENUE) (L2182), a double at run time because high precision is off, and is rounded to 0 decimal places by the target column PERISHABLE_SALES_FLAG decimal(1,0) (decision Q11)

### m_fl_js_marts_enriched/store_daily_kpis

- **master_outer** L1350: JNR_ADD_CUSTOMERS is a Master Outer Join: it keeps every row from SQ_STG_CUSTOMERS (detail) and only the rows from JNR_ADD_PRODUCTS (master) that match; JNR_ADD_PRODUCTS rows with no match are dropped
- **master_outer** L1398: JNR_ADD_LOCATIONS is a Master Outer Join: it keeps every row from SQ_STG_LOCATIONS (detail) and only the rows from JNR_ADD_CUSTOMERS (master) that match; JNR_ADD_CUSTOMERS rows with no match are dropped
- **master_outer** L1476: JNR_ADD_SUPPLIES is a Master Outer Join: it keeps every row from AGG_SUPPLIES_BY_PRODUCT (detail) and only the rows from JNR_ADD_LOCATIONS (master) that match; JNR_ADD_LOCATIONS rows with no match are dropped
- **master_outer** L1591: JNR_ORDERS_ITEMS_AGG is a Master Outer Join: it keeps every row from AGG_ITEMS_BY_ORDER (detail) and only the rows from SQ_STG_ORDERS1 (master) that match; SQ_STG_ORDERS1 rows with no match are dropped
- **sort_order** L1635: SRT_FOR_CUSTOMER_SEQ is kept only to put rows in order for EXP_CUSTOMER_ORDER_NUM (decisions Q12, Q13): sort keys CUSTOMER_ID, ORDERED_AT_DAY, ORDER_ID; case is ignored (Case Sensitive = NO, L1654), so strings sort by lower(); NULLs sort high (Null Treated Low = NO, L1658)
- **counter** L1706: v_PREV_CUSTOMER_ID is set to this row's CUSTOMER_ID (L1705) before v_ORDER_SEQUENCE compares them, so the comparison is true on every row where CUSTOMER_ID is not NULL: one running number over all rows in SRT_FOR_CUSTOMER_SEQ's order that never restarts per CUSTOMER_ID, back to 1 on a row whose CUSTOMER_ID is NULL
- **router_default** L1741: RTR_ORDER_VALUE_BAND: the default group is not connected, so rows that match no group are dropped
- **master_outer** L2081: JNR_ADD_LOCATION_INFO is a Master Outer Join: it keeps every row from SQ_STG_LOCATIONS1 (detail) and only the rows from EXP_STORE_KPIS (master) that match; EXP_STORE_KPIS rows with no match are dropped
- **self_compare** L2127: v_IS_FIRST_CUSTOMER compares un_order_bands.location_id, un_order_bands.ordered_at_day, un_order_bands.customer_id with itself: the variables it reads already hold this row's values (they come earlier in port order), so each comparison is true unless the value is NULL
- **rounds** L2555: GROSS_MARGIN_PCT is computed as IIF(SUBTOTAL_TOTAL = 0, 0, GROSS_PROFIT_TOTAL / SUBTOTAL_TOTAL) (L2038), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column GROSS_MARGIN_PCT decimal(10,4) (decision Q11)
- **rounds** L2556: AVG_ORDER_VALUE is computed as IIF(ORDERS_COUNT = 0, 0, REVENUE_TOTAL / ORDERS_COUNT) (L2039), a double at run time because high precision is off, and is rounded to 2 decimal places by the target column AVG_ORDER_VALUE decimal(12,2) (decision Q11)
- **rounds** L2558: HIGH_VALUE_ORDERS_PCT is computed as IIF(ORDERS_COUNT = 0, 0, HIGH_VALUE_ORDERS / ORDERS_COUNT) (L2040), a double at run time because high precision is off, and is rounded to 4 decimal places by the target column HIGH_VALUE_ORDERS_PCT decimal(10,4) (decision Q11)

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

## Not converted

Nothing.

## Left out

- L535: Pre SQL on target STG_CUSTOMERS: TRUNCATE TABLE STG.STG_CUSTOMERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L538: Pre SQL on target STG_LOCATIONS: TRUNCATE TABLE STG.STG_LOCATIONS. Why: a dbt table is rebuilt on every run (decision Q9).
- L541: Pre SQL on target STG_ORDERS: TRUNCATE TABLE STG.STG_ORDERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L544: Pre SQL on target STG_ORDER_ITEMS: TRUNCATE TABLE STG.STG_ORDER_ITEMS. Why: a dbt table is rebuilt on every run (decision Q9).
- L547: Pre SQL on target STG_PRODUCTS: TRUNCATE TABLE STG.STG_PRODUCTS. Why: a dbt table is rebuilt on every run (decision Q9).
- L550: Pre SQL on target STG_SUPPLIES: TRUNCATE TABLE STG.STG_SUPPLIES. Why: a dbt table is rebuilt on every run (decision Q9).
- L2389: Pre SQL on target CUSTOMER_360: TRUNCATE TABLE MART.CUSTOMER_360. Why: a dbt table is rebuilt on every run (decision Q9).
- L2392: Pre SQL on target ORDER_FINANCIALS1: TRUNCATE TABLE MART.ORDER_FINANCIALS. Why: a dbt table is rebuilt on every run (decision Q9).
- L2395: Pre SQL on target ORDER_ITEM_ENRICHED: TRUNCATE TABLE MART.ORDER_ITEM_ENRICHED. Why: a dbt table is rebuilt on every run (decision Q9).
- L2398: Pre SQL on target PRODUCT_DAILY_PERFORMANCE: TRUNCATE TABLE MART.PRODUCT_DAILY_PERFORMANCE. Why: a dbt table is rebuilt on every run (decision Q9).
- L2401: Pre SQL on target STORE_DAILY_KPIS: TRUNCATE TABLE MART.STORE_DAILY_KPIS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3691: Pre SQL on target CUSTOMERS: TRUNCATE TABLE MART.CUSTOMERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3694: Pre SQL on target ORDERS: TRUNCATE TABLE MART.ORDERS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3697: Pre SQL on target ORDER_ITEMS: TRUNCATE TABLE MART.ORDER_ITEMS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3700: Pre SQL on target PRODUCTS: TRUNCATE TABLE MART.PRODUCTS. Why: a dbt table is rebuilt on every run (decision Q9).
- L3703: Pre SQL on target SUPPLIES: TRUNCATE TABLE MART.SUPPLIES. Why: a dbt table is rebuilt on every run (decision Q9).
- L4054: Workflow wf_FL_JAFFLESHOP_DEMO (run order, links and failure handling). Why: dbt orders models from ref(); behaviour on failure is out of scope (decisions Q5, Q17).
- L4058: Command task cmd_FL_JS_CREATE_RPT_VIEWS (its command is never read). Why: not part of any mapping (decision Q17).
- L811: Session s_FL_JS_STAGING_FULL (connections and load settings). Why: connections come from the dbt profile; load settings from materialization (decision Q17).
- L4064: Session s_FL_JS_MARTS_CORE (connections and load settings). Why: connections come from the dbt profile; load settings from materialization (decision Q17).
- L4299: Session s_FL_JS_MARTS_ENRICHED (connections and load settings). Why: connections come from the dbt profile; load settings from materialization (decision Q17).
