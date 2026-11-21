/* Decisions waiting for the user. Nothing here is decided: "rec" is only the agent's recommendation.
 * Fields: id, group, title (the question), eli5 (plain explanation), example (from our data),
 *         options [{k, label, what}], rec (option key), why.
 * "L608" style refs become links to the demo XML.
 */
window.DECISIONS = {
  decided: [
    "D1: follow the connectors, copy what the XML does, and flag it. Don't fix it.",
    "D2: the reference is dbt-labs/jaffle-shop.",
    "D3: the credential in the command task is never shown, copied or committed.",
    "Model names come from the table, not the instance (prompt 6).",
    "The repo will be public, and the deadline is 24 Nov 2026."
  ],
  groups: ["Getting set up", "Shape of the dbt project", "Copying the XML exactly (how D1 applies)", "Edges", "Checking"],
  items: [
    { id: "Q1", group: "Getting set up", title: "How do we run jaffle-shop on DuckDB?",
      eli5: "To check our tables we need the answer sheet: jaffle-shop's own tables. Its newest version wants a newer dbt than the one that works with DuckDB, so we have to pick a way round that.",
      example: "All three ways built the whole project on the seed data: 49 of 49 steps passed, with 935 customers and 61,948 orders.",
      options: [
        { k: "A", label: "dbt 2 on the newest version", what: "Works, but dbt 2 has an older DuckDB inside that couldn't open a database file written by the current DuckDB Python package (2.0.1)." },
        { k: "B", label: "dbt 1.12 on the newest version", what: "Every command needs --no-version-check to get past the version rule." },
        { k: "C", label: "dbt 1.12 on an older commit (7d0d8de)", what: "Pinned to a commit from 27 Jul 2026. Only the README, Taskfile and config changed after it; the model files are identical." }
      ],
      rec: "C", why: "Same models as the newest version, with standard open-source dbt, no special flags, and one DuckDB version for both projects." },

    { id: "Q2", group: "Getting set up", title: "Which language is the converter written in?",
      eli5: "The converter is a program that reads the XML and writes SQL files. We need to pick its language and how we test it.",
      example: "The scripts behind these pages are already Python. One reads the XML and keeps every element's line number; that's how every L-link on these pages works.",
      options: [
        { k: "A", label: "Python, tested with pytest", what: "Same language as dbt and our scripts; the line-aware XML reader can be reused." },
        { k: "B", label: "TypeScript, tested with Vitest", what: "Fine for parsing, but adds a second toolchain next to dbt's Python." },
        { k: "C", label: "Another language (Go, Java…)", what: "Possible, but nothing in the task needs it." }
      ],
      rec: "A", why: "One toolchain for the converter, dbt and the checks, and the reader that already gives exact line numbers." },

    { id: "Q3", group: "Getting set up", title: "Do we convert all 3 mappings?",
      eli5: "There are 3 recipe cards. We can convert all of them, or only the ones we can check against the answer sheet.",
      example: "Staging (6 tables) and core (5) have twins in jaffle-shop. Enriched (5) has none. Aggregators appear only in the two mart mappings, and the only Filter is in enriched (L2385).",
      options: [
        { k: "A", label: "All 3 (16 models)", what: "Every box type gets used. Enriched is checked only by our own tests." },
        { k: "B", label: "Staging and core (11 models)", what: "Everything can be compared with jaffle-shop, but the Filter is never used." },
        { k: "C", label: "Staging only (6 models)", what: "Smallest, but skips Aggregators and the Filter." }
      ],
      rec: "A", why: "The converter is generic anyway, and the brief grades conversion logic. Enriched is where the Filter and several of the bugs live." },

    { id: "Q4", group: "Shape of the dbt project", title: "One dbt model per PC Target? (open question O2)",
      eli5: "A dbt model is one SQL file that builds one table. A mapping can fill several tables, so it has to be split into several files.",
      example: "Staging and core have no shared boxes: every table has its own path. In enriched, 26 of the 45 boxes feed two or more of its 5 tables, so one-model-per-table repeats that shared trunk in each file.",
      options: [
        { k: "A", label: "One model per target, shared boxes repeated", what: "Simplest: walk back from each table. Each file stands on its own; enriched files get long." },
        { k: "B", label: "One model per target, plus a shared model for boxes that feed several tables", what: "No repetition, but the converter must find where paths split and pass the right columns." },
        { k: "C", label: "One model per box", what: "98 small files: very traceable, hard to read." }
      ],
      rec: "A", why: "Each file reads top to bottom on its own, which is what you need to explain any line, and it fits the 4 hours. B is a good later improvement." },

    { id: "Q5", group: "Shape of the dbt project", title: "How do the mart models read the staging tables?",
      eli5: "The mart recipes start from the staging tables. dbt can build those tables first, in the right order, or assume they already exist.",
      example: "The core mapping reads STG_ORDERS (described again at L1044). In PowerCenter, the workflow link at L4624 makes staging run first.",
      options: [
        { k: "A", label: "ref('stg_orders')", what: "dbt builds staging first by itself, so the order, and the swaps, carry through as in PowerCenter." },
        { k: "B", label: "source('stg', 'stg_orders')", what: "Reads a table that must already exist; staging and marts are disconnected." }
      ],
      rec: "A", why: "ref() is how dbt replaces the workflow's run order, and it keeps the XML's chain raw → staging → marts." },

    { id: "Q6", group: "Shape of the dbt project", title: "How is the SQL inside a model laid out?",
      eli5: "Inside a model we can write one step per box, like the drawing, or squash everything into one big query.",
      example: "stg_orders on the example page has one step per box: sq_raw_orders, then exp_orders, then the final select with the flagged swap.",
      options: [
        { k: "A", label: "One CTE per box, with a comment giving its XML lines", what: "Longer, but every step points back to the drawing." },
        { k: "B", label: "One compact query", what: "Shorter, but hard to trace back to the XML." }
      ],
      rec: "A", why: "A step named after its box, with its line numbers, makes any line easy to explain." },

    { id: "Q7", group: "Shape of the dbt project", title: "What names do the columns get?",
      eli5: "Model names are settled (from the table). The columns still need names.",
      example: "The XML calls a column ORDERED_AT_DAY; jaffle-shop calls the same thing ordered_at.",
      options: [
        { k: "A", label: "The XML's names in lower case (ordered_at_day)", what: "Faithful. The comparison with jaffle-shop needs a small name map." },
        { k: "B", label: "jaffle-shop's names where they exist (ordered_at)", what: "Easier comparison, but the converter would have to know about jaffle-shop, which is hard-coding." }
      ],
      rec: "A", why: "The brief says not to hard-code the jaffle shop. The name map belongs in the check, not in the converter." },

    { id: "Q8", group: "Shape of the dbt project", title: "How are the model files arranged? (part of O4)",
      eli5: "Where the SQL files go inside the dbt project.",
      example: "16 models from 3 mappings.",
      options: [
        { k: "A", label: "One folder per mapping (models/m_fl_js_staging_full/…)", what: "Every file traces back to its mapping, with nothing to guess." },
        { k: "B", label: "By layer (models/staging, models/marts)", what: "Looks like a hand-written project, but the converter has to guess layers from names." },
        { k: "C", label: "All in one folder", what: "Simplest; gets crowded." }
      ],
      rec: "A", why: "Each folder matches one mapping in the XML, so no guessing." },

    { id: "Q9", group: "Shape of the dbt project", title: "How is each table built on every run? (closes O3)",
      eli5: "Each run can rebuild a table from scratch, or add new rows to what's already there.",
      example: "The session says Truncate target = NO (L919), but every target's Pre SQL empties it first: TRUNCATE TABLE STG.STG_ORDERS (L541). So PowerCenter rebuilds every table on every run.",
      options: [
        { k: "A", label: "table: rebuild every run", what: "Matches what PowerCenter does." },
        { k: "B", label: "view: store nothing, compute when read", what: "Always fresh, but unlike PowerCenter's stored tables." },
        { k: "C", label: "incremental: add rows", what: "What 'Truncate = NO' alone suggests, but the Pre SQL says otherwise." }
      ],
      rec: "A", why: "It matches what the XML really does once the Pre SQL is counted." },

    { id: "Q10", group: "Copying the XML exactly (how D1 applies)", title: "How do flags show up in the output?",
      eli5: "When we copy something that looks wrong, we leave a note. Where do the notes go?",
      example: "-- FLAG L608: SUBTOTAL (dollars) goes into SUBTOTAL_CENTS, as the connector says.",
      options: [
        { k: "A", label: "A comment in the SQL, at that line", what: "Seen by anyone reading the model." },
        { k: "B", label: "A, plus one flags report per run (flags.md)", what: "Also gives one list for the README." },
        { k: "C", label: "B, plus a dbt test per flag that warns", what: "Flags show up in dbt's output too; more files." }
      ],
      rec: "B", why: "The comment helps whoever reads one model; the report becomes the README's 'where output is likely wrong' section." },

    { id: "Q11", group: "Copying the XML exactly (how D1 applies)", title: "Do we copy the target column types too?",
      eli5: "Each target column has a size, like a box that only holds whole numbers. If we copy the sizes, some values get rounded, just as in the original database.",
      example: "Tax in dollars (0.42) lands in TAX_PAID_CENTS, a NUMBER(15,0) column (L73). The original database stores 0. Without the column type, DuckDB keeps 0.42.",
      options: [
        { k: "A", label: "Cast every output column to its target type", what: "Same values as the real table, rounding included." },
        { k: "B", label: "Keep whatever type the calculation gives", what: "Simpler, but differs from the real table in the two lossy spots." }
      ],
      rec: "A", why: "D1 copies what PowerCenter produces, and the target's column types are part of that. The two lossy spots get flags." },

    { id: "Q12", group: "Copying the XML exactly (how D1 applies)", title: "What happens to the Sorters?",
      eli5: "A Sorter lines rows up, like sorting cards. A stored table is a bag of cards: it forgets the order. Only a step that walks through the cards one by one cares about it.",
      example: "SRT_ORDERS (L513) sorts orders right before STG_ORDERS, and the table forgets that order. SRT_BY_CUSTOMER (L3554) sorts by customer, day and order before the counter, and the counter's numbers depend on it.",
      options: [
        { k: "A", label: "Drop every Sorter", what: "Breaks the counters: their numbers would come out in a random order." },
        { k: "B", label: "Keep each one as an ORDER BY", what: "Harmless but pointless in most places; the table forgets it anyway." },
        { k: "C", label: "Drop them as steps, but use their sort keys in any row-by-row step that follows", what: "Order is kept exactly where it changes the result." }
      ],
      rec: "C", why: "It keeps what the 3 Sorters that matter do, and drops the 12 that don't." },

    { id: "Q13", group: "Copying the XML exactly (how D1 applies)", title: "How do we translate the row-by-row ports?",
      eli5: "Some ports remember the previous row, like keeping a tally while reading a list. SQL can do this with window functions, but only for the patterns we teach it.",
      example: "v_ORDER_SEQUENCE (L3589) was meant to number each customer's orders, but because of the port order it counts 1, 2, 3… across all rows. v_IS_FIRST_CUSTOMER (L2127) is always 0.",
      options: [
        { k: "A", label: "Copy exactly for the patterns in this file; stop with an error on any other", what: "A running count over all rows, and a flag of 0, both flagged. Small and faithful." },
        { k: "B", label: "Build a general emulator of port-by-port evaluation", what: "Handles any XML, but far more work than 4 hours allows." },
        { k: "C", label: "Fix them to what the author meant", what: "Matches jaffle-shop, but goes against D1." }
      ],
      rec: "A", why: "D1 says copy and flag. Supporting the two patterns this file has, and refusing unknown ones, stays faithful and fits the time." },

    { id: "Q14", group: "Copying the XML exactly (how D1 applies)", title: "Which column types do the raw tables get when we load the seed data?",
      eli5: "The raw data is a set of CSV files. When we load them, each column needs a type. We can use what the XML says, or let DuckDB guess.",
      example: "The XML says PERISHABLE is text (L10), and the CSV holds True and False. As text, the rule at L504 finds 0 of 65 perishable supplies. With DuckDB's true/false guess, it finds 30.",
      options: [
        { k: "A", label: "Use the XML's PC Source types", what: "Our models see what PowerCenter would have seen." },
        { k: "B", label: "Let DuckDB guess", what: "Matches how jaffle-shop loads them, but the rule then behaves differently from PowerCenter." }
      ],
      rec: "A", why: "We are testing a copy of PowerCenter, so its input should look like PowerCenter's input. The difference from jaffle-shop gets a flag." },

    { id: "Q15", group: "Copying the XML exactly (how D1 applies)", title: "What date does recency count from?",
      eli5: "To know how long ago a customer last ordered, you need 'today'. The XML has a setting for it, with a default.",
      example: "$$RUN_DATE defaults to 12/31/2025 (L3104). The seed orders end on 31 Aug 2025, so every customer is at least 122 days old and gets the lowest recency score.",
      options: [
        { k: "A", label: "A dbt variable with the same default (2025-12-31)", what: "Same result as a default PowerCenter run; can be changed per run." },
        { k: "B", label: "Today's date", what: "Results change every day and never match the XML's default." },
        { k: "C", label: "A dbt variable with no default", what: "Every run must pass a date." }
      ],
      rec: "A", why: "It copies the XML, parameter and default included, and runs the same way every time." },

    { id: "Q16", group: "Copying the XML exactly (how D1 applies)", title: "What about functions with no exact twin in DuckDB?",
      eli5: "Most Informatica functions have a twin in SQL. A few behave slightly differently, like how a 2-digit year is turned back into a full year.",
      example: "ORDERED_AT_DAY = TO_DATE(TO_CHAR(ORDERED_AT, 'DD-MM-YY'), 'DD-MM-YY') (L110). For 2024–2025 dates this equals date_trunc('day', ordered_at).",
      options: [
        { k: "A", label: "Translate each call (to text and back), and flag the century rule", what: "Closest copy; the flag says where DuckDB and PowerCenter may guess the century differently." },
        { k: "B", label: "Use the shortcut date_trunc('day', …)", what: "Cleaner SQL, but it's our reading of the intent, not the XML." }
      ],
      rec: "A", why: "D1 again: copy what it does. The flag marks the one place the copy may differ." },

    { id: "Q17", group: "Edges", title: "What does the converter leave out?",
      eli5: "Some parts of the XML are about running things, not about what the tables contain.",
      example: "The TRUNCATE Pre SQL (L541), connections such as STG_Jaffleshop (L4587), the scheduler (L4055), the workflow links (L4622–4625), and the command task that creates report views (L4058–4062).",
      options: [
        { k: "A", label: "Leave them out, and list each one in the README and the flags report", what: "Truncation is covered by Q9 and run order by Q5. The report views aren't defined in any mapping." },
        { k: "B", label: "Generate stand-ins (for example an empty hook for the command)", what: "Shows they exist, but adds code that does nothing." }
      ],
      rec: "A", why: "None of them changes what the tables contain, except the views, which we can't rebuild from the mappings." },

    { id: "Q18", group: "Edges", title: "What happens when the converter meets something it doesn't know?",
      eli5: "Another XML might contain a box or a function we never taught the converter.",
      example: "This file has 8 box types and 13 functions. Another file might have a Lookup transformation or a DECODE function.",
      options: [
        { k: "A", label: "Stop with a clear error naming the element and its XML line", what: "Never writes SQL that looks right but isn't." },
        { k: "B", label: "Write a placeholder with a flag, and carry on", what: "You get partial output, but a placeholder is easy to miss." },
        { k: "C", label: "A by default, B with a switch", what: "Both, for a bit more code." },
        { k: "D", label: "Your option: convert everything else, and make the unknown model fail at dbt compile", what: "The failing model names the element and its XML line. It is listed in the report, and the converter exits with an error code. Nothing wrong can run, and nothing is easy to miss." }
      ],
      rec: "A", why: "Wrong SQL that runs is worse than no SQL, and the error says exactly what to add." },

    { id: "Q19", group: "Checking", title: "How does check 3 (compare with jaffle-shop) treat known differences?",
      eli5: "We compare our tables with jaffle-shop's. Some differences are expected, because we copy the XML's mistakes. The check has to tell those apart from new surprises.",
      example: "ORDERS: ours will have 61,465 rows, jaffle-shop 61,948 (the 483 orders with no items). stg_orders.subtotal_cents: ours 7, jaffle-shop 700 (the swap). And names like ordered_at_day versus ordered_at.",
      options: [
        { k: "A", label: "Strict: every row and column must match", what: "Fails on every flag, so it tells us nothing new." },
        { k: "B", label: "Compare against a list of expected differences, and report matched / explained / unexplained", what: "The list holds the flags, a column-name map and known row gaps. Only real surprises fail." },
        { k: "C", label: "Row counts only", what: "Fast, but misses wrong values." }
      ],
      rec: "B", why: "It turns each flag into a checked claim. The enriched marts have no twin, so they rely on our unit tests." }
  ]
};

/* What the user decided, 21 Nov 2026 (prompt 8). "k" is the chosen option. */
window.DECISIONS.made = {
  date: "21 Nov 2026",
  picks: {
    Q1: { k: "C" }, Q2: { k: "A" }, Q3: { k: "A" }, Q4: { k: "A" }, Q5: { k: "A" },
    Q6: { k: "A" }, Q7: { k: "A" }, Q8: { k: "A" }, Q9: { k: "A" }, Q10: { k: "B" },
    Q11: { k: "A", note: "Flag where the cast rounds. Rounding happens only at the targets, not inside the mapping, because high precision is off." },
    Q12: { k: "C", note: "Follow each Sorter's case and NULL settings where order matters, and flag them." },
    Q13: { k: "A", note: "Follow the Sorters' case and NULL settings, and flag them." },
    Q14: { k: "A" },
    Q15: { k: "A", note: "Also flag that the enriched session names a parameter file (L4554) that could override the run date." },
    Q16: { k: "A" },
    Q17: { k: "A", note: "The workflow not stopping on failure goes in the README as out of scope." },
    Q18: { k: "D", note: "Someone trying another XML still gets everything that could be converted." },
    Q19: { k: "B" }
  }
};
