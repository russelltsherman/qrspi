# Ticket: ORD-892

## Title
Add WebSocket support for real-time order status updates

## Description
Customers frequently refresh the order tracking page to check for status
changes. The support team reports this as a top complaint. We need real-time
updates so the UI reflects order status changes as they happen.

## Acceptance Criteria
- [ ] Order status changes push to connected clients within 2 seconds
- [ ] Client receives updates only for their own orders
- [ ] Connection survives brief network interruptions (reconnect within 5s)
- [ ] Graceful degradation when WebSocket is unavailable (fall back to polling)
- [ ] No more than 10% increase in server memory per 1000 concurrent connections

## Constraints
- Must work behind existing load balancer (sticky sessions or alternative)
- Must not break existing REST polling endpoint (backward compat)

## Out of Scope
- Push notifications (mobile/email) for order updates
- Real-time updates for non-order entities
