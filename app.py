import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import concurrent.futures
import json
import math
import os
import re
import socket
import ssl
import threading
import time
from urllib.parse import urlparse
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st

# -------------------------------------------------------------
# 1. INTEGRATED BACKGROUND RECEIVER
# -------------------------------------------------------------
class InterceptorHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(post_body)
            visited_url = data.get("url", "")
            if visited_url.startswith("http"):
                with open("latest_url.txt", "w", encoding="utf-8") as f:
                    f.write(visited_url)
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_background_receiver():
    try:
        server = HTTPServer(("0.0.0.0", 8000), InterceptorHandler)
        server.serve_forever()
    except Exception:
        pass


if "receiver_thread_active" not in st.session_state:
    threading.Thread(target=start_background_receiver, daemon=True).start()
    st.session_state["receiver_thread_active"] = True

# -------------------------------------------------------------
# 2. PAGE CONFIGURATION & RETRO AMBER CRT STYLING
# -------------------------------------------------------------
st.set_page_config(
    page_title="threatlens://term-v220",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap');

    :root {
        --amber: #ffb000;
        --amber-glow: rgba(255, 176, 0, 0.4);
        --amber-dim: #996a00;
        --amber-faint: rgba(255, 176, 0, 0.08);
        --bg-crt: #0d0802;
        --bg-panel: #140d03;
        --line-dim: #3a2205;
        --good-amber: #ffc425;
        --alert-red: #ff3b30;
    }

    /* FIX TOP HEADER OVERLAP & CLIPPING */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2.5rem !important;
    }
    header[data-testid="stHeader"] * {
        color: var(--amber-dim) !important;
    }

    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* GLOBAL CANVAS */
    html, body, [class*="css"], .stApp {
        background-color: var(--bg-crt) !important;
        background-image: 
            radial-gradient(circle at 50% 50%, rgba(35, 22, 5, 0.4) 0%, #080501 100%),
            linear-gradient(rgba(255, 176, 0, 0.03) 1px, transparent 1px);
        background-size: 100% 100%, 100% 3px;
        color: var(--amber) !important;
        font-family: 'Share Tech Mono', monospace !important;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #080501 !important;
        border-right: 2px solid var(--amber-dim) !important;
    }
    [data-testid="stSidebar"] * {
        color: var(--amber) !important;
        font-family: 'Share Tech Mono', monospace !important;
    }

    /* CRT HEADER BAR */
    .crt-topbar {
        border: 2px solid var(--amber);
        padding: 10px 18px;
        background: var(--bg-panel);
        box-shadow: 0 0 15px var(--amber-glow), inset 0 0 10px var(--amber-faint);
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .crt-title {
        font-family: 'VT323', monospace;
        font-size: 2.1rem;
        color: var(--amber);
        text-shadow: 0 0 8px var(--amber);
        margin: 0;
        line-height: 1;
        letter-spacing: 0.06em;
    }
    .crt-status {
        font-size: 0.85rem;
        color: var(--amber-dim);
    }
    .crt-status span {
        color: var(--amber);
        text-shadow: 0 0 5px var(--amber);
    }

    .crt-prompt {
        font-size: 0.82rem;
        color: var(--amber-dim);
        margin-bottom: 18px;
        border-left: 3px solid var(--amber);
        padding-left: 10px;
    }
    .crt-prompt b { color: var(--amber); }

    /* UNIFIED METRIC GRID */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        border: 2px solid var(--amber-dim);
        background: var(--bg-panel);
        box-shadow: 0 0 14px rgba(255, 176, 0, 0.15);
        margin-bottom: 20px;
    }
    @media (max-width: 992px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 576px) { .metric-grid { grid-template-columns: 1fr; } }

    .metric-cell {
        padding: 14px 16px;
        border-right: 1px dashed var(--amber-dim);
        border-bottom: 1px dashed var(--amber-dim);
    }
    .metric-cell:last-child { border-right: none; }
    .cell-title {
        font-size: 0.72rem;
        color: var(--amber-dim);
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .cell-title::before { content: ">> "; }
    .cell-data {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--amber);
        text-shadow: 0 0 6px var(--amber-glow);
        word-break: break-all;
    }

    /* RETRO LOG VERDICT BANNER */
    .terminal-box {
        border: 2px solid var(--amber);
        padding: 14px 18px;
        background: #090500;
        box-shadow: inset 0 0 15px rgba(255, 176, 0, 0.12);
        margin-bottom: 22px;
    }
    .terminal-box.alert {
        border-color: var(--alert-red);
        box-shadow: 0 0 15px rgba(255, 59, 48, 0.3), inset 0 0 10px rgba(255, 59, 48, 0.15);
    }
    .term-headline {
        font-family: 'VT323', monospace;
        font-size: 1.45rem;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .terminal-box .term-headline { color: var(--amber); text-shadow: 0 0 8px var(--amber); }
    .terminal-box.alert .term-headline { color: var(--alert-red); text-shadow: 0 0 8px var(--alert-red); }
    .term-detail {
        font-size: 0.88rem;
        color: #d19a30;
        line-height: 1.45;
    }

    /* TELEMETRY PILL */
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid var(--amber-dim);
        padding: 5px 14px;
        font-size: 0.78rem;
        background: #170f03;
        margin-bottom: 14px;
    }
    .pill-dot {
        width: 8px; height: 8px;
        background: var(--amber);
        box-shadow: 0 0 6px var(--amber);
        animation: crtblink 1s steps(1) infinite;
    }
    @keyframes crtblink { 50% { opacity: 0; } }

    /* RETRO AMBER TABLE */
    .retro-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid var(--amber-dim);
        background: #090501;
        margin-top: 10px;
    }
    .retro-table th {
        background: #191003;
        color: var(--amber);
        border: 1px solid var(--amber-dim);
        padding: 8px 14px;
        text-align: left;
        font-size: 0.82rem;
        letter-spacing: 0.05em;
    }
    .retro-table td {
        border: 1px solid var(--line-dim);
        padding: 8px 14px;
        color: #dca331;
        font-size: 0.85rem;
    }
    .retro-table tr:hover {
        background: rgba(255, 176, 0, 0.05);
    }

    /* INPUTS & TEXT AREAS */
    div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
        background-color: #120b02 !important;
        border: 1px solid var(--amber-dim) !important;
        color: var(--amber) !important;
        border-radius: 0px !important;
    }
    div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within {
        border-color: var(--amber) !important;
        box-shadow: 0 0 8px var(--amber-glow) !important;
    }
    input, textarea {
        color: var(--amber) !important;
        font-family: 'Share Tech Mono', monospace !important;
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        border-bottom: 2px solid var(--amber-dim);
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--amber-dim) !important;
        border-radius: 0px !important;
        font-family: 'Share Tech Mono', monospace !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-bottom: none !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--amber) !important;
        background: #170f03 !important;
        border-color: var(--amber-dim) !important;
        text-shadow: 0 0 6px var(--amber);
    }

    .stJson {
        background: #090500 !important;
        border: 1px dashed var(--amber-dim) !important;
        color: var(--amber) !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# 3. LOW-LEVEL NETWORK PROBING (CE: Sockets & TLS)
# -------------------------------------------------------------
_NETWORK_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="net-probe"
)


def _run_with_hard_timeout(fn, timeout, default):
    try:
        future = _NETWORK_EXECUTOR.submit(fn)
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return default
    except Exception:
        return default


def get_dns_telemetry(hostname):
    if not hostname:
        return {"status": "NO_CARRIER", "ip": "0.0.0.0"}
    clean_host = hostname.split(":")[0]

    def _resolve():
        try:
            return {"status": "ACK_RESOLVED", "ip": socket.gethostbyname(clean_host)}
        except socket.gaierror:
            return {"status": "NXDOMAIN_FAULT", "ip": "UNREACHABLE"}
        except Exception:
            return {"status": "SOCKET_FAULT", "ip": "N/A"}

    return _run_with_hard_timeout(
        _resolve, timeout=3.0, default={"status": "DNS_TIMEOUT", "ip": "UNREACHABLE"}
    )


def inspect_ssl(hostname, port=443):
    if not hostname:
        return {"valid": True, "issuer": "N/A", "days_remaining": 0, "tls_version": "NONE"}
    clean_host = hostname.split(":")[0]

    def _probe():
        context = ssl.create_default_context()
        try:
            with socket.create_connection((clean_host, port), timeout=2.0) as sock:
                with context.wrap_socket(sock, server_hostname=clean_host) as ssock:
                    cert = ssock.getpeercert()
                    exp_date = datetime.datetime.strptime(
                        cert.get("notAfter"), "%b %d %H:%M:%S %Y %Z"
                    )
                    days_left = (exp_date - datetime.datetime.utcnow()).days
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    return {
                        "valid": True,
                        "issuer": issuer.get("organizationName", issuer.get("commonName", "CA_AUTHENTICATED")),
                        "days_remaining": days_left,
                        "tls_version": ssock.version(),
                    }
        except Exception:
            return {
                "valid": False,
                "issuer": "UNVERIFIED_PLAINTEXT",
                "days_remaining": 0,
                "tls_version": "INSECURE",
            }

    return _run_with_hard_timeout(
        _probe,
        timeout=3.5,
        default={
            "valid": False,
            "issuer": "TIMEOUT_NO_HANDSHAKE",
            "days_remaining": 0,
            "tls_version": "INSECURE",
        },
    )


# -------------------------------------------------------------
# 4. PREDICTIVE ENGINES (M.Sc. IT: NLP & Tree Models)
# -------------------------------------------------------------
def calculate_entropy(text):
    if not text:
        return 0.0
    entropy = 0.0
    for x in set(text):
        p_x = float(text.count(x)) / len(text)
        entropy += -p_x * math.log(p_x, 2)
    return float(entropy)


URL_FEATURES = [
    "URL Length", "Host Length", "Dot Count", "Hyphen Count",
    "At-Symbols (@)", "Slash Count", "HTTPS Enabled", "Raw IP Present", "Shannon Entropy",
]


def extract_url_vector(url):
    parsed = urlparse(url)
    hostname = parsed.netloc if parsed.netloc else parsed.path
    ip_pattern = r"(([01]?\d\d?|2[0-4]\d|25[0-5])\.){3}([01]?\d\d?|2[0-4]\d|25[0-5])"
    has_ip = 1 if re.search(ip_pattern, hostname) else 0
    return [
        len(url), len(hostname), url.count("."), url.count("-"), url.count("@"),
        url.count("/"), 1 if parsed.scheme == "https" else 0, has_ip,
        round(calculate_entropy(url), 4),
    ]


@st.cache_resource
def load_models():
    url_train = [
        ("https://www.google.com", 0),
        ("https://github.com/torvalds/linux", 0),
        ("https://aws.amazon.com/console/", 0),
        ("https://payroll.razorpay.com/login", 0),
        ("https://git-scm.com", 0),
        ("https://claude.ai", 0),
        ("https://en.wikipedia.org/wiki/Main_Page", 0),
        ("http://192.168.1.105/login-verify-account.php?id=99", 1),
        ("http://paypal-security-update-center.com/login.html@verify", 1),
        ("http://bank-of-america-secure-login.support-portal.top", 1),
        ("http://free-crypto-giveaway-claim-now.xyz/wallet-auth", 1),
    ]
    u_X = [extract_url_vector(u) for u, _ in url_train]
    u_y = [l for _, l in url_train]
    url_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    url_clf.fit(u_X, u_y)

    sms_train = [
        ("Your OTP for SBI transaction is 482910. Valid for 10 mins. Do not share with anyone.", 0),
        ("Your Amazon order #402-984392 has been dispatched and will arrive tomorrow.", 0),
        ("Dear Customer, Your SBI account is suspended! Update PAN immediately at http://192.168.1.55/sbi-kyc", 1),
        ("URGENT: Power disconnection tonight at 9:30 PM due to unpaid bill. Visit http://wb-power-bill.top", 1),
    ]
    sms_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=150)
    s_X = sms_vec.fit_transform([t for t, _ in sms_train])
    sms_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    sms_clf.fit(s_X, [l for _, l in sms_train])

    return url_clf, sms_vec, sms_clf


url_clf, sms_vec, sms_clf = load_models()

# -------------------------------------------------------------
# 5. RETRO TERMINAL HEADER
# -------------------------------------------------------------
now_str = datetime.datetime.now().strftime("%H:%M:%S")
st.markdown(
    f"""
    <div class="crt-topbar">
        <div class="crt-title">▓ THREATLENS_OS // VT-220 CONSOLE</div>
        <div class="crt-status">BAUD: <span>9600-8N1</span> · TTY: <span>ACTIVE</span> · TIME: <span>{now_str}</span></div>
    </div>
    <div class="crt-prompt"><b>sys@gateway:~$</b> run --daemon zero_trust_telemetry.elf [OSI L4 + RFC1035 PROBER ACTIVE]</div>
    """,
    unsafe_allow_html=True,
)

auto_url = "https://payroll.razorpay.com/login"
if os.path.exists("latest_url.txt"):
    try:
        with open("latest_url.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("http"):
                auto_url = content
    except Exception:
        pass

with st.sidebar:
    st.markdown("### >> PIPELINE_ROUTING")
    mode = st.radio(
        "Select Operation Mode:",
        [
            "[1] DAEMON_AUTOFETCH_FEED",
            "[2] MANUAL_VECTOR_PROBE",
            "[3] SMS_SMISHING_DECONSTRUCTOR",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")


def render_cards(title, host, ip, tls, is_tls_valid, prob, is_threat):
    risk_color = "var(--alert-red)" if is_threat else "var(--good-amber)"
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-cell">
                <div class="cell-title">{title}</div>
                <div class="cell-data">{host}</div>
            </div>
            <div class="metric-cell">
                <div class="cell-title">SOCKET_IP</div>
                <div class="cell-data">{ip}</div>
            </div>
            <div class="metric-cell">
                <div class="cell-title">CIPHER_HANDSHAKE</div>
                <div class="cell-data">{tls}</div>
            </div>
            <div class="metric-cell">
                <div class="cell-title">THREAT_ENTROPY</div>
                <div class="cell-data" style="color:{risk_color};">{prob:.1f}%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_banner(is_threat, safe_title, safe_desc, threat_title, threat_desc):
    box_cls = "terminal-box alert" if is_threat else "terminal-box"
    head = threat_title if is_threat else safe_title
    body = threat_desc if is_threat else safe_desc
    prefix = "[ ALERT: THREAT_DETECTED ]" if is_threat else "[ PASS: GATEWAY_SECURE ]"
    st.markdown(
        f"""
        <div class="{box_cls}">
            <div class="term-headline">{prefix} :: {head}</div>
            <div class="term-detail">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_retro_table(headers, rows):
    th_html = "".join([f"<th>{h}</th>" for h in headers])
    tr_html = "".join([
        "<tr>" + "".join([f"<td>{cell}</td>" for cell in row]) + "</tr>"
        for row in rows
    ])
    st.markdown(
        f"""
        <table class="retro-table">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{tr_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


# =============================================================
# PIPELINE 1: AUTO-FETCH STREAM
# =============================================================
if mode == "[1] DAEMON_AUTOFETCH_FEED":
    st.markdown(
        """
        <div class="pill">
            <span class="pill-dot"></span> LISTENING PORT :8000 · ASYNC INTERCEPT DRIVER RUNNING
        </div>
        """,
        unsafe_allow_html=True,
    )

    parsed = urlparse(auto_url)
    hostname = parsed.netloc if parsed.netloc else parsed.path
    vec = extract_url_vector(auto_url)
    pred = url_clf.predict([vec])[0]
    prob = url_clf.predict_proba([vec])[0]

    with st.spinner(">> INTERROGATING KERNEL SOCKET..."):
        dns_telemetry = get_dns_telemetry(hostname)
        ssl_telemetry = (
            inspect_ssl(hostname)
            if parsed.scheme == "https"
            else {"valid": False, "issuer": "PLAINTEXT_TRAFFIC", "days_remaining": 0, "tls_version": "INSECURE"}
        )

    render_cards(
        "INGRESS_DOMAIN", hostname[:24], dns_telemetry["ip"],
        ssl_telemetry["tls_version"], ssl_telemetry["valid"], prob[1] * 100, pred == 1,
    )

    render_banner(
        pred == 1,
        "TELEMETRY CLEARED",
        f"Host resolves cleanly. Handshake issued by {ssl_telemetry['issuer']} ({ssl_telemetry['days_remaining']} days validity left). Shannon dispersion minimal.",
        "MALICIOUS PHISHING INGRESS HALTED",
        "High Shannon structural randomness detected. Ingress destination mimics high-value authentication pages or lacks validated cryptographic provenance.",
    )

    t1, t2 = st.tabs([">> FEATURE_VECTORS", ">> SOCKET_TELEMETRY"])
    with t1:
        render_retro_table(["VECTOR_PARAM", "MEASURED_VALUE"], list(zip(URL_FEATURES, vec)))
    with t2:
        st.json({
            "Target URL": auto_url,
            "Domain Host": hostname,
            "Resolved IP": dns_telemetry["ip"],
            "Certificate Authority": ssl_telemetry["issuer"],
            "Cipher Protocol": ssl_telemetry["tls_version"],
        })

    time.sleep(1.5)
    if os.path.exists("latest_url.txt"):
        try:
            with open("latest_url.txt", "r", encoding="utf-8") as f:
                newest = f.read().strip()
            if "last_seen_url" not in st.session_state:
                st.session_state["last_seen_url"] = newest
            elif st.session_state["last_seen_url"] != newest:
                st.session_state["last_seen_url"] = newest
                st.rerun()
        except Exception:
            pass

# =============================================================
# PIPELINE 2: MANUAL URL INSPECTOR
# =============================================================
elif mode == "[2] MANUAL_VECTOR_PROBE":
    st.sidebar.markdown("### >> PRESET_PAYLOADS")
    presets = {
        "Custom Input Payload": "",
        "Auth: Razorpay Gateway": "https://payroll.razorpay.com/login",
        "Auth: AWS Cloud Center": "https://aws.amazon.com",
        "Auth: Linux Kernel Git": "https://github.com/torvalds/linux",
        "Attack: Raw IP Spoof": "http://192.168.1.105/login-verify-account.php?id=99",
        "Attack: Fake Banking Portal": "http://bank-of-america-secure-login.support-portal.top",
    }
    choice = st.sidebar.selectbox("Test Scenario:", list(presets.keys()), label_visibility="collapsed")
    user_url = st.text_input(
        "INPUT TARGET URL TO INSPECT:",
        value=presets[choice] if choice != "Custom Input Payload" else "https://git-scm.com",
    )

    if user_url:
        parsed = urlparse(user_url)
        hostname = parsed.netloc if parsed.netloc else parsed.path
        vec = extract_url_vector(user_url)
        pred = url_clf.predict([vec])[0]
        prob = url_clf.predict_proba([vec])[0]

        with st.spinner(">> INTERROGATING KERNEL SOCKET..."):
            dns_data = get_dns_telemetry(hostname)
            ssl_data = (
                inspect_ssl(hostname)
                if parsed.scheme == "https"
                else {"valid": False, "issuer": "PLAINTEXT_TRAFFIC", "days_remaining": 0, "tls_version": "INSECURE"}
            )

        render_cards("EVAL_DOMAIN", hostname[:24], dns_data["ip"], ssl_data["tls_version"], ssl_data["valid"], prob[1] * 100, pred == 1)

        render_banner(
            pred == 1,
            "INSPECTION PASS",
            f"Nominal lexical indicators. Authenticated certificate issuer: {ssl_data['issuer']}.",
            "MALICIOUS SIGNATURE RECOGNIZED",
            "Elevated lexical vector anomaly detected. Significant heuristic alignment with credential stealer kits.",
        )

        t1, t2 = st.tabs([">> VECTOR_MATRIX", ">> KERNEL_LOG"])
        with t1:
            render_retro_table(["VECTOR_PARAM", "MEASURED_VALUE"], list(zip(URL_FEATURES, vec)))
        with t2:
            st.json({
                "Target URL": user_url,
                "Hostname": hostname,
                "Remote IP": dns_data["ip"],
                "Certificate Authority": ssl_data["issuer"],
                "TLS Protocol": ssl_data["tls_version"],
            })

# =============================================================
# PIPELINE 3: SMS SMISHING RECON
# =============================================================
else:
    st.sidebar.markdown("### >> PRESET_PAYLOADS")
    sms_presets = {
        "Clean: Bank Transaction OTP": "Your OTP for SBI transaction is 482910. Valid for 10 mins. Do not share with anyone.",
        "Clean: Logistics Update": "Your Amazon order #402-984392 has been dispatched and will arrive tomorrow.",
        "Scam: Bank Account Lockdown": "Dear Customer, Your SBI account is suspended! Update PAN immediately at http://192.168.1.55/sbi-kyc",
        "Scam: Power Grid Disconnection": "URGENT: Power disconnection tonight at 9:30 PM due to unpaid bill. Visit http://wb-power-bill.top",
    }
    s_choice = st.sidebar.selectbox("Test Scenario:", list(sms_presets.keys()), label_visibility="collapsed")
    sms_text = st.text_area("INGRESS SMS TELEMETRY STRING:", value=sms_presets[s_choice], height=100)

    if sms_text:
        urls = re.findall(r"http[s]?://[^\s]+", sms_text)
        ip_links = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/[^\s]*)?\b", sms_text)
        found_url = urls[0] if urls else (ip_links[0] if ip_links else None)

        ext_host = None
        if found_url:
            parsed = urlparse(found_url)
            ext_host = parsed.netloc if parsed.netloc else parsed.path.split("/")[0]

        with st.spinner(">> DECODING NLP + PROBING SOCKET..."):
            dns_res = get_dns_telemetry(ext_host)
            ssl_res = inspect_ssl(ext_host)

        vec_s = sms_vec.transform([sms_text])
        p_s = sms_clf.predict(vec_s)[0]
        prob_s = sms_clf.predict_proba(vec_s)[0]

        render_cards(
            "EXTRACTED_HOST", ext_host[:20] if ext_host else "CLEAN_TEXT_ONLY",
            dns_res["ip"], ssl_res["tls_version"], ssl_res["valid"], prob_s[1] * 100, p_s == 1,
        )

        render_banner(
            p_s == 1,
            "INFORMATIVE PAYLOAD VERIFIED",
            "Message contains ordinary transactional semantics. No social engineering urgency coercion identified.",
            "CRITICAL: SMISHING ATTACK DETECTED",
            "Message employs psychological manipulation and routes outbound traffic to an unauthenticated external endpoint.",
        )

        t1, t2 = st.tabs([">> STRUCTURAL_INDICATORS", ">> ENDPOINT_TELEMETRY"])
        with t1:
            render_retro_table(
                ["INDICATOR", "TELEMETRY_VALUE"],
                [
                    ["Payload Length", len(sms_text)],
                    ["Digit Count", sum(c.isdigit() for c in sms_text)],
                    ["Exclamation Marks", sms_text.count("!")],
                    ["Embedded URL Detected", "YES" if found_url else "NO"],
                ],
            )
        with t2:
            st.json({
                "Extracted URL": found_url if found_url else "None",
                "Domain Host": ext_host if ext_host else "None",
                "DNS Status": dns_res["status"],
                "Resolved IP": dns_res["ip"],
                "SSL Authority": ssl_res["issuer"],
                "Transport Protocol": ssl_res["tls_version"],
            })