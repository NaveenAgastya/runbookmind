"""Streamlit UI for RunbookMind: alert panel, response panel, memory panel."""
import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
SERVICES = ["payments-api", "orders-api", "checkout-service", "auth-service", "api-gateway",
            "notification-service", "postgres-primary", "redis-cache", "logging-node-01", "logging-node-02"]
BADGE = {"low": "🔴 LOW", "medium": "🟠 MEDIUM", "high": "🟢 HIGH"}

st.set_page_config(page_title="RunbookMind", page_icon="🛟", layout="wide")


def api(method: str, path: str, **kwargs):
    """Call the backend; show a readable error instead of crashing the page."""
    try:
        resp = httpx.request(method, f"{BACKEND}{path}", timeout=90.0, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        st.error(f"Backend error {exc.response.status_code}: {exc.response.json().get('detail', exc.response.text)}")
    except httpx.HTTPError as exc:
        st.error(f"Cannot reach backend at {BACKEND}: {exc}")
    return None


@st.cache_data(ttl=60)
def demo_alerts() -> list[dict]:
    try:
        return httpx.get(f"{BACKEND}/demo-alerts", timeout=10).json()
    except httpx.HTTPError:
        return []


def load_demo() -> None:
    choice = st.session_state.demo_choice
    alert = next((a for a in demo_alerts() if a["label"] == choice), None)
    if alert:
        st.session_state.update(service=alert["service"], title=alert["title"],
                                log=alert["log_snippet"], change=alert["recent_change"])
    for key in ("single", "off", "on", "feedback_msg"):
        st.session_state.pop(key, None)


def render_suggestion(resp: dict, heading: str) -> None:
    s = resp["suggestion"]
    st.subheader(heading)
    if resp.get("from_cache"):
        st.warning("Live services unreachable: showing cached known-good response.")
    if not s["based_on_team_history"]:
        st.info("General guidance only. Not based on team history.")
    st.success(f"**Do first:** {s['recommended_first_action']}")
    st.markdown(f"**Likely root cause:** {s['likely_root_cause']}")
    st.markdown(f"**Confidence:** {BADGE[s['confidence']]} — {s['confidence_reason']}")
    if s["alternative_actions"]:
        st.markdown("**Alternatives**\n" + "\n".join(f"{i}. {a}" for i, a in enumerate(s["alternative_actions"], 1)))
    if s["actions_to_avoid"]:
        st.error("**Avoid these**\n\n" + "\n".join(f"- {a}" for a in s["actions_to_avoid"]))
    if s["similar_incidents"]:
        st.markdown("**Similar incidents**")
        for inc in s["similar_incidents"]:
            st.markdown(f"- `{inc['id']}` {inc['reason']}")
    st.caption(f"{resp['latency_ms'] / 1000:.1f}s · memory {'ON' if resp['used_memory'] else 'OFF'} · {resp['alert_id']}")


def feedback_form(resp: dict) -> None:
    st.markdown("---\n**Did it work?**")
    with st.form("feedback"):
        action = st.text_input("Action tried", resp["suggestion"]["recommended_first_action"])
        root = st.text_input("Actual root cause (optional)")
        fix = st.text_input("Actual fix (optional)")
        notes = st.text_input("Notes (optional)")
        cols = st.columns(3)
        outcome = None
        for col, (label, value) in zip(cols, [("✅ Worked", "worked"), ("🟡 Partially", "partial"), ("❌ Didn't work", "failed")]):
            if col.form_submit_button(label):
                outcome = value
    if outcome:
        with st.spinner("Retaining feedback in memory..."):
            result = api("POST", "/feedback", json={"alert_id": resp["alert_id"], "action_tried": action, "outcome": outcome,
                                                    "actual_root_cause": root, "actual_fix": fix, "notes": notes})
        if result:
            st.session_state.feedback_msg = result["message"]
    if st.session_state.get("feedback_msg"):
        st.success(st.session_state.feedback_msg)


def analyze(use_memory: bool) -> dict | None:
    payload = {"service": st.session_state.service, "title": st.session_state.title, "log_snippet": st.session_state.log,
               "recent_change": st.session_state.change, "use_memory": use_memory}
    return api("POST", "/analyze", json=payload)


# ---- state defaults ----
for key, default in {"service": SERVICES[0], "title": "", "log": "", "change": ""}.items():
    st.session_state.setdefault(key, default)

st.title("🛟 RunbookMind")
st.caption("The on-call teammate who has seen every outage your team has ever had, and learns from every fix.")
tab_triage, tab_ask, tab_timeline = st.tabs(["Triage", "Ask history", "Memory timeline"])

with tab_triage:
    left, center, right = st.columns([1, 1.7, 1.1])

    with left:
        st.subheader("Alert")
        labels = [a["label"] for a in demo_alerts()]
        st.selectbox("Load demo alert", [""] + labels, key="demo_choice", on_change=load_demo)
        st.selectbox("Service", SERVICES, key="service")
        st.text_input("Alert title", key="title")
        st.text_area("Error message / log snippet", key="log", height=130)
        st.text_input("Recent change (optional)", key="change", placeholder="deployed v2.4.1 20 minutes ago")
        memory_on = st.toggle("Memory ON", value=True)
        compare = st.toggle("Compare: memory OFF vs ON")
        if st.button("Analyze", type="primary", use_container_width=True, disabled=not st.session_state.title):
            st.session_state.pop("feedback_msg", None)
            with st.spinner("Recalling similar incidents and reasoning..."):
                if compare:
                    st.session_state.off, st.session_state.on = analyze(False), analyze(True)
                    st.session_state.pop("single", None)
                else:
                    st.session_state.single = analyze(memory_on)
                    st.session_state.pop("off", None)
                    st.session_state.pop("on", None)

    active = st.session_state.get("single") or st.session_state.get("on")
    with center:
        if st.session_state.get("off") and st.session_state.get("on"):
            c1, c2 = st.columns(2)
            with c1:
                render_suggestion(st.session_state.off, "Memory OFF")
            with c2:
                render_suggestion(st.session_state.on, "Memory ON")
        elif st.session_state.get("single"):
            render_suggestion(st.session_state.single, "Suggestion")
        else:
            st.info("Pick a demo alert or enter one, then press Analyze.")
        if active and active["used_memory"]:
            feedback_form(active)

    with right:
        st.subheader("Memory")
        if active and active["memories"]:
            for m in active["memories"]:
                with st.expander(f"{m.get('date') or 'undated'} · {m.get('context') or m.get('type') or 'memory'}"):
                    st.write(m["text"])
        else:
            st.caption("Recalled memories appear here.")
        info = api("GET", "/health") or {}
        if info.get("hindsight_ui"):
            st.link_button("Open Hindsight knowledge graph", info["hindsight_ui"])
        metrics = api("GET", "/metrics")
        if metrics and metrics["series"]:
            st.markdown(f"**Suggestion accuracy** (demo data): {metrics['accuracy_pct']}% over {metrics['total']} outcomes")
            st.line_chart(metrics["series"])

with tab_ask:
    question = st.text_input("Ask about team history", placeholder="What failed last time we touched the payments DB?")
    if st.button("Ask") and question:
        with st.spinner("Reflecting over memory..."):
            answer = api("POST", "/ask", json={"question": question})
        if answer:
            st.markdown(answer["answer"])
            for m in answer["sources"]:
                with st.expander(f"Source · {m.get('date') or 'undated'}"):
                    st.write(m["text"])

with tab_timeline:
    query = st.text_input("Filter (optional)", value="incident postmortem and engineer feedback")
    if st.button("Load timeline"):
        for m in api("GET", "/memories", params={"query": query}) or []:
            st.markdown(f"**{m.get('date') or 'undated'}** · _{m.get('context') or m.get('type') or ''}_")
            st.write(m["text"])

with st.sidebar:
    st.header("Demo admin")
    if st.button("Ingest all incidents"):
        with st.spinner("Retaining incidents..."):
            result = api("POST", "/ingest")
        if result:
            st.success(f"Retained {result['retained']} incidents")
    if st.button("Reset bank (demo only)"):
        if api("POST", "/reset"):
            st.success("Bank reset")
