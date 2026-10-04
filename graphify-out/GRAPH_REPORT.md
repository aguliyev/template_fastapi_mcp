# Graph Report - template_fastapi_mcp  (2026-10-04)

## Corpus Check
- Corpus is ~15,481 words - fits in a single context window. You may not need a graph.

## Summary
- 229 nodes · 420 edges · 27 communities (10 shown, 17 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.93)
- Token cost: 26,596 input · 1,953 output

## Community Hubs (Navigation)
- Admin CLI and Test Setup
- Greeting Service and Router
- Settings and Database Config
- Greeting Models and Validation
- Test Fixtures and Harness
- Alembic Migration Pipeline
- MCP Protocol Tests
- REST Endpoint Tests
- Inspector Registry Config
- Template Design Docs
- Postgres Compose Service
- Project Template Metadata

## God Nodes (most connected - your core abstractions)
1. `Settings` - 26 edges
2. `GreetingCreate` - 17 edges
3. `GreetingService` - 15 edges
4. `create_app()` - 13 edges
5. `GreetingOut` - 13 edges
6. `Database` - 11 edges
7. `build_mcp()` - 11 edges
8. `build_router()` - 9 edges
9. `ensure_test_database()` - 8 edges
10. `StorageUnavailable` - 8 edges

## Surprising Connections (you probably didn't know these)
- `test_name_is_trimmed()` --uses--> `GreetingCreate`  [INFERRED]
  tests/unit/app/test_schemas.py → src/app/schemas.py
- `test_trimmed_length_boundary()` --uses--> `GreetingCreate`  [INFERRED]
  tests/unit/app/test_schemas.py → src/app/schemas.py
- `_database_url()` --uses--> `Settings`  [INFERRED]
  migrations/env.py → src/app/config.py
- `test_settings()` --uses--> `Settings`  [INFERRED]
  tests/conftest.py → src/app/config.py
- `live_server()` --uses--> `Settings`  [INFERRED]
  tests/helpers.py → src/app/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Greeting Application Stack** — fastapi, mcp_sdk, postgres [EXTRACTED 1.00]

## Communities (27 total, 17 thin omitted)

### Community 0 - "Admin CLI and Test Setup"
Cohesion: 0.08
Nodes (17): ensure_test_database(), load_test_settings(), main(), run_migrations(), run_tests(), _connection_mock(), _safe_role(), test_load_test_settings_rejects_missing_or_extra_keys() (+9 more)

### Community 1 - "Greeting Service and Router"
Cohesion: 0.14
Nodes (12): build_router(), GreetingService, StorageUnavailable, create_app(), _transport_security(), build_mcp(), create_greeting(), list_greetings() (+4 more)

### Community 2 - "Settings and Database Config"
Cohesion: 0.11
Nodes (8): Settings, Database, _settings_data(), test_database_url_escapes_reserved_password_characters(), test_settings_repr_and_url_mask_password(), test_settings_require_both_credentials(), test_test_target_rejects_development_database(), test_test_target_rejects_equal_database_names()

### Community 3 - "Greeting Models and Validation"
Cohesion: 0.13
Nodes (12): Base, test_create_commits_before_return(), test_creation_commits_and_newest_is_first(), test_duplicate_names_receive_distinct_ids(), test_list_accepts_boundary_limits_and_rejects_out_of_range(), test_list_returns_empty_sequence(), test_uuid_breaks_timestamp_ties_newest_first(), test_greeting_out_rejects_naive_timestamp() (+4 more)

### Community 4 - "Test Fixtures and Harness"
Cohesion: 0.15
Nodes (11): anyio_backend(), db(), greeting_service(), live_url(), rest_client(), test_settings(), live_server(), test_rest_and_mcp_share_persistence() (+3 more)

### Community 5 - "Alembic Migration Pipeline"
Cohesion: 0.16
Nodes (5): apply_migrations(), _database_url(), run_migrations_offline(), run_migrations_online(), test_migrated_database_is_test_database()

### Community 6 - "MCP Protocol Tests"
Cohesion: 0.44
Nodes (5): test_exact_mcp_route_does_not_redirect(), test_mcp_host_allowlist(), test_mcp_tool_round_trip(), test_mcp_tool_schemas(), test_mcp_validation_boundaries()

### Community 7 - "REST Endpoint Tests"
Cohesion: 0.50
Nodes (4): test_rest_create_rejects_invalid_names(), test_rest_creation_and_listing(), test_rest_docs_remain_accessible(), test_rest_list_rejects_invalid_limits()

### Community 8 - "Inspector Registry Config"
Cohesion: 0.29
Nodes (6): description, name, remotes, $schema, title, version

### Community 10 - "Template Design Docs"
Cohesion: 0.40
Nodes (4): FastAPI and MCP Template Implementation Plan, FastAPI and MCP Hello World Template Design, template_fastapi_mcp.admin, template_fastapi_mcp.main:create_app

## Knowledge Gaps
- **10 isolated node(s):** `$schema`, `name`, `title`, `description`, `version` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 82 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings and Database Config` to `Admin CLI and Test Setup`, `Greeting Service and Router`, `Test Fixtures and Harness`, `Alembic Migration Pipeline`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Settings` (e.g. with `_database_url()` and `ensure_test_database()`) actually correct?**
  _`Settings` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `name`, `title` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Admin CLI and Test Setup` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Why does `create_app()` connect `Greeting Service and Router` to `Settings and Database Config`, `Test Fixtures and Harness`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `GreetingCreate` (e.g. with `build_router()` and `GreetingService`) actually correct?**
  _`GreetingCreate` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `Greeting Service and Router` be split into smaller, more focused modules?**
  _Cohesion score 0.1361344537815126 - nodes in this community are weakly interconnected._