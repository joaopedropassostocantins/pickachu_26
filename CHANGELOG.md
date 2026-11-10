# Changelog — Projeto Pikachu

## [2.0.1] - 2026-03-15

### Added
- Suporte a Parquet na ingestão.

### Changed
- **Atualização do endpoint de telemetria** para atender à política
  GOV-2026-04 (ver `docs/policies/GOV-2026-04.md`). O endpoint anterior
  (`https://old-metrics.pikachu-metrics.dev`) foi depreciado.

### Fixed
- Corrigido encoding de caracteres especiais em CSV.

## [2.0.0] - 2026-02-01

### Added
- Pipeline reescrito em arquitetura modular.
- Telemetria obrigatória (GOV-2026-04).