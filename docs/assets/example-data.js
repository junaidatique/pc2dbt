/* GENERATED from the demo XML (FLOWLINE_DEMO_JAFFLESHOP.xml) by a script. Do not edit by hand.
   Slice: RAW_ORDERS -> STG_ORDERS in mapping m_FL_JS_STAGING_FULL, plus its session and workflow.
   Every line number is read from the file. Attributes are trimmed to the ones that matter. */
window.EXAMPLE = {
 "xmlFile": "FLOWLINE_DEMO_JAFFLESHOP.xml",
 "mapping": {
  "name": "m_FL_JS_STAGING_FULL",
  "start": 90,
  "end": 769
 },
 "nodes": [
  {
   "id": "RAW_ORDERS",
   "type": "Source",
   "start": 26,
   "end": 34,
   "instanceLine": 574,
   "lines": [
    [
     26,
     "<SOURCE NAME=\"RAW_ORDERS\" OWNERNAME=\"RAW\" DATABASETYPE=\"Oracle\">"
    ],
    [
     27,
     "<SOURCEFIELD NAME=\"ID\" DATATYPE=\"varchar2\"/>"
    ],
    [
     28,
     "<SOURCEFIELD NAME=\"CUSTOMER\" DATATYPE=\"varchar2\"/>"
    ],
    [
     29,
     "<SOURCEFIELD NAME=\"ORDERED_AT\" DATATYPE=\"timestamp\"/>"
    ],
    [
     30,
     "<SOURCEFIELD NAME=\"STORE_ID\" DATATYPE=\"varchar2\"/>"
    ],
    [
     31,
     "<SOURCEFIELD NAME=\"SUBTOTAL\" DATATYPE=\"number\"/>"
    ],
    [
     32,
     "<SOURCEFIELD NAME=\"TAX_PAID\" DATATYPE=\"number\"/>"
    ],
    [
     33,
     "<SOURCEFIELD NAME=\"ORDER_TOTAL\" DATATYPE=\"number(p,s)\"/>"
    ],
    [
     34,
     "</SOURCE>"
    ]
   ],
   "wiresIn": []
  },
  {
   "id": "SQ_RAW_ORDERS",
   "type": "Source Qualifier",
   "start": 161,
   "end": 180,
   "instanceLine": 562,
   "lines": [
    [
     161,
     "<TRANSFORMATION NAME=\"SQ_RAW_ORDERS\" TYPE=\"Source Qualifier\">"
    ],
    [
     162,
     "<TRANSFORMFIELD NAME=\"ID\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     163,
     "<TRANSFORMFIELD NAME=\"CUSTOMER\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     164,
     "<TRANSFORMFIELD NAME=\"ORDERED_AT\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     165,
     "<TRANSFORMFIELD NAME=\"STORE_ID\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     166,
     "<TRANSFORMFIELD NAME=\"SUBTOTAL\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     167,
     "<TRANSFORMFIELD NAME=\"TAX_PAID\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     168,
     "<TRANSFORMFIELD NAME=\"ORDER_TOTAL\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     169,
     "<TABLEATTRIBUTE NAME=\"Sql Query\" VALUE=\"\"/>"
    ],
    [
     170,
     "<TABLEATTRIBUTE NAME=\"User Defined Join\" VALUE=\"\"/>"
    ],
    [
     171,
     "<TABLEATTRIBUTE NAME=\"Source Filter\" VALUE=\"\"/>"
    ],
    [
     null,
     "…"
    ],
    [
     174,
     "<TABLEATTRIBUTE NAME=\"Select Distinct\" VALUE=\"NO\"/>"
    ],
    [
     null,
     "…"
    ],
    [
     180,
     "</TRANSFORMATION>"
    ]
   ],
   "wiresIn": [
    [
     668,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"ID\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"ID\"/>"
    ],
    [
     669,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"CUSTOMER\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"CUSTOMER\"/>"
    ],
    [
     670,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"ORDERED_AT\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"ORDERED_AT\"/>"
    ],
    [
     671,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"STORE_ID\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"STORE_ID\"/>"
    ],
    [
     672,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"SUBTOTAL\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"SUBTOTAL\"/>"
    ],
    [
     673,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"TAX_PAID\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"TAX_PAID\"/>"
    ],
    [
     674,
     "<CONNECTOR FROMINSTANCE=\"RAW_ORDERS\" FROMFIELD=\"ORDER_TOTAL\" TOINSTANCE=\"SQ_RAW_ORDERS\" TOFIELD=\"ORDER_TOTAL\"/>"
    ]
   ]
  },
  {
   "id": "EXP_ORDERS",
   "type": "Expression",
   "start": 106,
   "end": 125,
   "instanceLine": 555,
   "lines": [
    [
     106,
     "<TRANSFORMATION NAME=\"EXP_ORDERS\" TYPE=\"Expression\">"
    ],
    [
     107,
     "<TRANSFORMFIELD NAME=\"ORDER_ID\" EXPRESSION=\"ID\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     108,
     "<TRANSFORMFIELD NAME=\"CUSTOMER_ID\" EXPRESSION=\"CUSTOMER\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     109,
     "<TRANSFORMFIELD NAME=\"LOCATION_ID\" EXPRESSION=\"STORE_ID\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     110,
     "<TRANSFORMFIELD NAME=\"ORDERED_AT_DAY\" EXPRESSION=\"TO_DATE(TO_CHAR(ORDERED_AT, 'DD-MM-YY'), 'DD-MM-YY')\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     111,
     "<TRANSFORMFIELD NAME=\"SUBTOTAL\" EXPRESSION=\"SUBTOTAL_IN/100\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     112,
     "<TRANSFORMFIELD NAME=\"TAX_PAID\" EXPRESSION=\"TAX_PAID_IN/100\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     113,
     "<TRANSFORMFIELD NAME=\"ORDER_TOTAL\" EXPRESSION=\"ORDER_TOTAL_IN/100\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     114,
     "<TRANSFORMFIELD NAME=\"SUBTOTAL_CENTS\" EXPRESSION=\"SUBTOTAL_IN\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     115,
     "<TRANSFORMFIELD NAME=\"TAX_PAID_CENTS\" EXPRESSION=\"TAX_PAID_IN\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     116,
     "<TRANSFORMFIELD NAME=\"ORDER_TOTAL_CENTS\" EXPRESSION=\"ORDER_TOTAL_IN\" PORTTYPE=\"OUTPUT\"/>"
    ],
    [
     117,
     "<TRANSFORMFIELD NAME=\"ID\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     118,
     "<TRANSFORMFIELD NAME=\"CUSTOMER\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     119,
     "<TRANSFORMFIELD NAME=\"STORE_ID\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     120,
     "<TRANSFORMFIELD NAME=\"ORDERED_AT\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     121,
     "<TRANSFORMFIELD NAME=\"SUBTOTAL_IN\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     122,
     "<TRANSFORMFIELD NAME=\"TAX_PAID_IN\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     123,
     "<TRANSFORMFIELD NAME=\"ORDER_TOTAL_IN\" PORTTYPE=\"INPUT\"/>"
    ],
    [
     null,
     "…"
    ],
    [
     125,
     "</TRANSFORMATION>"
    ]
   ],
   "wiresIn": [
    [
     643,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"ID\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"ID\"/>"
    ],
    [
     644,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"ORDERED_AT\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"ORDERED_AT\"/>"
    ],
    [
     645,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"STORE_ID\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"STORE_ID\"/>"
    ],
    [
     646,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"CUSTOMER\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"CUSTOMER\"/>"
    ],
    [
     647,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"SUBTOTAL\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"SUBTOTAL_IN\"/>"
    ],
    [
     648,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"TAX_PAID\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"TAX_PAID_IN\"/>"
    ],
    [
     649,
     "<CONNECTOR FROMINSTANCE=\"SQ_RAW_ORDERS\" FROMFIELD=\"ORDER_TOTAL\" TOINSTANCE=\"EXP_ORDERS\" TOFIELD=\"ORDER_TOTAL_IN\"/>"
    ]
   ]
  },
  {
   "id": "SRT_ORDERS",
   "type": "Sorter",
   "start": 513,
   "end": 533,
   "instanceLine": 596,
   "lines": [
    [
     513,
     "<TRANSFORMATION NAME=\"SRT_ORDERS\" TYPE=\"Sorter\">"
    ],
    [
     514,
     "<TRANSFORMFIELD NAME=\"ORDER_ID\" PORTTYPE=\"INPUT/OUTPUT\" ISSORTKEY=\"YES\"/>"
    ],
    [
     515,
     "<TRANSFORMFIELD NAME=\"CUSTOMER_ID\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     516,
     "<TRANSFORMFIELD NAME=\"LOCATION_ID\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     517,
     "<TRANSFORMFIELD NAME=\"ORDERED_AT_DAY\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     518,
     "<TRANSFORMFIELD NAME=\"SUBTOTAL\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     519,
     "<TRANSFORMFIELD NAME=\"TAX_PAID\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     520,
     "<TRANSFORMFIELD NAME=\"ORDER_TOTAL\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     521,
     "<TRANSFORMFIELD NAME=\"SUBTOTAL_CENTS\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     522,
     "<TRANSFORMFIELD NAME=\"TAX_PAID_CENTS\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     523,
     "<TRANSFORMFIELD NAME=\"ORDER_TOTAL_CENTS\" PORTTYPE=\"INPUT/OUTPUT\"/>"
    ],
    [
     null,
     "…"
    ],
    [
     527,
     "<TABLEATTRIBUTE NAME=\"Distinct\" VALUE=\"NO\"/>"
    ],
    [
     null,
     "…"
    ],
    [
     533,
     "</TRANSFORMATION>"
    ]
   ],
   "wiresIn": [
    [
     633,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"ORDER_ID\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"ORDER_ID\"/>"
    ],
    [
     634,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"CUSTOMER_ID\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"CUSTOMER_ID\"/>"
    ],
    [
     635,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"LOCATION_ID\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"LOCATION_ID\"/>"
    ],
    [
     636,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"ORDERED_AT_DAY\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"ORDERED_AT_DAY\"/>"
    ],
    [
     637,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"SUBTOTAL\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"SUBTOTAL\"/>"
    ],
    [
     638,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"TAX_PAID\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"TAX_PAID\"/>"
    ],
    [
     639,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"ORDER_TOTAL\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"ORDER_TOTAL\"/>"
    ],
    [
     640,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"SUBTOTAL_CENTS\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"SUBTOTAL_CENTS\"/>"
    ],
    [
     641,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"TAX_PAID_CENTS\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"TAX_PAID_CENTS\"/>"
    ],
    [
     642,
     "<CONNECTOR FROMINSTANCE=\"EXP_ORDERS\" FROMFIELD=\"ORDER_TOTAL_CENTS\" TOINSTANCE=\"SRT_ORDERS\" TOFIELD=\"ORDER_TOTAL_CENTS\"/>"
    ]
   ]
  },
  {
   "id": "STG_ORDERS",
   "type": "Target",
   "start": 67,
   "end": 78,
   "instanceLine": 540,
   "lines": [
    [
     67,
     "<TARGET NAME=\"STG_ORDERS\" DATABASETYPE=\"Oracle\">"
    ],
    [
     68,
     "<TARGETFIELD NAME=\"ORDER_ID\" DATATYPE=\"varchar2\"/>"
    ],
    [
     69,
     "<TARGETFIELD NAME=\"CUSTOMER_ID\" DATATYPE=\"varchar2\"/>"
    ],
    [
     70,
     "<TARGETFIELD NAME=\"LOCATION_ID\" DATATYPE=\"varchar2\"/>"
    ],
    [
     71,
     "<TARGETFIELD NAME=\"ORDERED_AT_DAY\" DATATYPE=\"date\"/>"
    ],
    [
     72,
     "<TARGETFIELD NAME=\"SUBTOTAL_CENTS\" DATATYPE=\"number\"/>"
    ],
    [
     73,
     "<TARGETFIELD NAME=\"TAX_PAID_CENTS\" DATATYPE=\"number\"/>"
    ],
    [
     74,
     "<TARGETFIELD NAME=\"ORDER_TOTAL_CENTS\" DATATYPE=\"number(p,s)\"/>"
    ],
    [
     75,
     "<TARGETFIELD NAME=\"SUBTOTAL\" DATATYPE=\"number\"/>"
    ],
    [
     76,
     "<TARGETFIELD NAME=\"TAX_PAID\" DATATYPE=\"number\"/>"
    ],
    [
     77,
     "<TARGETFIELD NAME=\"ORDER_TOTAL\" DATATYPE=\"number(p,s)\"/>"
    ],
    [
     78,
     "</TARGET>"
    ]
   ],
   "wiresIn": [
    [
     604,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"ORDER_ID\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"ORDER_ID\"/>"
    ],
    [
     605,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"CUSTOMER_ID\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"CUSTOMER_ID\"/>"
    ],
    [
     606,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"LOCATION_ID\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"LOCATION_ID\"/>"
    ],
    [
     607,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"ORDERED_AT_DAY\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"ORDERED_AT_DAY\"/>"
    ],
    [
     608,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"SUBTOTAL\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"SUBTOTAL_CENTS\"/>"
    ],
    [
     609,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"TAX_PAID\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"TAX_PAID_CENTS\"/>"
    ],
    [
     610,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"ORDER_TOTAL\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"ORDER_TOTAL_CENTS\"/>"
    ],
    [
     611,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"SUBTOTAL_CENTS\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"SUBTOTAL\"/>"
    ],
    [
     612,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"TAX_PAID_CENTS\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"TAX_PAID\"/>"
    ],
    [
     613,
     "<CONNECTOR FROMINSTANCE=\"SRT_ORDERS\" FROMFIELD=\"ORDER_TOTAL_CENTS\" TOINSTANCE=\"STG_ORDERS\" TOFIELD=\"ORDER_TOTAL\"/>"
    ]
   ]
  }
 ],
 "wireCounts": [
  {
   "from": "RAW_ORDERS",
   "to": "SQ_RAW_ORDERS",
   "count": 7
  },
  {
   "from": "SQ_RAW_ORDERS",
   "to": "EXP_ORDERS",
   "count": 7
  },
  {
   "from": "EXP_ORDERS",
   "to": "SRT_ORDERS",
   "count": 10
  },
  {
   "from": "SRT_ORDERS",
   "to": "STG_ORDERS",
   "count": 10
  }
 ],
 "session": {
  "name": "s_FL_JS_STAGING_FULL",
  "start": 811,
  "lines": [
   [
    811,
    "<SESSION NAME=\"s_FL_JS_STAGING_FULL\" MAPPINGNAME=\"m_FL_JS_STAGING_FULL\">"
   ],
   [
    null,
    "…"
   ],
   [
    814,
    "<SESSTRANSFORMATIONINST SINSTANCENAME=\"STG_ORDERS\" TRANSFORMATIONTYPE=\"Target Definition\"/>"
   ],
   [
    null,
    "…"
   ],
   [
    820,
    "<SESSTRANSFORMATIONINST SINSTANCENAME=\"EXP_ORDERS\" TRANSFORMATIONTYPE=\"Expression\">"
   ],
   [
    null,
    "…"
   ],
   [
    827,
    "<SESSTRANSFORMATIONINST SINSTANCENAME=\"RAW_ORDERS\" TRANSFORMATIONTYPE=\"Source Definition\"/>"
   ],
   [
    828,
    "<SESSTRANSFORMATIONINST SINSTANCENAME=\"SQ_RAW_ORDERS\" TRANSFORMATIONTYPE=\"Source Qualifier\"/>"
   ],
   [
    null,
    "…"
   ],
   [
    883,
    "<SESSTRANSFORMATIONINST SINSTANCENAME=\"SRT_ORDERS\" TRANSFORMATIONTYPE=\"Sorter\">"
   ],
   [
    null,
    "…"
   ],
   [
    911,
    "<SESSIONEXTENSION NAME=\"Relational Writer\" SINSTANCENAME=\"STG_ORDERS\" TYPE=\"WRITER\">"
   ],
   [
    912,
    "<CONNECTIONREFERENCE CONNECTIONNAME=\"MART_Jaffleshop\" CONNECTIONTYPE=\"Relational\"/>"
   ],
   [
    913,
    "<ATTRIBUTE NAME=\"Target load type\" VALUE=\"Bulk\"/>"
   ],
   [
    914,
    "<ATTRIBUTE NAME=\"Insert\" VALUE=\"YES\"/>"
   ],
   [
    null,
    "…"
   ],
   [
    919,
    "<ATTRIBUTE NAME=\"Truncate target table option\" VALUE=\"NO\"/>"
   ],
   [
    null,
    "…"
   ],
   [
    922,
    "</SESSIONEXTENSION>"
   ],
   [
    null,
    "…"
   ],
   [
    995,
    "<ATTRIBUTE NAME=\"Treat source rows as\" VALUE=\"Insert\"/>"
   ]
  ]
 },
 "workflow": {
  "name": "wf_FL_JAFFLESHOP_DEMO",
  "start": 4054,
  "lines": [
   [
    4054,
    "<WORKFLOW NAME=\"wf_FL_JAFFLESHOP_DEMO\">"
   ],
   [
    null,
    "…"
   ],
   [
    4056,
    "<SCHEDULEINFO SCHEDULETYPE=\"ONDEMAND\"/>"
   ],
   [
    null,
    "…"
   ],
   [
    4058,
    "<TASK NAME=\"cmd_FL_JS_CREATE_RPT_VIEWS\" TYPE=\"Command\">"
   ],
   [
    null,
    "…"
   ],
   [
    4063,
    "<TASK NAME=\"Start\" TYPE=\"Start\"/>"
   ],
   [
    null,
    "…"
   ],
   [
    4577,
    "<TASKINSTANCE NAME=\"cmd_FL_JS_CREATE_RPT_VIEWS\" TASKTYPE=\"Command\"/>"
   ],
   [
    4578,
    "<TASKINSTANCE NAME=\"Start\" TASKTYPE=\"Start\"/>"
   ],
   [
    4579,
    "<TASKINSTANCE NAME=\"s_FL_JS_STAGING_FULL\" TASKTYPE=\"Session\">"
   ],
   [
    null,
    "…"
   ],
   [
    4620,
    "<TASKINSTANCE NAME=\"s_FL_JS_MARTS_CORE\" TASKTYPE=\"Session\"/>"
   ],
   [
    4621,
    "<TASKINSTANCE NAME=\"s_FL_JS_MARTS_ENRICHED\" TASKTYPE=\"Session\"/>"
   ],
   [
    4622,
    "<WORKFLOWLINK FROMTASK=\"s_FL_JS_MARTS_ENRICHED\" TOTASK=\"cmd_FL_JS_CREATE_RPT_VIEWS\"/>"
   ],
   [
    4623,
    "<WORKFLOWLINK FROMTASK=\"Start\" TOTASK=\"s_FL_JS_STAGING_FULL\"/>"
   ],
   [
    4624,
    "<WORKFLOWLINK FROMTASK=\"s_FL_JS_STAGING_FULL\" TOTASK=\"s_FL_JS_MARTS_CORE\"/>"
   ],
   [
    4625,
    "<WORKFLOWLINK FROMTASK=\"s_FL_JS_MARTS_CORE\" TOTASK=\"s_FL_JS_MARTS_ENRICHED\"/>"
   ]
  ],
  "links": [
   {
    "CONDITION": "",
    "FROMTASK": "s_FL_JS_MARTS_ENRICHED",
    "TOTASK": "cmd_FL_JS_CREATE_RPT_VIEWS"
   },
   {
    "CONDITION": "",
    "FROMTASK": "Start",
    "TOTASK": "s_FL_JS_STAGING_FULL"
   },
   {
    "CONDITION": "",
    "FROMTASK": "s_FL_JS_STAGING_FULL",
    "TOTASK": "s_FL_JS_MARTS_CORE"
   },
   {
    "CONDITION": "",
    "FROMTASK": "s_FL_JS_MARTS_CORE",
    "TOTASK": "s_FL_JS_MARTS_ENRICHED"
   }
  ]
 },
 "targetColumns": [
  "ORDER_ID",
  "CUSTOMER_ID",
  "LOCATION_ID",
  "ORDERED_AT_DAY",
  "SUBTOTAL_CENTS",
  "TAX_PAID_CENTS",
  "ORDER_TOTAL_CENTS",
  "SUBTOTAL",
  "TAX_PAID",
  "ORDER_TOTAL"
 ],
 "lineage": {
  "ORDER_ID": [
   {
    "n": 604,
    "text": "STG_ORDERS.ORDER_ID ← SRT_ORDERS.ORDER_ID",
    "kind": "connector"
   },
   {
    "n": 633,
    "text": "SRT_ORDERS.ORDER_ID ← EXP_ORDERS.ORDER_ID",
    "kind": "connector"
   },
   {
    "n": 107,
    "text": "EXP_ORDERS.ORDER_ID = ID",
    "kind": "port expression"
   },
   {
    "n": 643,
    "text": "EXP_ORDERS.ID ← SQ_RAW_ORDERS.ID",
    "kind": "connector"
   },
   {
    "n": 668,
    "text": "SQ_RAW_ORDERS.ID ← RAW_ORDERS.ID",
    "kind": "connector"
   },
   {
    "n": 27,
    "text": "RAW_ORDERS.ID",
    "kind": "PC Source column"
   }
  ],
  "CUSTOMER_ID": [
   {
    "n": 605,
    "text": "STG_ORDERS.CUSTOMER_ID ← SRT_ORDERS.CUSTOMER_ID",
    "kind": "connector"
   },
   {
    "n": 634,
    "text": "SRT_ORDERS.CUSTOMER_ID ← EXP_ORDERS.CUSTOMER_ID",
    "kind": "connector"
   },
   {
    "n": 108,
    "text": "EXP_ORDERS.CUSTOMER_ID = CUSTOMER",
    "kind": "port expression"
   },
   {
    "n": 646,
    "text": "EXP_ORDERS.CUSTOMER ← SQ_RAW_ORDERS.CUSTOMER",
    "kind": "connector"
   },
   {
    "n": 669,
    "text": "SQ_RAW_ORDERS.CUSTOMER ← RAW_ORDERS.CUSTOMER",
    "kind": "connector"
   },
   {
    "n": 28,
    "text": "RAW_ORDERS.CUSTOMER",
    "kind": "PC Source column"
   }
  ],
  "LOCATION_ID": [
   {
    "n": 606,
    "text": "STG_ORDERS.LOCATION_ID ← SRT_ORDERS.LOCATION_ID",
    "kind": "connector"
   },
   {
    "n": 635,
    "text": "SRT_ORDERS.LOCATION_ID ← EXP_ORDERS.LOCATION_ID",
    "kind": "connector"
   },
   {
    "n": 109,
    "text": "EXP_ORDERS.LOCATION_ID = STORE_ID",
    "kind": "port expression"
   },
   {
    "n": 645,
    "text": "EXP_ORDERS.STORE_ID ← SQ_RAW_ORDERS.STORE_ID",
    "kind": "connector"
   },
   {
    "n": 671,
    "text": "SQ_RAW_ORDERS.STORE_ID ← RAW_ORDERS.STORE_ID",
    "kind": "connector"
   },
   {
    "n": 30,
    "text": "RAW_ORDERS.STORE_ID",
    "kind": "PC Source column"
   }
  ],
  "ORDERED_AT_DAY": [
   {
    "n": 607,
    "text": "STG_ORDERS.ORDERED_AT_DAY ← SRT_ORDERS.ORDERED_AT_DAY",
    "kind": "connector"
   },
   {
    "n": 636,
    "text": "SRT_ORDERS.ORDERED_AT_DAY ← EXP_ORDERS.ORDERED_AT_DAY",
    "kind": "connector"
   },
   {
    "n": 110,
    "text": "EXP_ORDERS.ORDERED_AT_DAY = TO_DATE(TO_CHAR(ORDERED_AT, 'DD-MM-YY'), 'DD-MM-YY')",
    "kind": "port expression"
   },
   {
    "n": 644,
    "text": "EXP_ORDERS.ORDERED_AT ← SQ_RAW_ORDERS.ORDERED_AT",
    "kind": "connector"
   },
   {
    "n": 670,
    "text": "SQ_RAW_ORDERS.ORDERED_AT ← RAW_ORDERS.ORDERED_AT",
    "kind": "connector"
   },
   {
    "n": 29,
    "text": "RAW_ORDERS.ORDERED_AT",
    "kind": "PC Source column"
   }
  ],
  "SUBTOTAL_CENTS": [
   {
    "n": 608,
    "text": "STG_ORDERS.SUBTOTAL_CENTS ← SRT_ORDERS.SUBTOTAL",
    "kind": "connector",
    "flag": true
   },
   {
    "n": 637,
    "text": "SRT_ORDERS.SUBTOTAL ← EXP_ORDERS.SUBTOTAL",
    "kind": "connector"
   },
   {
    "n": 111,
    "text": "EXP_ORDERS.SUBTOTAL = SUBTOTAL_IN/100",
    "kind": "port expression"
   },
   {
    "n": 647,
    "text": "EXP_ORDERS.SUBTOTAL_IN ← SQ_RAW_ORDERS.SUBTOTAL",
    "kind": "connector"
   },
   {
    "n": 672,
    "text": "SQ_RAW_ORDERS.SUBTOTAL ← RAW_ORDERS.SUBTOTAL",
    "kind": "connector"
   },
   {
    "n": 31,
    "text": "RAW_ORDERS.SUBTOTAL",
    "kind": "PC Source column"
   }
  ],
  "TAX_PAID_CENTS": [
   {
    "n": 609,
    "text": "STG_ORDERS.TAX_PAID_CENTS ← SRT_ORDERS.TAX_PAID",
    "kind": "connector",
    "flag": true
   },
   {
    "n": 638,
    "text": "SRT_ORDERS.TAX_PAID ← EXP_ORDERS.TAX_PAID",
    "kind": "connector"
   },
   {
    "n": 112,
    "text": "EXP_ORDERS.TAX_PAID = TAX_PAID_IN/100",
    "kind": "port expression"
   },
   {
    "n": 648,
    "text": "EXP_ORDERS.TAX_PAID_IN ← SQ_RAW_ORDERS.TAX_PAID",
    "kind": "connector"
   },
   {
    "n": 673,
    "text": "SQ_RAW_ORDERS.TAX_PAID ← RAW_ORDERS.TAX_PAID",
    "kind": "connector"
   },
   {
    "n": 32,
    "text": "RAW_ORDERS.TAX_PAID",
    "kind": "PC Source column"
   }
  ],
  "ORDER_TOTAL_CENTS": [
   {
    "n": 610,
    "text": "STG_ORDERS.ORDER_TOTAL_CENTS ← SRT_ORDERS.ORDER_TOTAL",
    "kind": "connector",
    "flag": true
   },
   {
    "n": 639,
    "text": "SRT_ORDERS.ORDER_TOTAL ← EXP_ORDERS.ORDER_TOTAL",
    "kind": "connector"
   },
   {
    "n": 113,
    "text": "EXP_ORDERS.ORDER_TOTAL = ORDER_TOTAL_IN/100",
    "kind": "port expression"
   },
   {
    "n": 649,
    "text": "EXP_ORDERS.ORDER_TOTAL_IN ← SQ_RAW_ORDERS.ORDER_TOTAL",
    "kind": "connector"
   },
   {
    "n": 674,
    "text": "SQ_RAW_ORDERS.ORDER_TOTAL ← RAW_ORDERS.ORDER_TOTAL",
    "kind": "connector"
   },
   {
    "n": 33,
    "text": "RAW_ORDERS.ORDER_TOTAL",
    "kind": "PC Source column"
   }
  ],
  "SUBTOTAL": [
   {
    "n": 611,
    "text": "STG_ORDERS.SUBTOTAL ← SRT_ORDERS.SUBTOTAL_CENTS",
    "kind": "connector",
    "flag": true
   },
   {
    "n": 640,
    "text": "SRT_ORDERS.SUBTOTAL_CENTS ← EXP_ORDERS.SUBTOTAL_CENTS",
    "kind": "connector"
   },
   {
    "n": 114,
    "text": "EXP_ORDERS.SUBTOTAL_CENTS = SUBTOTAL_IN",
    "kind": "port expression"
   },
   {
    "n": 647,
    "text": "EXP_ORDERS.SUBTOTAL_IN ← SQ_RAW_ORDERS.SUBTOTAL",
    "kind": "connector"
   },
   {
    "n": 672,
    "text": "SQ_RAW_ORDERS.SUBTOTAL ← RAW_ORDERS.SUBTOTAL",
    "kind": "connector"
   },
   {
    "n": 31,
    "text": "RAW_ORDERS.SUBTOTAL",
    "kind": "PC Source column"
   }
  ],
  "TAX_PAID": [
   {
    "n": 612,
    "text": "STG_ORDERS.TAX_PAID ← SRT_ORDERS.TAX_PAID_CENTS",
    "kind": "connector",
    "flag": true
   },
   {
    "n": 641,
    "text": "SRT_ORDERS.TAX_PAID_CENTS ← EXP_ORDERS.TAX_PAID_CENTS",
    "kind": "connector"
   },
   {
    "n": 115,
    "text": "EXP_ORDERS.TAX_PAID_CENTS = TAX_PAID_IN",
    "kind": "port expression"
   },
   {
    "n": 648,
    "text": "EXP_ORDERS.TAX_PAID_IN ← SQ_RAW_ORDERS.TAX_PAID",
    "kind": "connector"
   },
   {
    "n": 673,
    "text": "SQ_RAW_ORDERS.TAX_PAID ← RAW_ORDERS.TAX_PAID",
    "kind": "connector"
   },
   {
    "n": 32,
    "text": "RAW_ORDERS.TAX_PAID",
    "kind": "PC Source column"
   }
  ],
  "ORDER_TOTAL": [
   {
    "n": 613,
    "text": "STG_ORDERS.ORDER_TOTAL ← SRT_ORDERS.ORDER_TOTAL_CENTS",
    "kind": "connector",
    "flag": true
   },
   {
    "n": 642,
    "text": "SRT_ORDERS.ORDER_TOTAL_CENTS ← EXP_ORDERS.ORDER_TOTAL_CENTS",
    "kind": "connector"
   },
   {
    "n": 116,
    "text": "EXP_ORDERS.ORDER_TOTAL_CENTS = ORDER_TOTAL_IN",
    "kind": "port expression"
   },
   {
    "n": 649,
    "text": "EXP_ORDERS.ORDER_TOTAL_IN ← SQ_RAW_ORDERS.ORDER_TOTAL",
    "kind": "connector"
   },
   {
    "n": 674,
    "text": "SQ_RAW_ORDERS.ORDER_TOTAL ← RAW_ORDERS.ORDER_TOTAL",
    "kind": "connector"
   },
   {
    "n": 33,
    "text": "RAW_ORDERS.ORDER_TOTAL",
    "kind": "PC Source column"
   }
  ]
 },
 "flags": [
  {
   "n": 608,
   "column": "SUBTOTAL_CENTS",
   "from": "SRT_ORDERS.SUBTOTAL"
  },
  {
   "n": 609,
   "column": "TAX_PAID_CENTS",
   "from": "SRT_ORDERS.TAX_PAID"
  },
  {
   "n": 610,
   "column": "ORDER_TOTAL_CENTS",
   "from": "SRT_ORDERS.ORDER_TOTAL"
  },
  {
   "n": 611,
   "column": "SUBTOTAL",
   "from": "SRT_ORDERS.SUBTOTAL_CENTS"
  },
  {
   "n": 612,
   "column": "TAX_PAID",
   "from": "SRT_ORDERS.TAX_PAID_CENTS"
  },
  {
   "n": 613,
   "column": "ORDER_TOTAL",
   "from": "SRT_ORDERS.ORDER_TOTAL_CENTS"
  }
 ]
};
