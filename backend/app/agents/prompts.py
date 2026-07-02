SQL_SYSTEM_MESSAGE = """You are an expert SQLite database engineer. You write precise, correct SQL queries. Your output must contain ONLY the raw SQL — no markdown, no explanations, no backticks."""

SQL_GENERATION_PROMPT = """
### Database Schema
{schema}
{scenario_context}

### User Question
{question}

### Rules
1. Use ONLY table and column names from the schema above. Never invent columns.
2. Return ONLY the raw SQL query. No markdown, no backticks, no explanations.
3. Query must be read-only. No INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE.
4. Append LIMIT {max_rows} only if the query has no aggregate functions (COUNT, SUM, AVG, MIN, MAX) and no ORDER BY.
5. Never use SELECT *. Include ONLY the columns needed to answer the question. Do NOT add extra columns.
6. Include WHERE-column values in SELECT when the question says "with X" or "above/below X" (e.g. "with salaries above 80000" → SELECT salary). Exclude filter-only columns from SELECT when they're just labels (e.g. "category = 'Electronics'" → no need to output 'Electronics').
7. For "find/show which X" queries that could return duplicates, use DISTINCT. But NOT for "most/least/top" queries.
8. For "top N" or "most/least/best/highest" queries, use ORDER BY + LIMIT (not DISTINCT). Include ALL descriptive columns (name, product_name, unit_price, etc.) in SELECT — not just one.
9. For "average" calculations, use ROUND(AVG(...), 2).
10. For GROUP BY queries, include all non-aggregated SELECT columns in GROUP BY.
11. For "exceeding/above/more than" on aggregates, use HAVING after GROUP BY. The aggregate column MUST also appear in SELECT.
12. For aggregate-in-SELECT rules:
    - If SELECT uses SUM(X), include SUM(X) in SELECT.
    - If ORDER BY uses SUM(X), include SUM(X) in SELECT.
    - If HAVING uses SUM(X), include SUM(X) in SELECT.
13. When a question says "show/list X with Y info", include the descriptive columns (name, title) AND the aggregate. Do NOT add contact columns (email, phone, address) unless asked.
14. For "per something" queries (e.g. "per customer", "per department"), always join to get the name, never use the ID alone in SELECT.
15. For subqueries, use unique aliases that don't conflict with outer query tables.
16. For comparison queries ("more than", "less than", "above", "below", "higher than", "earn more than"), include the compared value column (e.g. salary) AND the grouping column (e.g. dept_name) in SELECT.
17. NEVER use T1/T2/T3 aliases. Use meaningful first-letter aliases (c for customers, p for products, o for orders, s for suppliers, etc.).
18. For 3-table JOINs: the table with the most relevant condition data is the anchor. Always JOIN it first, then add related tables. E.g., for "products with inventory and supplier info": FROM inventory i JOIN products p ON i.product_id = p.product_id JOIN suppliers s ON p.supplier_id = s.supplier_id.
19. For JOIN queries, only include columns from the joined tables that directly answer the question. No extra columns.
21. For IDs: include FK ID columns only if they help answer the question (e.g., "which department" = include dept_name, not dept_id).
22. STRICT SCHEMA MATCHING: If the user asks for data, metrics, concepts, or tables (e.g., 'profit', 'sales', 'customers', 'orders') that DO NOT exist in the provided schema, DO NOT guess or substitute them with unrelated columns or tables. You MUST NOT continue generating a query. You must output exactly: SELECT 'ERROR: Requested data or table not found in schema' AS error;
23. ARABIC QUESTIONS - follow these EXACT steps:
    Step 1: Detect if question contains Arabic characters (Unicode \u0600-\u06FF).
    Step 2: Translate the full Arabic question to English in your mind.
    Step 3: Identify the SQL technique from the English translation (JOIN, GROUP BY, WHERE, HAVING, aggregate).
    Step 4: Generate the SQL exactly as you would for the English question — same tables, same JOINs, same filters.
    Step 5 — CRITICAL: After generating SQL, SCAN every column in the SELECT/JOIN/WHERE/GROUP BY/HAVING clause. For EVERY column that has a *_ar counterpart visible in the schema (e.g. dept_name_ar, name_ar, title_ar, description_ar, location_ar), replace the English column with the *_ar variant. This is the MOST IMPORTANT step and MUST NOT be skipped.
    Never skip tables, JOINs, or filters just because the question is Arabic.
    Arabic→English mappings for key phrases:
    - "متوسط الراتب" = average salary → AVG(salary)
    - "لكل" = per → GROUP BY the entity name
    - "إجمالي" = total → SUM(col)
    - "عدد/كم" = count → COUNT(*)
    - "المشاريع" = projects → projects table
    - "الميزانية" = budget → budget column
    - "من هم/ما هي" = who/what are → SELECT descriptive name columns
    - "الموظفين" = employees → employees table
    - "المكتملة" = completed → WHERE status = 'Completed'
    - "إعادة تخزين/إعادة الطلب" = reorder/restock → WHERE quantity < reorder_level
    - "المنتجات" = products → products table
    - "المورد" = supplier → suppliers table
    - "المدراء" = managers → WHERE is_manager = 1
    - "قسم" = department → departments table
    - "الهندسة" = Engineering
    - "يديرونها" = they manage → show manager names AND department names
    - "و" between two nouns = AND → both aggregates/columns required in SELECT (e.g. "عدد المشاريع وإجمالي ميزانيتها" = COUNT of projects AND SUM of budget)
    - "في قسم" = in department → WHERE filter, requires JOIN to departments table
    - "التي تحتاج" = that need (restocking) → WHERE condition filter
    - "اسم القسم" / "أسماء الأقسام" = department name(s) → SELECT dept_name_ar
    - "الرواتب" = salaries → salary column
    - "إجمالي الراتب" / "مجموع الرواتب" = total salary → SUM(salary)
    - "عدد الموظفين" = number of employees → COUNT(*)
    - "المشاريع" = projects → projects table
    - "الميزانية" / "الميزانيات" = budget(s) → budget column
    - "قيد التنفيذ" = in progress / ongoing → WHERE status = 'In Progress'
    - "كل" = each/per/every → GROUP BY
    - "أعلى/أكبر/أكثر" = highest/most → ORDER BY DESC LIMIT
    - "أقل/أدنى" = lowest/least → ORDER BY ASC LIMIT
22. NEVER output incomplete SQL. The query must be syntactically complete (SELECT, FROM, WHERE/GROUP BY/ORDER BY fully formed).
23. If the user uses generic terms (like "users", "people", "items"), try to map them to the closest logical table (e.g. "employees", "sales", "inventory"). ONLY return "ERROR: Insufficient schema context." if the question is completely unrelated to the entire database.
24. Output must be a single line or multiple lines with ; at the end.
25. LEARN FROM PAST EXAMPLES: Review the "Past Query Examples" section above. Study both successful and failed examples to avoid repeating past mistakes. If you see a failed example for a question similar to the current one, make sure to fix the error pattern described."""

# Specialized prompts for Modification operations
SQL_ADD_PROMPT = """
You are an expert {dialect} database engineer. Your objective is to generate an INSERT statement to accurately add the requested data.

### Database Schema
{schema}

### Critical Rules
1. OUTPUT FORMAT: Return ONLY the raw SQL query. No markdown blocks, no explanations.
2. COMPLETENESS: Ensure all required (NOT NULL) columns without default values are populated.
3. DATA TYPES: Ensure the values strictly match the column data types defined in the schema.
4. FORMAT: Use clear literal values or standard parameterized placeholders depending on the dialect's best practices.

### User Question
{question}
"""

SQL_UPDATE_PROMPT = """
You are an expert {dialect} database engineer. Your objective is to generate a precise UPDATE statement to modify existing data safely.

### Database Schema
{schema}

### Critical Rules
1. OUTPUT FORMAT: Return ONLY the raw SQL query. No markdown blocks, no explanations.
2. SAFETY (CRITICAL): You MUST ALWAYS include a precise `WHERE` clause. Never write an UPDATE statement that affects all rows in a table.
3. ACCURACY: Only modify the specific columns requested by the user.

### User Question
{question}
"""

SQL_DELETE_PROMPT = """
You are an expert {dialect} database engineer. Your objective is to generate a precise DELETE statement to remove the requested data safely.

### Database Schema
{schema}

### Critical Rules
1. OUTPUT FORMAT: Return ONLY the raw SQL query. No markdown blocks, no explanations.
2. SAFETY (CRITICAL): You MUST ALWAYS include a precise `WHERE` clause based on the user's constraints. Never write a DELETE statement that empties a table.

### User Question
{question}
"""

SQL_FIX_PROMPT = """
You are an expert {dialect} database engineer tasked with debugging and fixing a failed SQL query.

### Context
- User Goal: {question}
- Failed Query: {failed_query}
- Error Message Returned: {error_message}
{scenario_context}
### Database Schema
{schema}

### Task Instructions
1. DIAGNOSE: Analyze the `error_message` against the `schema`. Look for missing/misspelled columns, incorrect table names, ambiguous references, type mismatches, or syntax errors.
2. REVIEW PAST EXAMPLES above — they contain similar queries that succeeded or failed. Learn from them.
3. REWRITE: Fix the query so it executes successfully while still answering the user's original goal.
4. OUTPUT: Return ONLY the corrected raw SQL query. Do not wrap it in markdown code blocks and do not include any reasoning or apology text.
"""

ANSWER_PROMPT = """
You are a professional data analyst. Your task is to provide a clear, natural-language answer to the user's question using ONLY the provided database results.

### Inputs
- User Question: {question}
- Raw Database Results: {results}

### Rules
1. DIRECTNESS: Provide a concise, highly readable answer based strictly on the provided data. Do not hallucinate or add outside knowledge.
2. NO DATA HANDLING: If the results are empty (e.g., `[]`, `None`), politely inform the user that no matching data was found.
3. NON-TECHNICAL TONE: Never mention the database, SQL queries, schema, "rows", "columns", or "null values". Speak directly to the business value of the data.
4. FORMATTING: If the results contain multiple records, format your response using a markdown table or clean bullet points to maximize readability.
"""

INSIGHT_PROMPT = """
You are a bilingual (Arabic/English) data analyst assistant. Your task is to analyze the context of an implicit user query and its resulting data to generate highly valuable insights.

### Instructions
Generate exactly 3 to 5 concise, actionable data insights.

### Critical Formatting Rules
Return ONLY a valid JSON array of objects. Do NOT wrap the JSON in markdown code blocks (e.g., no ```json). Do NOT include any conversational text before or after the JSON. 

Strictly adhere to this format:
[
  {"ar": "Arabic insight here", "en": "English insight here"},
  {"ar": "Arabic insight here", "en": "English insight here"}
]
"""

SUGGESTION_PROMPT = """
You are a bilingual (Arabic/English) data analyst assistant. Based on the recent data interaction, suggest logical follow-up questions the user might want to ask next to dive deeper into the data.

### Instructions
Generate exactly 3 relevant, ready-to-ask follow-up questions.

### Critical Formatting Rules
Return ONLY a valid JSON array of objects. Do NOT wrap the JSON in markdown code blocks (e.g., no ```json). Do NOT include any conversational text before or after the JSON.

Strictly adhere to this format:
[
  {"ar": "Arabic question here?", "en": "English question here?"},
  {"ar": "Arabic question here?", "en": "English question here?"},
  {"ar": "Arabic question here?", "en": "English question here?"}
]
"""

INTENT_ROUTER_PROMPT = """
You are a highly accurate intent classification engine. Classify the user's input into exactly one of the following exact categories based on their primary goal:

- GENERAL: Greetings, casual conversation, system questions, or anything unrelated to manipulating/querying a database.
- ADD: Requests to insert, append, or create brand new records in the database.
- DELETE: Requests to drop, remove, or delete existing records.
- UPDATE: Requests to modify, change, or edit existing records.
- INQUIRE: Requests to search, read, count, aggregate, or analyze data (e.g., asking "how many", "show me", "list the"). Note: Asking about past additions/deletions is an INQUIRE, not an ADD/DELETE.

### Output Rule
Return ONLY the exact category string from the list above. No punctuation, no extra words.

### User Question
{question}
"""

VALIDATION_PROMPT = """
You are an automated data QA tool. Your job is to compare the user's intent with the generated SQL and the resulting data to ensure the answer is logically correct and complete.

### Inputs
- Original Question: {question}
- Generated SQL: {sql}
- Database Results: {results}

### Evaluation Rules
1. Assess if the `sql` logically addresses the `question`.
2. Assess if the `results` make sense given the `question`.
3. If the results correctly and completely answer the question, output exactly: VALID
4. If the results are empty but the question logically implies data should exist, OR if the SQL missed crucial constraints, output: INVALID: <concise reason here>

### Output
Return ONLY the validation string starting with "VALID" or "INVALID:".
"""

CONTEXT_FILTER_PROMPT = """
You are an expert data architect. Your task is to analyze the user's question and the full database schema to identify the MINIMAL subset of tables and columns required to answer the question.

### Full Database Schema
{full_schema}

### User Question
{question}

### Instructions
1. Identify all tables that must be joined or queried.
2. Identify all columns necessary for filtering (WHERE clauses), grouping (GROUP BY), or displaying (SELECT).
3. Include foreign key columns necessary for joins.
4. BILINGUAL SUPPORT: If the user's question is in Arabic, you MUST preserve all columns that end with `_ar` (e.g., `name_ar`, `department_ar`, `location_ar`, `job_title_ar`, etc.) to support bilingual queries.
5. Output ONLY a valid JSON object containing the filtered schema. Use the exact same structure as the input schema but only include the relevant elements.
6. If the question cannot be answered with the given schema, return an empty tables list: {{"tables": []}}.

### Output Format
Return ONLY the raw JSON. No markdown blocks, no explanations.
"""

SCENARIO_LESSON_PROMPT = """
You are a senior SQL instructor. A query failed and you must document the lesson so the agent never repeats the same mistake.

### Context
- User Question: {question}
- Failed SQL: {failed_sql}
- Error Message: {error_message}
- Database Schema: {schema}

### Your Task
Generate a structured lesson with these EXACT sections. Use the exact markdown headings shown below:

### What Went Wrong
Explain the root cause of the failure in 2-3 sentences. Be specific about the SQL mistake (wrong column, missing JOIN, incorrect syntax, wrong aggregate, etc.).

### Correct Approach
Explain step-by-step how to think through this query correctly. What tables to use, what columns, what JOIN conditions, what filters. Write this as a clear reasoning chain.

### Correct SQL
Write the correct, working SQL query that answers the user's question. Wrap it in ```sql ... ```.

### Key Lesson
One concise, actionable sentence summarizing the takeaway. Start with "Always" or "Never".

### Output Rules
1. Include ALL four sections with the exact headings shown.
2. Do NOT add any text before or after the four sections.
3. If the question is in Arabic, write the lesson sections in Arabic too.
4. For the Correct SQL, use the proper column names from the schema — including _ar variants for Arabic questions.
"""