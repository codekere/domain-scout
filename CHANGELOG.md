# Changelog

All notable changes to DomainScout will be documented in this file.

## [v3.2.5] - 2026-08-02
### Added
- Integrated absolute error-catching across the main loop, background spinner, and file diagnostics.
- Polished all interactive prompt menus, ensuring zero unexpected closures or auto-exit bugs.

## [v3.2.4] - 2026-08-02
### Changed
- Reverted minified scripts back to standard, readable Python architecture to prevent background compilation errors.
- Refined DOM parsing logic for instantdomainsearch.com status indicators.

## [v3.2.3] - 2026-08-02
### Fixed
- Extended try-except blocks across all web scraping modules to catch timeout and network exceptions gracefully.
- Corrected remaining bottom border color leaks in the system diagnostics table.

## [v3.2.2] - 2026-08-02
### Added
- Full-color status badges so that extension and status text combined (e.g., .com:[-]) are uniformly colored.
### Changed
- Streamlined core logic to improve overall execution speed.

## [v3.2.1] - 2026-08-02
### Added
- Cyan coloring for domain extensions (.com, .net, etc.) in live scanning logs.
### Fixed
- Resolved ANSI color reset bugs that caused table borders in diagnostic menus to break and turn white.
- Fixed an unhandled reference bug in the help menu path.

## [v3.2.0] - 2026-08-02
### Added
- Centralized "Log Management & Diagnostics" menu replacing silent background file deletions.
- Real-time status indicators ([✓] OK, [!] Missing, [X] Corrupt) for core files (config.json, master log, error log).
- Empowered users with explicit options to repair, clean, or delete log files safely.

## [v3.1.1] - 2026-08-02
### Added
- Dedicated domain_scout_error.log file to record critical system and browser exceptions.
- Automatic verification for master log files to detect and discard corrupted rows.

## [v3.1.0] - 2026-08-02
### Added
- Upgraded settings menus to fully interactive multi-select checkboxes using questionary.
- Windows terminal UTF-8 encoding support (chcp 65001) to prevent box-drawing character glitches.
### Fixed
- Fixed default value errors to prevent unexpected application crashes.

## [v3.0.0] - 2026-08-02
### Added
- Real-time keyboard shortcuts (SPACE to pause/resume, M to modify settings on the fly, H for help).
- Master logging via domain_scout_master.log to centrally store scanned domains and categories.
- Log rechecker feature to re-verify existing logs using the primary scan engine.

## [v2.0.0] - 2026-08-02
### Added
- Dynamic User-Agent rotation pool to simulate real user browsers.
- Local config.json support to save user preferences.
- Headless browsing mode (--headless=new) and randomized search delays to avoid IP rate-limiting.

## [v1.0.0] - 2026-08-02
### Added
- Initial domain hunting framework built using Selenium WebDriver and BeautifulSoup.
- Automated keyword permutation generation (sequential and random options).
- Basic terminal output showing domain availability status (AVAILABLE, TAKEN).