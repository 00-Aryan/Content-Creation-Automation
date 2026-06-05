"""Streamlit SSE client component: injects JavaScript EventSource for real-time updates.

Uses st.components.v1.html() to create an EventSource connection to the SSE server.
Receives events via window.postMessage and updates Streamlit session state.
"""

import json
import streamlit as st
from typing import Optional


_SSE_CLIENT_JS_TEMPLATE = """
<div id="sse-status" style="
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-bottom: 4px;
    display: inline-block;
">
    <span id="sse-dot" style="
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        background-color: #888;
    "></span>
    <span id="sse-label">Connecting...</span>
</div>

<script>
(function() {
    const SSE_URL = "%s";
    const dot = document.getElementById("sse-dot");
    const label = document.getElementById("sse-label");
    let eventSource = null;
    let reconnectTimer = null;
    let lastEventId = null;

    function updateStatus(state) {
        if (state === "connected") {
            dot.style.backgroundColor = "#4CAF50";
            label.textContent = "Live";
        } else if (state === "disconnected") {
            dot.style.backgroundColor = "#f44336";
            label.textContent = "Disconnected";
        } else {
            dot.style.backgroundColor = "#FFC107";
            label.textContent = "Connecting...";
        }
    }

    function connect() {
        if (eventSource) {
            eventSource.close();
        }
        updateStatus("connecting");

        eventSource = new EventSource(SSE_URL + "/events");

        eventSource.onopen = function() {
            updateStatus("connected");
        };

        eventSource.addEventListener("notification_created", function(e) {
            var data = JSON.parse(e.data);
            lastEventId = data.event_id;
            window.parent.postMessage({
                type: "sse_notification",
                data: data
            }, "*");
        });

        eventSource.addEventListener("unread_count_updated", function(e) {
            var data = JSON.parse(e.data);
            window.parent.postMessage({
                type: "sse_unread_count",
                data: data
            }, "*");
        });

        eventSource.addEventListener("summary_updated", function(e) {
            var data = JSON.parse(e.data);
            window.parent.postMessage({
                type: "sse_summary",
                data: data
            }, "*");
        });

        eventSource.addEventListener("notification_read", function(e) {
            var data = JSON.parse(e.data);
            window.parent.postMessage({
                type: "sse_notification_read",
                data: data
            }, "*");
        });

        eventSource.addEventListener("notification_archived", function(e) {
            var data = JSON.parse(e.data);
            window.parent.postMessage({
                type: "sse_notification_archived",
                data: data
            }, "*");
        });

        eventSource.addEventListener("heartbeat", function(e) {
            // Keepalive — no action needed
        });

        eventSource.onerror = function() {
            updateStatus("disconnected");
            eventSource.close();
            // Auto-reconnect after 3 seconds
            reconnectTimer = setTimeout(connect, 3000);
        };
    }

    connect();
})();
</script>
"""


def render_sse_client(sse_port: int = 8502) -> None:
    """Render the SSE client JavaScript component.

    Injects EventSource connection to the SSE server and bridges
    events to Streamlit via window.postMessage.

    Args:
        sse_port: Port the SSE server is listening on.
    """
    js = _SSE_CLIENT_JS_TEMPLATE % f"http://localhost:{sse_port}"
    st.components.v1.html(js, height=30, scrolling=False)


def render_notification_badge_live(
    unread_count: int,
    sse_port: int = 8502,
) -> None:
    """Render notification badge with live SSE updates.

    Displays unread count badge that auto-updates via SSE.
    """
    badge_html = f"""
    <div id="live-badge" style="
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 14px;
        display: inline-block;
        background-color: {"#ff4444" if unread_count > 0 else "#4CAF50"};
        color: white;
        font-weight: bold;
    ">
        🔔 <span id="badge-count">{unread_count}</span> unread
    </div>

    <script>
    (function() {{
        var countEl = document.getElementById("badge-count");
        var badgeEl = document.getElementById("live-badge");

        window.addEventListener("message", function(event) {{
            if (event.data && event.data.type === "sse_unread_count") {{
                var newCount = event.data.data.unread_count;
                countEl.textContent = newCount;
                badgeEl.style.backgroundColor = newCount > 0 ? "#ff4444" : "#4CAF50";
                badgeEl.innerHTML = "🔔 <span id=\\"badge-count\\">" + newCount + "</span> unread";
            }}
        }});
    }})();
    </script>
    """
    st.components.v1.html(badge_html, height=35, scrolling=False)
