# Research — Codebase Map

**Questions source:** questions_websocket.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> Scenario: ORD-892 — Add WebSocket support for real-time order status
> updates. Findings are factual observations of the (fictional reference)
> codebase the eval harness models; every answer is backed by a `file:line`
> citation. The codebase has no real-time transport today — it is poll-only.

## Q1: How does an order status change currently propagate from the point of mutation to the client, and where in the code is the status field written?

**Answer:** Status is written by `OrderService.setStatus`, which updates the `orders.status` column and emits a domain event on an in-process `EventEmitter`; nothing in the read/serve path consumes that event, so clients only see the change on their next poll.
**Evidence:**

```
this.events.emit('order.status_changed', { id, status })
```

— `src/services/order_service.js:84`
**Dependencies:** `src/db/knex.js`, `src/events/bus.js`
**Implicit contracts:** the emitted event is consumed only by audit logging today; no transport layer subscribes to it.

## Q2: How does the order tracking page learn about status changes today (poll interval, endpoint, payload shape)?

**Answer:** The client polls `GET /api/orders/:id/status` every 10 seconds via `setInterval`; the payload is the bare order object `{ id, status, updatedAt }`.
**Evidence:**

```
setInterval(() => fetchStatus(orderId), 10000)
```

— `web/src/pages/order_tracking.js:41`
**Dependencies:** `web/src/api/orders.js`
**Implicit contracts:** the poll interval is hard-coded; there is no push channel, so latency to the user is bounded below by the 10s interval.

## Q3: What real-time transport, if any, already exists in the server (WebSocket, SSE, long-poll), and how is it mounted on the HTTP server?

**Answer:** NOT FOUND. Searched `src/`, `package.json`, and the server bootstrap for `ws`, `socket.io`, `WebSocket`, `EventSource`, and `text/event-stream`; no WebSocket, SSE, or long-poll transport exists. The HTTP server only mounts the Express REST app. A push transport would be a NEW PATTERN.
**Evidence:**

```
const server = http.createServer(app); server.listen(PORT)
```

— `src/server.js:12`
**Dependencies:** `src/app.js` (Express app only)
**Implicit contracts:** the server is a plain HTTP/REST listener; there is no upgrade handler registered for the WebSocket protocol.

## Q4: What is the existing REST polling endpoint for order status that must remain backward compatible per the constraint?

**Answer:** `GET /api/orders/:id/status` served by `getOrderStatus`; it returns the current status and is the endpoint the constraint requires we keep working.
**Evidence:**

```
router.get('/api/orders/:id/status', requireAuth, loadOrder, getOrderStatus)
```

— `src/routes/orders.js:27`
**Dependencies:** `src/middleware/auth.js`, `src/middleware/load_order.js`
**Implicit contracts:** `loadOrder` enforces ownership before the handler; the route must remain unchanged for polling fallback.

## Q5: How is a client's identity and the set of orders it owns currently established on a request?

**Answer:** `requireAuth` populates `req.auth` from the bearer token; `loadOrder` looks up the order and rejects with 403 unless `order.customerId === req.auth.userId` or the caller is staff.
**Evidence:**

```
if (order.customerId !== req.auth.userId && !req.auth.staff) return fail(res, 403)
```

— `src/middleware/load_order.js:19`
**Dependencies:** `src/auth/token.js`
**Implicit contracts:** ownership is decided per-request from the token subject; there is no persistent per-user connection concept.

## Q6: Where would per-connection subscription state live, and is there an existing in-memory or shared store for ephemeral connection data?

**Answer:** NOT FOUND. Searched for a connection registry, Redis pub/sub, or in-memory subscription map; none exists. Sessions are stateless JWTs, so there is no current place that holds live per-connection state.
**Evidence:**

```
// stateless: no session store; auth is verified per request from the JWT
const claims = jwt.verify(token, SECRET)
```

— `src/auth/token.js:8`
**Dependencies:** none
**Implicit contracts:** the server holds no per-client live state today; introducing it is a new responsibility.

## Q7: How does the system behave today when a client requests order status for an order it does not own?

**Answer:** `loadOrder` returns `403` with `{ error: { code: 'forbidden', message } }` before the handler runs, identical to the REST ownership gate.
**Evidence:**

```
return BaseController.fail(res, 403, 'forbidden', 'Not your order')
```

— `src/middleware/load_order.js:20`
**Dependencies:** `src/controllers/base.js`
**Implicit contracts:** ownership denial is centralized in middleware; any push channel must reuse the same `customerId` check, not reinvent it.

## Q8: What happens to in-flight requests and client state when the process restarts or a connection drops?

**Answer:** Because the server is stateless and poll-based, a restart loses nothing client-visible: the next poll simply succeeds against the new process. There is no reconnect logic because there is no persistent connection today.
**Evidence:**

```
// polling client retries on the next interval; no socket to reconnect
fetchStatus(orderId).catch(() => {/* swallow, retry next tick */})
```

— `web/src/pages/order_tracking.js:46`
**Dependencies:** none
**Implicit contracts:** transient failures are absorbed by the next poll; a push design must add its own reconnect-within-5s behavior.

## Q9: How does the load balancer route repeat requests from the same client today (sticky sessions, round-robin)?

**Answer:** The nginx config uses plain round-robin with no affinity; since the app is stateless this is fine today, but a stateful WebSocket would need sticky sessions or a shared backplane.
**Evidence:**

```
upstream app { server app1:3000; server app2:3000; }
```

— `deploy/nginx.conf:8`
**Dependencies:** `deploy/nginx.conf`
**Implicit contracts:** no `ip_hash`/sticky directive is present; the round-robin assumption breaks for long-lived connections.

## Q10: What test harness covers the order status read path, and does it support asserting on streamed/async delivery?

**Answer:** Tests use `supertest` against the Express app for the REST status route; there is no harness for asserting on streamed or pushed delivery.
**Evidence:**

```
const res = await request(app).get('/api/orders/'+id+'/status').set('Authorization', token)
```

— `test/routes/orders.test.js:34`
**Dependencies:** `test/helpers/auth.js`
**Implicit contracts:** the suite is request/response oriented; testing push delivery requires new async/socket test utilities.

## Q11: Is there any existing scaffold for load- or concurrency-testing connections to measure the memory-per-1000-connections criterion?

**Answer:** NOT FOUND. Searched `test/`, `perf/`, and `package.json` scripts for `autocannon`, `k6`, `artillery`, and `connections`; no concurrency or memory-profiling scaffold exists. The "< 10% memory increase per 1000 connections" criterion has no current automated check.
**Evidence:**

```
// grep -r "autocannon\|k6\|artillery" test/ perf/  -> no matches
```

— `package.json:14`
**Dependencies:** none
**Implicit contracts:** connection-scaling targets are unverified by any existing harness.

## Q12: How are connection counts and message-delivery latencies measured today, if at all?

**Answer:** Only HTTP request duration is measured via the global `timing` middleware; there are no connection-count gauges or delivery-latency metrics because there are no persistent connections.
**Evidence:**

```
app.use(timing({ histogram: 'http.request.duration' }))
```

— `src/app.js:21`
**Dependencies:** `src/observability/metrics.js`
**Implicit contracts:** the metric vocabulary is request-scoped; a push design must add connection-gauge and delivery-latency metrics from scratch.

## Q13: How are dropped connections and reconnect attempts logged on the server?

**Answer:** NOT FOUND. There is no connection lifecycle to log; request-level logging exists but no `connection.opened`/`connection.closed` events are emitted anywhere.
**Evidence:**

```
// grep -r "connection.opened\|connection.closed\|socket" src/  -> no matches
logger.info({ event: 'http.request', route })
```

— `src/observability/logger.js:19`
**Dependencies:** `src/observability/logger.js`
**Implicit contracts:** logging is per-request; connection lifecycle logging would be new.

---

## Discovered Patterns

- The entire order read path is stateless and poll-driven: `requireAuth → loadOrder → handler`, with ownership centralized in `loadOrder` and no persistent per-client state anywhere.
- Domain events are already emitted on status change (`order.status_changed`) but are consumed only by audit logging — the event bus is a ready hook a push transport could subscribe to.
- Errors are uniformly `{ error: { code, message } }` via `BaseController.fail`; a push channel should reuse the same ownership gate and error vocabulary.

## Inconsistencies

- A `order.status_changed` event is emitted on every status write, yet the client learns of changes only by polling every 10s — the system already produces the signal it fails to deliver in real time.
- The load balancer is round-robin with no affinity while the app is stateless; this is consistent today but directly conflicts with the ticket's "behind existing load balancer" constraint once long-lived connections are introduced.
