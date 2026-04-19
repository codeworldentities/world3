# World3 B2B Readiness Plan (1M-10M stage)

## Objective
Build a stable pilot-ready platform that can convert into recurring B2B revenue.

## North-Star KPIs
- Availability evidence: uninterrupted runtime windows >= 14 days
- Tick latency: p95 <= 60ms on target workload
- Code quality: avg >= 0.65
- Review coverage: reviews/commits >= 0.60
- Bug pressure: live bugs / alive entities <= 0.20
- Pilot retention proxy: weekly active pilot accounts >= 70% of onboarded pilots

## What Is Already Added
- /api/b2b/readiness endpoint for score, blockers, strengths, KPIs, milestones
- Tick performance telemetry in core world loop (EMA + p95 sample window)
- Server uptime reporting
- Settings panel card for B2B readiness monitoring

## Execution Phases

### Phase 1: Pilot-Ready Core (now)
- Stabilize lifecycle dynamics and performance under load
- Add alerting on score drop and KPI threshold breaches
- Freeze baseline configs for reproducible pilot behavior

### Phase 2: Customer Packaging
- Tenant-aware auth (workspace/user isolation)
- API keys per tenant and role-based access
- Billing + usage metering
- Pricing plans and hard quotas

### Phase 3: Reliability + Compliance
- Error budgets and SLOs
- Backup + restore drills
- Audit event coverage for sensitive actions
- Security hardening (secret management, key rotation, dependency scanning)

### Phase 4: Revenue Engine
- Pilot funnel: onboarding -> activation -> weekly usage
- Expansion playbook: usage-based upsell and enterprise plan
- Case studies from first pilot outcomes

## Weekly Ops Loop
1. Review /api/b2b/readiness score and blockers daily
2. Fix highest-impact blocker first (latency, bug pressure, review coverage)
3. Run stress simulation and compare KPI deltas vs previous week
4. Publish one pilot report with uptime, quality, and outcomes

## Target Outcome
- Pilot-ready score >= 60 for 2 consecutive weeks
- B2B-ready score >= 80 for 4 consecutive weeks
- First recurring pilot contracts signed
