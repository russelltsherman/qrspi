# Ticket: RPT-2100

## Title
Build advanced report builder with custom filters and export

## Description
Users need a flexible reporting tool that lets them build custom queries
against their data, apply filters, sort results, and export in multiple
formats. This replaces the current static reports page.

## Acceptance Criteria
- [ ] Users can select which columns to include in the report
- [ ] Users can add filter conditions (equals, contains, greater than, less than, between)
- [ ] Users can combine filters with AND/OR logic
- [ ] Users can sort by any selected column, ascending or descending
- [ ] Users can group results by one or more columns
- [ ] Aggregation functions available: count, sum, average, min, max
- [ ] Report preview shows first 100 rows before full generation
- [ ] Export to CSV with proper escaping of special characters
- [ ] Export to XLSX with column type preservation
- [ ] Export to PDF with pagination and headers
- [ ] Saved report templates can be stored and re-run
- [ ] Saved templates are shareable within the same team
- [ ] Report generation for > 10k rows runs as background job with progress
- [ ] Background jobs notify user via in-app notification on completion
- [ ] Rate limiting: max 5 concurrent report generations per user
- [ ] All exports include generation timestamp and filter summary

## Constraints
- Must use existing query builder library (knex), not raw SQL
- Export files must not exceed 50MB
- Background jobs must use existing job queue (Bull)

## Out of Scope
- Scheduled/recurring reports
- Chart or visualization generation
- Cross-team report sharing
