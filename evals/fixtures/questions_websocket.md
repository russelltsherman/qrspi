# Questions — Add WebSocket support for real-time order status updates

**Ticket:** ORD-892
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

## Data Flow

- Q1: How does an order status change currently propagate from the point of mutation to the client, and where in the code is the status field written?
  **Target:** the order service write path and the status-mutation call site
- Q2: How does the order tracking page learn about status changes today (poll interval, endpoint, payload shape)?
  **Target:** the client polling loop and the REST endpoint it calls

## API Surface

- Q3: What real-time transport, if any, already exists in the server (WebSocket, SSE, long-poll), and how is it mounted on the HTTP server?
  **Target:** the server bootstrap and any existing socket/transport module
- Q4: What is the existing REST polling endpoint for order status that must remain backward compatible per the constraint?
  **Target:** the order status route and its handler

## State Management

- Q5: How is a client's identity and the set of orders it owns currently established on a request?
  **Target:** the auth/session layer and the order-ownership lookup
- Q6: Where would per-connection subscription state live, and is there an existing in-memory or shared store for ephemeral connection data?
  **Target:** the session store or in-memory registry used for live state

## Edge Cases

- Q7: How does the system behave today when a client requests order status for an order it does not own?
  **Target:** the ownership gate on the order status route
- Q8: What happens to in-flight requests and client state when the process restarts or a connection drops?
  **Target:** the connection lifecycle and any reconnect handling on the client
- Q9: How does the load balancer route repeat requests from the same client today (sticky sessions, round-robin)?
  **Target:** the deployment/load-balancer configuration

## Testing

- Q10: What test harness covers the order status read path, and does it support asserting on streamed/async delivery?
  **Target:** the order route test directory and its async helpers
- Q11: Is there any existing scaffold for load- or concurrency-testing connections to measure the memory-per-1000-connections criterion?
  **Target:** the performance/load test configuration

## Observability

- Q12: How are connection counts and message-delivery latencies measured today, if at all?
  **Target:** the metrics emitter and any connection gauges
- Q13: How are dropped connections and reconnect attempts logged on the server?
  **Target:** the connection lifecycle logging
