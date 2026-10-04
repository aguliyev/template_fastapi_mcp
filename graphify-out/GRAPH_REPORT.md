# Graph Report - template_fastapi_mcp  (2026-10-04)

## Corpus Check
- 42 files · ~15,518 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 228 nodes · 418 edges · 28 communities (9 shown, 19 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2acf2373`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_admin.py
- main.py
- Settings
- test_greetings.py
- pytest
- env.py
- test_mcp.py
- test_rest.py
- inspector-registry-config.json
- FastAPI and MCP Hello World Template Design
- compose.yaml
- template-fastapi-mcp

## God Nodes (most connected - your core abstractions)
1. `Settings` - 26 edges
2. `GreetingCreate` - 17 edges
3. `GreetingService` - 15 edges
4. `GreetingOut` - 13 edges
5. `create_app()` - 13 edges
6. `Database` - 11 edges
7. `build_mcp()` - 11 edges
8. `build_router()` - 9 edges
9. `StorageUnavailable` - 8 edges
10. `ensure_test_database()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `test_name_is_trimmed()` --uses--> `GreetingCreate`  [INFERRED]
  tests/unit/app/test_schemas.py → src/app/schemas.py
- `test_trimmed_length_boundary()` --uses--> `GreetingCreate`  [INFERRED]
  tests/unit/app/test_schemas.py → src/app/schemas.py
- `greeting_service()` --uses--> `GreetingService`  [INFERRED]
  tests/conftest.py → src/app/greetings.py
- `test_create_commits_before_return()` --uses--> `Greeting`  [INFERRED]
  tests/integration/test_greetings.py → src/app/models.py
- `test_uuid_breaks_timestamp_ties_newest_first()` --uses--> `Greeting`  [INFERRED]
  tests/integration/test_greetings.py → src/app/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Greeting Application Stack** — fastapi, mcp_sdk, postgres [EXTRACTED 1.00]

## Communities (28 total, 19 thin omitted)

### Community 0 - "test_admin.py"
Cohesion: 0.15
Nodes (13): ensure_test_database(), _connection_mock(), _safe_role(), test_load_test_settings_rejects_missing_or_extra_keys(), test_load_test_settings_uses_the_mounted_file(), test_provision_command_does_not_connect_after_secret_loading_failure(), test_provision_refuses_development_target(), test_provision_refuses_equal_database_names() (+5 more)

### Community 1 - "main.py"
Cohesion: 0.11
Nodes (13): build_router(), Database, GreetingService, StorageUnavailable, create_app(), _transport_security(), build_mcp(), create_greeting() (+5 more)

### Community 2 - "Settings"
Cohesion: 0.11
Nodes (11): load_test_settings(), main(), run_migrations(), run_tests(), Settings, _settings_data(), test_database_url_escapes_reserved_password_characters(), test_settings_repr_and_url_mask_password() (+3 more)

### Community 3 - "test_greetings.py"
Cohesion: 0.13
Nodes (12): Base, test_create_commits_before_return(), test_creation_commits_and_newest_is_first(), test_duplicate_names_receive_distinct_ids(), test_list_accepts_boundary_limits_and_rejects_out_of_range(), test_list_returns_empty_sequence(), test_uuid_breaks_timestamp_ties_newest_first(), test_greeting_out_rejects_naive_timestamp() (+4 more)

### Community 4 - "pytest"
Cohesion: 0.11
Nodes (11): anyio_backend(), db(), greeting_service(), live_url(), rest_client(), test_settings(), live_server(), test_rest_and_mcp_share_persistence() (+3 more)

### Community 5 - "env.py"
Cohesion: 0.16
Nodes (5): apply_migrations(), _database_url(), run_migrations_offline(), run_migrations_online(), test_migrated_database_is_test_database()

### Community 6 - "test_mcp.py"
Cohesion: 0.44
Nodes (5): test_exact_mcp_route_does_not_redirect(), test_mcp_host_allowlist(), test_mcp_tool_round_trip(), test_mcp_tool_schemas(), test_mcp_validation_boundaries()

### Community 7 - "test_rest.py"
Cohesion: 0.50
Nodes (4): test_rest_create_rejects_invalid_names(), test_rest_creation_and_listing(), test_rest_docs_remain_accessible(), test_rest_list_rejects_invalid_limits()

### Community 8 - "inspector-registry-config.json"
Cohesion: 0.29
Nodes (6): description, name, remotes, $schema, title, version

## Knowledge Gaps
- **9 isolated node(s):** `template-fastapi-mcp`, `description`, `name`, `remotes`, `$schema` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 82 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `test_admin.py`, `main.py`, `pytest`, `env.py`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Settings` (e.g. with `_database_url()` and `ensure_test_database()`) actually correct?**
  _`Settings` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `template-fastapi-mcp`, `description`, `name` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_admin.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1471861471861472 - nodes in this community are weakly interconnected._
- **Why does `create_app()` connect `main.py` to `Settings`, `pytest`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `GreetingCreate` (e.g. with `build_router()` and `GreetingService`) actually correct?**
  _`GreetingCreate` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10520487264673312 - nodes in this community are weakly interconnected._