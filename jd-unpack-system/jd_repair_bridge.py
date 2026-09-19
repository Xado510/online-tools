import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeoutError
import gzip
import hashlib
import html
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import datetime
import uuid
from decimal import Decimal, InvalidOperation
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

from gmssl import sm2, sm4
from websocket import create_connection


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PRINT_SCRIPT = os.path.join(ROOT_DIR, "trigger_barcode_print.ps1")
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"/usr/bin/google-chrome",
    r"/usr/bin/google-chrome-stable",
    r"/usr/bin/chromium",
    r"/usr/bin/chromium-browser",
    r"/opt/google/chrome/chrome",
]
DEFAULT_BAR_PRINTER = (
    r"D:\we\data\xwechat_files\wxid_4m1kqcgnvn2v22_d9be\msg\file\2026-07"
    r"\条码打印软件\条码打印软件\BarPrinter.exe"
)
JD_BASE = "https://baozang-out.jd.com"
JD_SERVICE_BASE = "https://jdservice.jdl.com"
SERVICEPLUS_BASE = "http://serviceplus.jdl.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
API_KEY_FILE = os.path.join(ROOT_DIR, "api_key.txt")
API_KEYS = set()
LATEST_RESULTS = {}
JDL_TOKEN = ""
JDL_COOKIE = ""
LAST_BARCODE_ERROR = ""
LAST_MCS_SERVICE_NO = ""
WRITTEN_SERVICE_LOG_MESSAGES = set()
SERVICE_LOG_ADD_INTERVAL_SECONDS = 5.0
SERVICE_LOG_MAX_ATTEMPTS = 2
SERVICE_LOG_RETRY_DELAYS = (2.0,)
SERVICE_LOG_CREDENTIAL_LOCKS = {}
SERVICE_LOG_CREDENTIAL_LAST_WRITE = {}
SERVICE_LOG_CREDENTIAL_GUARD = threading.Lock()
SERVICE_LOG_LOCKS = {}
SERVICE_LOG_LOCKS_GUARD = threading.Lock()
SERVICE_LOG_TASKS = {}
SERVICE_LOG_TASKS_GUARD = threading.Lock()
SERVICE_LOG_TASK_TTL_SECONDS = 3600
BAOZANG_REMARK_INTERVAL_SECONDS = 0.6
BAOZANG_REMARK_LOCKS = {}
BAOZANG_REMARK_LAST_WRITE = {}
BAOZANG_REMARK_GUARD = threading.Lock()
BAOZANG_ORDER_LOCKS = {}
REPAIR_STANDARD_CACHE = {}
REPAIR_STANDARD_CACHE_LOADED = False
REPAIR_STANDARD_LOCK = threading.Lock()
REPAIR_STANDARD_CACHE_FILE = os.path.join(ROOT_DIR, "repair_standard_cache.json")
REPAIR_OCR_WORKERS = 4
REPAIR_OCR_TIMEOUT_SECONDS = 30.0
SUMMER_CRYPTO_JS = ""
DIGITAL_CONFIG = {
    "cookie": "",
    "cookie2": "",
    "userId": "",
    "appCode": "",
    "shopCode": "",
}
DIGITAL_CONFIG_FILE = os.path.join(ROOT_DIR, "digital_config.json")
JDL_TOKEN_FILE = os.path.join(ROOT_DIR, "jdl_token.json")
CLIENT_CONFIG_FILE = os.path.join(ROOT_DIR, "client_configs.json")
CLIENT_CONFIGS = {}
CLIENT_JDL_TOKENS = {}
CLIENT_JDL_COOKIES = {}
SHARED_STATES = {}
SHARED_STATE_FILE = os.path.join(ROOT_DIR, "shared_state.json")
AGREEMENTS = {}
AGREEMENT_FILE = os.path.join(ROOT_DIR, "agreements.json")
AGREEMENT_PDF_DIR = os.path.join(ROOT_DIR, "agreement_pdfs")
AGREEMENT_LOCK = threading.Lock()
PRINT_AGENTS = {}
PRINT_JOBS = {}
PRINT_JOB_RESULTS = {}
PRINT_JOB_SEQ = 0
PRINT_LOCK = threading.Lock()
PERFORMANCE_MAP = {
    "01": "维修",
    "REPAIR": "维修",
    "02": "换新",
    "CHANGE_NEW": "换新",
    "05": "补贴",
    "SUBSIDY": "补贴",
    "08": "退货",
    "SALES_RETURN": "退货",
    "10": "增值服务",
    "ADD_VALUE": "增值服务",
    "11": "服务中台",
    "SERVICE_PLATFORM_THIRD_PART_RIGHT": "服务中台",
}
SERVICE_ORDER_STATE_NAMES = {
    "ZERO": "初审通过,待服务商接单",
    "ONE": "已接单,待接机",
    "TWO": "已接机,待服务商提交维修方案",
    "THREE": "提交方案待审核",
    "FOUR": "审核通过,待维修",
    "FIRVE": "审核不通过",
    "START_MAINTAIN": "维修中",
    "MAINTAIN_FINISH": "商品维修结束,待寄送",
    "MAINTAIN_FINISH_WAIT_VISIT": "商品维修结束,待上门送货",
    "MAINTAIN_FINISH_WAIT_SHORE": "商品维修结束,待客户到门店取商品",
    "RETURN_GOODS": "已寄送,待确认收货",
    "CUSTOMER_RECEIVE": "客服确认收货,待反馈结果",
    "RETURN_MAINTAIN": "客户不满意,待客服沟通,确认是否返修",
    "SERVICE_ORDER_END": "服务单结单",
    "CHANGE_SERVICE": "改派",
    "RETURN": "返修,待处理",
    "CANCEL": "取消履约",
    "MAINTAIN_FINISH_WAIT_PAY": "待打款",
    "FINISH_PAY": "已打款",
    "FAIL_PAY": "打款失败",
    "MERCHANT_REMOINDER": "催单待处理",
}
NO_OLD_PART_REASON_NAMES = {
    "200元以下双向物流，无需邮寄": "200元以下双向物流，无需邮寄",
    "原厂维修，厂家回收无旧件": "原厂维修，厂家回收无旧件",
    "耳机补配，无旧件": "耳机补配，无旧件",
    "补贴服务，无旧件": "补贴服务，无旧件",
    "调试调整，无旧件": "调试调整，无旧件",
    "清洗服务，无旧件": "清洗服务，无旧件",
    "交换维修，无旧件": "交换维修，无旧件",
    "该品类无残值": "该品类无残值",
    "无需返件": "无需返件",
}


def decode_body(raw, headers):
    if headers.get("Content-Encoding", "").lower() == "gzip":
        return gzip.decompress(raw).decode("utf-8", "ignore")
    return raw.decode("utf-8", "ignore")


def load_digital_config():
    try:
        with open(DIGITAL_CONFIG_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            DIGITAL_CONFIG.update(
                {
                    key: str(data.get(key) or "").strip()
                    for key in ("cookie", "cookie2", "userId", "appCode", "shopCode")
                }
            )
    except Exception:
        pass


def save_digital_config():
    try:
        with open(DIGITAL_CONFIG_FILE, "w", encoding="utf-8") as handle:
            json.dump(DIGITAL_CONFIG, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_jdl_token():
    global JDL_TOKEN, JDL_COOKIE
    try:
        with open(JDL_TOKEN_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            JDL_TOKEN = str(data.get("jdlToken") or "").strip()
            JDL_COOKIE = str(data.get("jdlCookie") or "").strip()
    except Exception:
        pass


def save_jdl_token():
    try:
        with open(JDL_TOKEN_FILE, "w", encoding="utf-8") as handle:
            json.dump(
                {"jdlToken": JDL_TOKEN, "jdlCookie": JDL_COOKIE},
                handle,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass


def load_client_configs():
    try:
        with open(CLIENT_CONFIG_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            digital = data.get("digital")
            if isinstance(digital, dict):
                CLIENT_CONFIGS.update(digital)
            tokens = data.get("jdlTokens")
            if isinstance(tokens, dict):
                CLIENT_JDL_TOKENS.update(tokens)
            cookies = data.get("jdlCookies")
            if isinstance(cookies, dict):
                CLIENT_JDL_COOKIES.update(cookies)
    except Exception:
        pass


def save_client_configs():
    try:
        with open(CLIENT_CONFIG_FILE, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "digital": CLIENT_CONFIGS,
                    "jdlTokens": CLIENT_JDL_TOKENS,
                    "jdlCookies": CLIENT_JDL_COOKIES,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass


def apply_settings_update(
    client_id,
    config_updates=None,
    jdl_token=None,
    jdl_cookie=None,
):
    global JDL_TOKEN, JDL_COOKIE
    if client_id:
        if config_updates:
            CLIENT_CONFIGS[client_id] = {
                **(CLIENT_CONFIGS.get(client_id) or {}),
                **config_updates,
            }
        if jdl_token is not None:
            CLIENT_JDL_TOKENS[client_id] = jdl_token
        if jdl_cookie is not None:
            CLIENT_JDL_COOKIES[client_id] = jdl_cookie
        save_client_configs()
        return

    if config_updates:
        DIGITAL_CONFIG.update(config_updates)
        save_digital_config()
    if jdl_token is not None:
        JDL_TOKEN = jdl_token
    if jdl_cookie is not None:
        JDL_COOKIE = jdl_cookie
    if jdl_token is not None or jdl_cookie is not None:
        save_jdl_token()


def load_shared_states():
    try:
        with open(SHARED_STATE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            for account, state in data.items():
                SHARED_STATES[account] = _normalize_shared_state(state)
    except Exception:
        pass


def save_shared_states():
    cleanup_shared_states()
    try:
        with open(SHARED_STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(SHARED_STATES, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_agreements():
    try:
        with open(AGREEMENT_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            AGREEMENTS.update(data)
    except Exception:
        pass


def save_agreements():
    try:
        with open(AGREEMENT_FILE, "w", encoding="utf-8") as handle:
            json.dump(AGREEMENTS, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def agreement_pdf_filename(record):
    digest = hashlib.sha256(
        str(record.get("id") or "").encode("utf-8")
    ).hexdigest()[:24]
    return "agreement_" + digest + ".pdf"


def agreement_text_sections():
    return [
        (
            "一、使用范围",
            [
                "1. 本软件仅用于北京保险服务中心内部业务处理，不得用于任何个人用途、对外经营、商业推广或其他未经授权的用途。",
                "2. 未经公司书面授权，不得将本软件、安装包、账号、访问密钥、接口权限、操作权限或相关配置提供给任何第三方使用。",
                "3. 不得将本软件复制、安装、迁移或远程共享至未授权设备、未授权账号或非公司人员。",
                "4. 本软件属于内部工作工具，不构成对外服务承诺，不得向客户、合作方或外部人员展示、演示或交付。",
            ],
        ),
        (
            "二、账号与设备责任",
            [
                "1. 使用人应妥善保管自己的账号、密码、Cookie、令牌、验证信息和设备访问权限。",
                "2. 不得借用、共用、转让、出售或公开账号及访问凭证。因个人保管不当造成的操作、数据泄露或其他后果，由使用人承担相应责任。",
                "3. 使用人应确保操作设备处于公司允许的安全环境中，禁止在公共电脑、无授权设备或不安全网络环境中使用。",
                "4. 离开工位或结束使用时，应及时退出账号并锁定设备。",
            ],
        ),
        (
            "三、数据与保密要求",
            [
                "1. 软件中涉及的订单、客户、维修、商品、物流、备注及其他业务数据，仅限在授权业务范围内查询和使用。",
                "2. 不得擅自复制、导出、截图、拍摄、转发、上传或向无关人员披露软件数据。",
                "3. 使用人应遵循最小必要原则，只查询、处理和保存完成当前工作所必需的信息。",
                "4. 发现数据泄露、账号异常、设备丢失、接口被滥用或其他安全事件时，应立即停止操作并向公司管理人员报告。",
            ],
        ),
        (
            "四、禁止行为",
            [
                "1. 禁止对软件进行破解、反编译、逆向工程、脱壳、注入、篡改、替换、二次打包或绕过授权验证。",
                "2. 禁止删除、遮挡或修改软件名称、版权标识、版本信息、日志记录和安全提示。",
                "3. 禁止绕过软件界面直接调用接口，禁止批量抓取、恶意请求、攻击服务器或影响系统正常运行。",
                "4. 禁止利用软件实施违规接机、虚假操作、数据篡改、越权处理或其他违反公司制度及平台规则的行为。",
                "5. 禁止擅自开发、传播或使用外挂、脚本、插件、自动化工具连接本软件或相关接口。",
            ],
        ),
        (
            "五、知识产权",
            [
                "1. 本软件的程序、代码、界面、文档、接口、标识及相关资料的知识产权归公司或合法权利人所有。",
                "2. 未经公司书面许可，任何人不得复制、修改、传播、出租、出售、许可他人使用或用于申请专利、著作权等权利。",
                "3. 本说明仅授予使用人在授权范围内进行内部使用的有限、可撤销、不可转让的使用权。",
            ],
        ),
        (
            "六、审计与监控",
            [
                "1. 公司有权基于信息安全、业务合规和系统运维需要，对软件登录、操作记录、接口调用、异常日志和设备信息进行审计。",
                "2. 使用人不得关闭、伪造、删除或规避必要的审计和日志功能。",
                "3. 对异常操作、超范围查询、数据外传或其他风险行为，公司有权暂停账号、收回权限并开展调查。",
            ],
        ),
        (
            "七、更新与维护",
            [
                "1. 使用人应使用公司提供的正式版本，不得自行修改、替换或传播非官方版本。",
                "2. 软件更新、接口调整、权限变更和维护安排，以公司正式通知为准。",
                "3. 因未授权修改、非官方版本、个人设备环境或违规操作造成的问题，公司不承担相应责任。",
            ],
        ),
        (
            "八、违规处理",
            [
                "1. 违反本说明的，公司有权立即停止授权、冻结账号、收回设备或软件使用权限，并按内部制度处理。",
                "2. 因违规使用造成公司、客户、合作方或其他第三方损失的，使用人应依法依规承担相应责任。",
                "3. 涉嫌违法犯罪的，公司有权移交司法机关处理。",
            ],
        ),
        (
            "九、其他说明",
            [
                "1. 本软件属于内部辅助工具，软件提示和自动处理结果仍需使用人按照业务流程进行必要核对。",
                "2. 本说明如与公司正式管理制度、保密协议、劳动合同、授权文件或法律法规不一致的，以公司正式制度和有效法律文件为准。",
                "3. 公司在合法合规范围内有权根据业务变化对本说明进行更新，更新后的内容以软件展示或公司正式通知为准。",
            ],
        ),
    ]


def build_agreement_html(record):
    sections = []
    for title, items in agreement_text_sections():
        paragraphs = "".join(
            "<p>" + html.escape(item) + "</p>" for item in items
        )
        sections.append(
            '<section><h2>'
            + html.escape(title)
            + "</h2>"
            + paragraphs
            + "</section>"
        )
    signature_rows = [
        ("使用者姓名", record.get("userName") or "--"),
        ("协议版本", record.get("version") or "--"),
        ("签署时间", record.get("acceptedAt") or "--"),
        ("设备编号", record.get("clientId") or "--"),
        ("电脑名称", record.get("machineName") or "--"),
        ("Windows 用户", record.get("windowsUser") or "--"),
        ("客户端版本", record.get("appVersion") or "--"),
        ("后台接收时间", record.get("serverReceivedAt") or "--"),
    ]
    signature_html = "".join(
        "<tr><th>"
        + html.escape(label)
        + "</th><td>"
        + html.escape(str(value))
        + "</td></tr>"
        for label, value in signature_rows
    )
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
@page { size: A4; margin: 16mm 15mm 18mm; }
* { box-sizing: border-box; }
body {
  margin: 0;
  color: #202733;
  font-family: "WenQuanYi Micro Hei", "Microsoft YaHei", sans-serif;
  font-size: 11px;
  line-height: 1.75;
}
.head { text-align: center; border-bottom: 2px solid #dce5f0; padding-bottom: 12px; }
h1 { margin: 0; font-size: 21px; letter-spacing: 0; }
.subtitle { margin-top: 5px; color: #667487; font-size: 12px; }
.notice {
  margin-top: 16px;
  padding: 11px 13px;
  border: 1px solid #dce5f0;
  border-radius: 8px;
  background: #f7faff;
}
section { page-break-inside: avoid; margin-top: 14px; }
h2 { margin: 0 0 5px; font-size: 13px; color: #24538f; }
p { margin: 2px 0; text-align: justify; }
.signature {
  page-break-inside: avoid;
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px solid #dce5f0;
}
.signature h2 { margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; }
th, td {
  padding: 7px 9px;
  border: 1px solid #e1e8f1;
  text-align: left;
}
th { width: 25%; color: #52677f; background: #f7faff; }
.declaration {
  margin-top: 15px;
  padding: 11px 13px;
  border: 1px solid #dce5f0;
  border-radius: 8px;
  background: #fbfdff;
}
.foot { margin-top: 16px; color: #7b8798; font-size: 10px; text-align: center; }
</style>
</head>
<body>
  <div class="head">
    <h1>SCRP 北京保险服务中心服务平台</h1>
    <div class="subtitle">内部使用同意说明 · 已签署版本</div>
  </div>
  <div class="notice">
    本软件仅限北京保险服务中心授权的内部员工，在授权设备、授权账号及授权业务范围内使用。
    使用人确认已完整阅读、理解并同意遵守本协议全部内容。
  </div>
  __AGREEMENT_SECTIONS__
  <div class="signature">
    <h2>签署信息</h2>
    <table>__SIGNATURE_ROWS__</table>
  </div>
  <div class="declaration">
    本人确认：以上姓名由本人填写，点击“同意”即视为本人签署本使用协议，并承诺仅在公司授权范围内使用本软件。
  </div>
  <div class="foot">SCRP 北京保险服务中心服务平台 · 内部使用签署凭证</div>
</body>
</html>""".replace(
        "__AGREEMENT_SECTIONS__", "".join(sections)
    ).replace("__SIGNATURE_ROWS__", signature_html)


def ensure_agreement_pdf(record):
    pdf_name = record.get("pdfFile") or agreement_pdf_filename(record)
    pdf_path = os.path.join(AGREEMENT_PDF_DIR, pdf_name)
    if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
        record["pdfFile"] = pdf_name
        return pdf_name

    os.makedirs(AGREEMENT_PDF_DIR, exist_ok=True)
    html_path = os.path.join(
        tempfile.gettempdir(),
        "scrp-agreement-" + secrets.token_hex(8) + ".html",
    )
    try:
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(build_agreement_html(record))
        chrome = _find_edge_path()
        command = [
            chrome,
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--print-to-pdf-no-header",
            "--print-to-pdf=" + pdf_path,
            "file://" + html_path,
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0 or not os.path.isfile(pdf_path):
            raise RuntimeError("Chrome PDF generation failed")
        record["pdfFile"] = pdf_name
        record["pdfGeneratedAt"] = datetime.datetime.now().isoformat(
            timespec="seconds"
        )
        record.pop("pdfError", None)
        return pdf_name
    finally:
        try:
            os.remove(html_path)
        except Exception:
            pass


def ensure_all_agreement_pdfs():
    with AGREEMENT_LOCK:
        records = list(AGREEMENTS.values())
    changed = False
    for record in records:
        try:
            ensure_agreement_pdf(record)
            changed = True
        except Exception as error:
            record["pdfError"] = str(error)
            changed = True
    if changed:
        with AGREEMENT_LOCK:
            save_agreements()


def load_api_keys():
    try:
        with open(API_KEY_FILE, encoding="utf-8") as handle:
            for raw_line in handle:
                key = raw_line.strip()
                if key and len(key) >= 8:
                    API_KEYS.add(key)
    except Exception:
        pass


def _state_time_value(value):
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.timestamp()
    except Exception:
        return 0.0


def _state_timestamp(item):
    if not isinstance(item, dict):
        return 0.0
    return _state_time_value(
        item.get("updatedAt")
        or item.get("unpackedAt")
        or item.get("createdAt")
    )


def cleanup_shared_states():
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    cutoff_value = cutoff.replace(tzinfo=datetime.timezone.utc).timestamp()
    removed = 0
    for account, state in SHARED_STATES.items():
        if not isinstance(state, dict):
            continue
        items = state.get("parcels") or []
        kept = []
        for item in items:
            timestamp = _state_timestamp(item)
            if not timestamp or timestamp >= cutoff_value:
                kept.append(item)
            else:
                removed += 1
        state["parcels"] = kept
    if removed:
        sys.stdout.write(
            "bridge: cleaned %d old parcel records\n" % removed
        )
        sys.stdout.flush()


def _state_identity(item, id_key):
    if id_key == "tracking":
        tracking = str(item.get("tracking") or "").strip()
        if tracking:
            return tracking.upper()
        value = item.get("id")
        return str(value) if value else ""
    value = item.get(id_key)
    return str(value) if value else ""


def _merge_state_list(stored, incoming, id_key="id", cleared_at=""):
    combined = {}
    cleared_value = _state_time_value(cleared_at)
    for item in list(stored or []) + list(incoming or []):
        if not isinstance(item, dict):
            continue
        if cleared_value and _state_timestamp(item) < cleared_value:
            continue
        key = _state_identity(item, id_key)
        if not key:
            continue
        if key not in combined or _state_timestamp(item) >= _state_timestamp(combined[key]):
            combined[key] = item
    return list(combined.values())


def _normalize_shared_state(state):
    if not isinstance(state, dict):
        return state
    normalized = merge_shared_state({}, state)
    if state.get("clearedAt"):
        normalized["clearedAt"] = state["clearedAt"]
    return normalized


def merge_shared_state(stored, incoming):
    stored = stored or {}
    incoming = incoming or {}
    cleared_at = str(
        stored.get("clearedAt") or incoming.get("clearedAt") or ""
    )
    return {
        "schemaVersion": int(
            stored.get("schemaVersion")
            or incoming.get("schemaVersion")
            or 2
        ),
        "parcels": _merge_state_list(
            stored.get("parcels"),
            incoming.get("parcels"),
            id_key="tracking",
            cleared_at=cleared_at,
        ),
        "anomalies": _merge_state_list(
            stored.get("anomalies"),
            incoming.get("anomalies"),
            cleared_at=cleared_at,
        ),
        **({"clearedAt": cleared_at} if cleared_at else {}),
    }


def find_barcode_printer():
    if os.path.isfile(DEFAULT_BAR_PRINTER):
        return DEFAULT_BAR_PRINTER
    roots = [
        r"D:\we\data\xwechat_files",
        r"C:\Users\zx173\Desktop",
        r"C:\Users\zx173\Downloads",
        r"C:\Users\zx173\Documents",
        "D:\\",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
    ]
    skip_dirs = {
        "windows",
        "programdata",
        "$recycle.bin",
        "system volume information",
        "node_modules",
        ".git",
        "appdata",
    }
    for root in roots:
        if not os.path.isdir(root):
            continue
        for current, dirs, files in os.walk(root):
            depth = current[len(root):].count(os.sep)
            if depth >= 5:
                dirs[:] = []
            dirs[:] = [
                name
                for name in dirs
                if name.lower() not in skip_dirs
                and not name.startswith("$")
                and not name.startswith(".")
            ]
            try:
                for name in files:
                    if name.lower() == "barprinter.exe":
                        return os.path.join(current, name)
                for name in dirs:
                    if "条码打印软件" in name:
                        nested = os.path.join(current, name, "BarPrinter.exe")
                        if os.path.isfile(nested):
                            return nested
            except Exception:
                continue
    return ""


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
        for value in obj.values():
            result = find_key(value, key)
            if result not in (None, ""):
                return result
    elif isinstance(obj, list):
        for value in obj:
            result = find_key(value, key)
            if result not in (None, ""):
                return result
    return None


def extract_cookie_value(cookie_text, name):
    for part in (cookie_text or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return ""


def call_jd(path, payload, cookie, user_id, app_code):
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Content-Type": "application/json",
        "Origin": "https://digital-ins.jd.com",
        "Referer": "https://digital-ins.jd.com/repair/business/pendingServiceList",
        "sysType": "1",
        "User-Agent": UA,
    }
    if cookie:
        headers["Cookie"] = cookie.replace("\r", "").replace("\n", "")
    if user_id:
        headers["userId"] = user_id.strip()
    if app_code:
        headers["appcode"] = app_code.strip()
    request = urllib.request.Request(
        JD_BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = decode_body(response.read(), response.headers)
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = decode_body(error.read(), error.headers)
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": f"HTTP {error.code}: {body[:200]}"}
    except Exception as error:
        return {"success": False, "error": str(error)}


def call_jd_get(path, cookie, user_id, app_code):
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Content-Type": "application/json",
        "Origin": "https://digital-ins.jd.com",
        "Referer": "https://digital-ins.jd.com/repair/business/pendingServiceList",
        "sysType": "1",
        "User-Agent": UA,
    }
    if cookie:
        headers["Cookie"] = cookie.replace("\r", "").replace("\n", "")
    if user_id:
        headers["userId"] = user_id.strip()
    if app_code:
        headers["appcode"] = app_code.strip()
    request = urllib.request.Request(
        JD_BASE + path,
        headers=headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = decode_body(response.read(), response.headers)
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = decode_body(error.read(), error.headers)
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": f"HTTP {error.code}: {body[:200]}"}
    except Exception as error:
        return {"success": False, "error": str(error)}


def validate_digital_cookie(cookie_text):
    cookie_text = str(cookie_text or "").strip()
    if not cookie_text:
        return False
    user_id = extract_cookie_value(cookie_text, "pin")
    app_code = extract_cookie_value(cookie_text, "systemCode")
    response = call_jd(
        "/serviceOrder/queryBindShopInfo",
        {},
        cookie_text,
        user_id,
        app_code,
    )
    return bool(response.get("success"))


def jd_encrypt_data(key_text, payload):
    decoded = base64.b64decode(key_text)
    if len(decoded) < 65:
        raise RuntimeError("SM key too short")
    public_key = decoded[-65:].hex()
    public_key_header = decoded[:-65].hex()

    sm4_key = secrets.token_hex(8)
    iv = secrets.token_hex(16)

    crypt_sm2 = sm2.CryptSM2(private_key="", public_key=public_key, mode=0)
    sm2_encrypted = crypt_sm2.encrypt(sm4_key.encode("ascii")).hex()

    sm4_key_bytes = sm4_key.encode("ascii")
    crypt_sm4 = sm4.CryptSM4()
    crypt_sm4.set_key(sm4_key_bytes, sm4.SM4_ENCRYPT)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sm4_encrypted = crypt_sm4.crypt_cbc(bytes.fromhex(iv), plaintext).hex()

    combined = (
        bytes.fromhex(public_key_header)
        + bytes.fromhex(sm2_encrypted)
        + bytes.fromhex(iv)
        + bytes.fromhex(sm4_encrypted)
    )
    return base64.b64encode(combined).decode("ascii")


def _find_edge_path():
    for candidate in EDGE_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    raise RuntimeError("Edge browser not found")


def _wait_debugger(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            request = urllib.request.Request(
                "http://127.0.0.1:%d/json/version" % port,
                headers={"User-Agent": "Codex/1.0"},
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                return json.loads(response.read().decode("utf-8", "ignore"))
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Edge debugger did not start")


def _get_page_ws(port):
    request = urllib.request.Request(
        "http://127.0.0.1:%d/json/list" % port,
        headers={"User-Agent": "Codex/1.0"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        targets = json.loads(response.read().decode("utf-8", "ignore"))
    for target in targets:
        if target.get("type") == "page":
            return target.get("webSocketDebuggerUrl")
    raise RuntimeError("Edge page target not found")


def _cdp(ws, method, params, message_id):
    ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
    while True:
        message = json.loads(ws.recv())
        if message.get("id") == message_id:
            return message


def _set_cdp_cookies(ws, cookie_text):
    cookies = []
    for part in (cookie_text or "").split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": ".jd.com",
                "path": "/",
                "secure": True,
                "sameSite": "None",
            }
        )
    if not cookies:
        return
    _cdp(ws, "Network.setCookies", {"cookies": cookies}, 1)


def _evaluate_cdp(ws, expression, await_promise=True, timeout=30):
    _cdp(ws, "Runtime.evaluate", {"expression": "1"}, 100)
    result = _cdp(
        ws,
        "Runtime.evaluate",
        {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
            "userGesture": True,
        },
        101,
    )
    return result


def _wait_page_ready(ws, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = _evaluate_cdp(
                ws,
                "document.readyState === 'complete' && typeof window.SummerCryptico !== 'undefined'",
                False,
            )
            value = (
                result.get("result", {})
                .get("result", {})
                .get("value")
            )
            if value:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def call_jd_encrypted_headless(path, payload, cookie, user_id, app_code, key_text):
    edge_path = _find_edge_path()
    port = 10240 + secrets.randbelow(20000)
    profile = os.path.join(
        os.environ.get("TEMP", ROOT_DIR),
        "jd-unpack-cdp-" + secrets.token_hex(4),
    )
    process = subprocess.Popen(
        [
            edge_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--remote-debugging-port=%d" % port,
            "--remote-allow-origins=*",
            "--user-data-dir=" + profile,
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    ws = None
    try:
        _wait_debugger(port)
        ws_url = _get_page_ws(port)
        ws = create_connection(ws_url, timeout=30)
        _cdp(ws, "Network.enable", {}, 2)
        _cdp(ws, "Page.enable", {}, 3)
        _set_cdp_cookies(ws, cookie)
        _cdp(
            ws,
            "Page.navigate",
            {"url": "https://digital-ins.jd.com/repair/business/pendingServiceList"},
            4,
        )
        if not _wait_page_ready(ws):
            raise RuntimeError("京东页面或 SummerCryptico 未加载完成")
        expression = (
            "(async () => {"
            " const keyResult = " + json.dumps(key_text) + ";"
            " const payload = " + json.dumps(payload, ensure_ascii=False) + ";"
            " return window.SummerCryptico.encryptData(keyResult, JSON.stringify(payload));"
            "})()"
        )
        result = _evaluate_cdp(ws, expression)
        exception = result.get("result", {}).get("exceptionDetails")
        if exception:
            raise RuntimeError(str(exception.get("exception", {}).get("description") or exception))
        encrypted_body = result.get("result", {}).get("result", {}).get("value")
        if not encrypted_body:
            raise RuntimeError("加密结果为空")
        return _post_encrypted_body(path, encrypted_body, cookie, user_id, app_code)
    finally:
        try:
            if ws:
                ws.close()
        except Exception:
            pass
        try:
            process.terminate()
        except Exception:
            pass
        try:
            import shutil

            shutil.rmtree(profile, ignore_errors=True)
        except Exception:
            pass


def auto_start_via_browser(express_no, cookie, user_id, app_code):
    edge_path = _find_edge_path()
    port = 10240 + secrets.randbelow(20000)
    profile = os.path.join(
        os.environ.get("TEMP", ROOT_DIR),
        "jd-unpack-cdp-" + secrets.token_hex(4),
    )
    process = subprocess.Popen(
        [
            edge_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--remote-debugging-port=%d" % port,
            "--remote-allow-origins=*",
            "--user-data-dir=" + profile,
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    ws = None
    try:
        _wait_debugger(port)
        ws_url = _get_page_ws(port)
        ws = create_connection(ws_url, timeout=30)
        _cdp(ws, "Network.enable", {}, 2)
        _cdp(ws, "Page.enable", {}, 3)
        _set_cdp_cookies(ws, cookie)
        local_script = (
            "try{"
            "localStorage.setItem('userInfo',"
            + json.dumps(json.dumps(user_id or ""))
            + ");"
            "localStorage.setItem('systemCode',"
            + json.dumps(app_code or "")
            + ");"
            "}catch(e){}"
        )
        _cdp(
            ws,
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": local_script},
            5,
        )
        _cdp(
            ws,
            "Page.navigate",
            {"url": "https://digital-ins.jd.com/repair/business/pendingServiceList"},
            6,
        )
        if not _wait_page_ready(ws):
            return {"ok": False, "error": "宝藏页面或加密组件未加载完成"}
        time.sleep(2)
        try:
            final_ws_url = _get_page_ws(port)
            final_ws = create_connection(final_ws_url, timeout=30)
            ws = final_ws
        except Exception as error:
            return {"ok": False, "error": "连接宝藏页面失败：" + str(error)}
        probe = _evaluate_cdp(
            ws,
            "document.readyState + '|' + location.href",
            False,
        )
        sys.stdout.write(
            "bridge: browser probe=%s\n"
            % json.dumps(probe, ensure_ascii=False)[:1200]
        )
        sys.stdout.flush()
        if probe.get("error"):
            return {"ok": False, "error": "宝藏页面连接不稳定：" + str(probe.get("error"))}
        code = str(express_no or "").strip()
        expression = r"""
(async () => {
  const code = __CODE__;
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const waitFor = async (fn, timeout) => {
    const end = Date.now() + (timeout || 30000);
    while (Date.now() < end) {
      const value = fn();
      if (value) return value;
      await sleep(400);
    }
    return null;
  };
  const input = await waitFor(() => Array.from(document.querySelectorAll('input')).find((el) => {
    const p = String(el.placeholder || '').trim();
    return (p === '快递单号' || p === '履约单号') && el.offsetParent !== null;
  }));
  if (!input) return {ok: false, error: '未找到快递单号/履约单号输入框'};
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, code);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new Event('change', {bubbles: true}));
  const queryButton = await waitFor(() => Array.from(document.querySelectorAll('button')).find((el) => {
    const text = (el.innerText || '').trim();
    return (text === '查询' || text === '查询查看' || text.includes('查询')) && el.offsetParent !== null;
  }));
  if (!queryButton) return {ok: false, error: '未找到查询按钮'};
  queryButton.click();
  const row = await waitFor(() => Array.from(document.querySelectorAll('.el-table__body-wrapper tbody tr, .el-table tbody tr')).find((el) => el.offsetParent !== null && (el.innerText || '').includes(code)), 35000);
  if (!row) return {ok: false, error: '未找到该单记录', found: false};
  await sleep(800);
  const receiveButton = await waitFor(() => Array.from(document.querySelectorAll('button')).find((el) => {
    const text = (el.innerText || '').trim();
    return (text === '确认接机' || text === '开始接机' || text.includes('接机')) && el.offsetParent !== null;
  }), 10000);
  if (!receiveButton) return {ok: false, error: '未找到确认接机按钮', found: false};
  receiveButton.click();
  await sleep(800);
  const confirmButton = Array.from(document.querySelectorAll('button')).find((el) => {
    const text = (el.innerText || '').trim();
    return (text === '确定' || text === '确认') && el.offsetParent !== null;
  });
  if (confirmButton) confirmButton.click();
  await sleep(1500);
  return {ok: true, found: true, message: '已触发确认接机'};
})()
"""
        expression = expression.replace("__CODE__", json.dumps(code))
        result = _evaluate_cdp(ws, expression)
        sys.stdout.write(
            "bridge: browser cdp result=%s\n"
            % json.dumps(result, ensure_ascii=False)[:4000]
        )
        sys.stdout.flush()
        exception = result.get("result", {}).get("exceptionDetails")
        if exception:
            detail = str(
                exception.get("exception", {}).get("description")
                or exception
            )
            return {"ok": False, "error": detail[:500]}
        value = result.get("result", {}).get("result", {}).get("value")
        return value or {"ok": False, "error": "浏览器自动接机未返回结果"}
    except Exception as error:
        return {"ok": False, "error": str(error)}
    finally:
        try:
            if ws:
                ws.close()
        except Exception:
            pass
        try:
            process.terminate()
        except Exception:
            pass
        try:
            import shutil

            shutil.rmtree(profile, ignore_errors=True)
        except Exception:
            pass


def _post_encrypted_body(path, encrypted_body, cookie, user_id, app_code):
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Content-Type": "application/json",
        "Origin": "https://digital-ins.jd.com",
        "Referer": "https://digital-ins.jd.com/repair/business/pendingServiceList",
        "sysType": "1",
        "User-Agent": UA,
    }
    if cookie:
        headers["Cookie"] = cookie.replace("\r", "").replace("\n", "")
    if user_id:
        headers["userId"] = user_id.strip()
    if app_code:
        headers["appcode"] = app_code.strip()
    request = urllib.request.Request(
        JD_BASE + path,
        data=encrypted_body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = decode_body(response.read(), response.headers)
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = decode_body(error.read(), error.headers)
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": f"HTTP {error.code}: {body[:200]}"}
    except Exception as error:
        return {"success": False, "error": str(error)}


def load_summer_cryptico_js():
    global SUMMER_CRYPTO_JS
    if SUMMER_CRYPTO_JS:
        return SUMMER_CRYPTO_JS
    url = (
        "https://storage.jd.com/public-static-resource/"
        "baozang/js/summer-cryptico-h5.min.js"
    )
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        SUMMER_CRYPTO_JS = decode_body(response.read(), response.headers)
    return SUMMER_CRYPTO_JS


def encrypt_with_summer_cryptico(key_text, payload):
    script_text = load_summer_cryptico_js()
    edge_path = _find_edge_path()
    port = 10240 + secrets.randbelow(20000)
    profile = os.path.join(
        os.environ.get("TEMP", ROOT_DIR),
        "jd-unpack-cdp-" + secrets.token_hex(4),
    )
    process = subprocess.Popen(
        [
            edge_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--remote-debugging-port=%d" % port,
            "--remote-allow-origins=*",
            "--user-data-dir=" + profile,
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    ws = None
    try:
        _wait_debugger(port)
        ws_url = _get_page_ws(port)
        ws = create_connection(ws_url, timeout=30)
        _cdp(ws, "Runtime.enable", {}, 2)
        load_result = _evaluate_cdp(
            ws,
            "eval(" + json.dumps(script_text) + ")",
            False,
        )
        load_exception = load_result.get("result", {}).get("exceptionDetails")
        if load_exception:
            raise RuntimeError(
                str(
                    load_exception.get("exception", {}).get("description")
                    or load_exception
                )
            )
        expression = (
            "(async () => {"
            " const keyResult = " + json.dumps(key_text) + ";"
            " const payload = " + json.dumps(payload, ensure_ascii=False) + ";"
            " return window.SummerCryptico.encryptData(keyResult, JSON.stringify(payload));"
            "})()"
        )
        result = _evaluate_cdp(ws, expression)
        exception = result.get("result", {}).get("exceptionDetails")
        if exception:
            raise RuntimeError(
                str(
                    exception.get("exception", {}).get("description")
                    or exception
                )
            )
        encrypted_body = result.get("result", {}).get("result", {}).get("value")
        if not encrypted_body:
            raise RuntimeError("SummerCryptico 加密结果为空")
        return encrypted_body
    finally:
        try:
            if ws:
                ws.close()
        except Exception:
            pass
        try:
            process.terminate()
        except Exception:
            pass
        try:
            import shutil

            shutil.rmtree(profile, ignore_errors=True)
        except Exception:
            pass


def call_jd_encrypted(path, payload, cookie, user_id, app_code):
    key_response = call_jd_get("/aks/getSMKey", cookie, user_id, app_code)
    sys.stdout.write(
        "bridge: getSMKey response=%s\n"
        % json.dumps(key_response, ensure_ascii=False)[:1000]
    )
    sys.stdout.flush()
    if not key_response.get("success"):
        return {
            "success": False,
            "error": str(
                key_response.get("showMsg")
                or key_response.get("msg")
                or key_response.get("error")
                or "获取加密密钥失败"
            ),
        }
    try:
        encrypted_body = encrypt_with_summer_cryptico(
            key_response.get("result"),
            payload,
        )
        return _post_encrypted_body(
            path,
            encrypted_body,
            cookie,
            user_id,
            app_code,
        )
    except Exception as error:
        sys.stdout.write(
            "bridge: summer cryptico error=%s\n" % str(error)
        )
        sys.stdout.flush()
    encrypted_body = jd_encrypt_data(key_response.get("result"), payload)
    sys.stdout.write(
        "bridge: encrypted body len=%d prefix=%s\n"
        % (len(encrypted_body), encrypted_body[:80])
    )
    sys.stdout.flush()
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Content-Type": "application/json",
        "Origin": "https://digital-ins.jd.com",
        "Referer": "https://digital-ins.jd.com/repair/business/pendingServiceList",
        "sysType": "1",
        "User-Agent": UA,
    }
    if cookie:
        headers["Cookie"] = cookie.replace("\r", "").replace("\n", "")
    if user_id:
        headers["userId"] = user_id.strip()
    if app_code:
        headers["appcode"] = app_code.strip()
    request = urllib.request.Request(
        JD_BASE + path,
        data=encrypted_body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = decode_body(response.read(), response.headers)
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = decode_body(error.read(), error.headers)
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": f"HTTP {error.code}: {body[:200]}"}
    except Exception as error:
        return {"success": False, "error": str(error)}


def call_jd_service(path, payload, jdl_token, jdl_cookie="", timeout=25):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://jdservice.jdl.com",
        "Referer": "https://jdservice.jdl.com/spc/repair/servicebilllist",
        "User-Agent": UA,
        "login-type": "2",
        "X-Requested-With": "XMLHttpRequest",
    }
    token_value = (jdl_token or "").strip()
    cookie_value = (
        (jdl_cookie or "").strip().replace("\r", "").replace("\n", "")
    )
    if token_value:
        headers["X-Access-Token"] = token_value
    if cookie_value:
        headers["Cookie"] = cookie_value
    elif token_value:
        headers["Cookie"] = "pin=" + token_value
    request = urllib.request.Request(
        JD_SERVICE_BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = decode_body(response.read(), response.headers)
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = decode_body(error.read(), error.headers)
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": f"HTTP {error.code}: {body[:200]}"}
    except Exception as error:
        return {"success": False, "error": str(error)}


def normalize_row(row):
    return {
        "performingOrderNo": find_key(row, "performingOrderNo") or find_key(row, "performingNo"),
        "serviceOrderNo": find_key(row, "serviceOrderNo"),
        "expressNo": find_key(row, "expressNo"),
        "serviceBillNo": find_key(row, "serviceBillNo"),
        "afsServiceBillNo": find_key(row, "afsServiceBillNo"),
        "facilitatorCode": find_key(row, "facilitatorCode"),
        "shopCode": find_key(row, "shopCode"),
        "serviceState": find_key(row, "serviceState"),
        "outerMainSkuThridCategory": find_key(row, "outerMainSkuThridCategory"),
        "outerMainSkuThirdCategory": find_key(row, "outerMainSkuThirdCategory"),
        "outerMainSkuName": find_key(row, "outerMainSkuName"),
        "outerSkuName": find_key(row, "outerSkuName"),
        "outerSku": find_key(row, "outerSku"),
    }


def format_performing_model(commit):
    leaf = find_key(commit, "leafPerformingModelName")
    code = find_key(commit, "performanceTypeEnum")
    if code in ("ADD_VALUE", "10") and leaf:
        return leaf
    return PERFORMANCE_MAP.get(code) or leaf or code or "未知状态"


def is_pending_start_row(row):
    state = str(find_key(row, "serviceState") or "").strip()
    return state in {
        "ZERO",
        "ONE",
        "WAIT_REPORT_INFO",
        "WAIT_VISIT",
        "WAIT_ARRIVE_STORE",
        "EXPRESS_INFO_FINISH",
        "WAIT_RECEIVE",
        "WAIT_RECEIVED",
        "TO_BE_RECEIVED",
        "RECEIVE",
    }


def query_parts_barcode(
    merchant_order_no,
    jdl_token,
    jdl_cookie="",
    client_id="",
    service_bill_no="",
    afs_service_bill_no="",
):
    global LAST_BARCODE_ERROR
    global LAST_MCS_SERVICE_NO
    LAST_BARCODE_ERROR = ""
    LAST_MCS_SERVICE_NO = ""
    candidates = []
    if merchant_order_no:
        candidates.append(
            {"merchantOrderNo": str(merchant_order_no).strip()}
        )
    if service_bill_no:
        candidates.append({"serviceBillNo": str(service_bill_no).strip()})
    if afs_service_bill_no:
        candidates.append({"afsServiceBillNo": str(afs_service_bill_no).strip()})
    if not candidates:
        return ""
    token, cookie = _resolve_service_credentials(jdl_token, jdl_cookie, client_id)
    for candidate in candidates:
        response = call_jd_service(
            "/spcapi/mcsServiceBill/page",
            {
                **candidate,
                "pageIndex": 1,
                "pageSize": 10,
                "serviceBillState": -1000,
                "createTimeBegin": None,
                "createTimeEnd": None,
            },
            token,
            cookie,
        )
        sys.stdout.write(
            "bridge: mcs page query=%r response=%s\n"
            % (candidate, json.dumps(response, ensure_ascii=False)[:2000])
        )
        sys.stdout.flush()
        if not isinstance(response, dict):
            LAST_BARCODE_ERROR = "京东物流返回格式异常"
            return ""
        if response.get("error") == "NotLogin" or response.get("success") is False:
            LAST_BARCODE_ERROR = str(
                response.get("error")
                or response.get("msg")
                or response.get("message")
                or "京东物流查询失败"
            )
            return ""
        data = response.get("data") or {}
        item_list = data.get("itemList") or []
        if item_list and isinstance(item_list, list):
            first = item_list[0]
            if isinstance(first, dict):
                if first.get("serviceBillNo"):
                    LAST_MCS_SERVICE_NO = str(first["serviceBillNo"]).strip()
                if first.get("partCode"):
                    return str(first["partCode"]).strip()
    LAST_BARCODE_ERROR = "京东物流未返回备件条码"
    return ""


def _resolve_service_credentials(jdl_token, jdl_cookie="", client_id=""):
    token = (jdl_token or "").strip() or CLIENT_JDL_TOKENS.get(client_id, "")
    cookie = (jdl_cookie or "").strip() or CLIENT_JDL_COOKIES.get(client_id, "")
    if not client_id:
        token = token or JDL_TOKEN
        cookie = cookie or JDL_COOKIE
    return token, cookie


def _clean_log_message(text):
    return str(text or "").replace("\r", " ").replace("\n", " ").strip()


def add_service_bill_log(
    service_bill_no,
    message,
    jdl_token,
    jdl_cookie="",
    client_id="",
):
    token, cookie = _resolve_service_credentials(jdl_token, jdl_cookie, client_id)
    credential_fingerprint = hashlib.sha256(
        (str(token or "") + "\n" + str(cookie or "")).encode("utf-8")
    ).hexdigest()[:12]
    if not service_bill_no or not message:
        return {"success": False, "error": "缺少服务单号或留言内容"}
    response = call_jd_service(
        "/mcs/log/add",
        {
            "serviceBillNo": str(service_bill_no).strip(),
            "logType": 2,
            "logMessage": str(message).strip(),
        },
        token,
        cookie,
        8,
    )
    sys.stdout.write(
        "bridge: service log add client=%r cred=%s service=%r message=%r result=%s\n"
        % (
            str(client_id or ""),
            credential_fingerprint,
            str(service_bill_no).strip(),
            str(message).strip()[:80],
            json.dumps(response, ensure_ascii=False)[:1200],
        )
    )
    sys.stdout.flush()
    return response


def _service_log_retryable(response):
    if not isinstance(response, dict):
        return True
    response_text = json.dumps(response, ensure_ascii=False).lower()
    permanent_markers = (
        "缺少服务单号",
        "缺少留言",
        "参数错误",
        "invalid parameter",
        "notlogin",
        "未登录",
        "无权限",
        "用户不在职",
        "请联系管理员",
        "重复",
        "已存在",
    )
    return not any(marker in response_text for marker in permanent_markers)


def _service_log_identity_error(response):
    response_text = json.dumps(response or {}, ensure_ascii=False).lower()
    return any(
        marker in response_text
        for marker in ("用户不在职", "无权限", "未登录", "请联系管理员")
    )


def add_service_bill_log_with_retry(
    service_bill_no,
    message,
    jdl_token,
    jdl_cookie="",
    client_id="",
):
    token, cookie = _resolve_service_credentials(jdl_token, jdl_cookie, client_id)
    credential_fingerprint = hashlib.sha256(
        (str(token or "") + "\n" + str(cookie or "")).encode("utf-8")
    ).hexdigest()[:12]
    with SERVICE_LOG_CREDENTIAL_GUARD:
        credential_lock = SERVICE_LOG_CREDENTIAL_LOCKS.get(credential_fingerprint)
        if credential_lock is None:
            credential_lock = threading.Lock()
            SERVICE_LOG_CREDENTIAL_LOCKS[credential_fingerprint] = credential_lock

    last_response = None
    attempts = []
    for attempt in range(1, SERVICE_LOG_MAX_ATTEMPTS + 1):
        with credential_lock:
            with SERVICE_LOG_CREDENTIAL_GUARD:
                last_write_at = SERVICE_LOG_CREDENTIAL_LAST_WRITE.get(
                    credential_fingerprint,
                    0.0,
                )
            elapsed = time.monotonic() - last_write_at
            wait_seconds = SERVICE_LOG_ADD_INTERVAL_SECONDS - elapsed
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            response = add_service_bill_log(
                service_bill_no,
                message,
                jdl_token,
                jdl_cookie,
                client_id,
            )
            with SERVICE_LOG_CREDENTIAL_GUARD:
                SERVICE_LOG_CREDENTIAL_LAST_WRITE[credential_fingerprint] = (
                    time.monotonic()
                )
        last_response = response
        attempts.append(
            {
                "attempt": attempt,
                "success": bool(response) and response.get("success") is True,
                "response": response,
            }
        )
        if bool(response) and response.get("success") is True:
            result = dict(response)
            result["attempts"] = attempt
            return result
        if not _service_log_retryable(response) or attempt >= SERVICE_LOG_MAX_ATTEMPTS:
            break
        time.sleep(SERVICE_LOG_RETRY_DELAYS[min(attempt - 1, len(SERVICE_LOG_RETRY_DELAYS) - 1)])

    result = dict(last_response or {})
    result.setdefault("success", False)
    result["attempts"] = len(attempts)
    result["attemptResults"] = attempts
    return result


def _service_fee_code(base):
    # 延保商品详情/服务单详情里的“服务方式”：
    # 1 = 谁寄谁付；2 = 快递寄送物流费用我方承担。
    code = str(base.get("logisticsFeeType") or "").strip()
    if code not in ("1", "2"):
        code = str(base.get("logisticsFree") or "").strip()
    return code


def _service_fee_remark(base):
    code = _service_fee_code(base)
    if code == "1":
        return "谁寄谁付"
    if code == "2":
        return "快递费我方承担"
    return ""


def _logistics_free_label(base):
    code = _service_fee_code(base)
    if code == "1":
        return "否"
    if code == "2":
        return "是"
    return ""


def _official_system_queryable(base):
    code = str(base.get("whetherWarranty") or "").strip()
    if not code:
        detail = base.get("detail") or {}
        code = str(
            find_key(detail, "whetherWarranty")
            or find_key(detail, "officialSystemQuery")
            or ""
        ).strip()
    return code.lower() in ("1", "true", "yes", "是")


def _load_repair_standard_cache():
    global REPAIR_STANDARD_CACHE_LOADED
    if REPAIR_STANDARD_CACHE_LOADED:
        return
    REPAIR_STANDARD_CACHE_LOADED = True
    try:
        with open(REPAIR_STANDARD_CACHE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            REPAIR_STANDARD_CACHE.update(
                {
                    str(key): str(value)
                    for key, value in data.items()
                    if str(value)
                    in ("original", "original_official", "non_original", "none")
                }
            )
    except Exception:
        pass


def _save_repair_standard_cache():
    try:
        with open(REPAIR_STANDARD_CACHE_FILE, "w", encoding="utf-8") as handle:
            json.dump(REPAIR_STANDARD_CACHE, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _normalize_detail_text(text):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", str(text or ""))


def _ocr_repair_detail(url, psm=6):
    normalized_url = str(url or "").strip()
    if normalized_url.startswith("//"):
        normalized_url = "https:" + normalized_url
    if not normalized_url.startswith(("http://", "https://")):
        return ""
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return ""
    request = urllib.request.Request(
        normalized_url,
        headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"},
    )
    temp_path = ""
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
        with tempfile.NamedTemporaryFile(
            prefix="scrp-repair-", suffix=".jpg", delete=False
        ) as handle:
            handle.write(body)
            temp_path = handle.name
        completed = subprocess.run(
            [
                tesseract,
                temp_path,
                "stdout",
                "-l",
                "chi_sim",
                "--psm",
                str(psm),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        return completed.stdout.decode("utf-8", "ignore")
    except Exception:
        return ""
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass


def _detect_repair_requirement_from_images(urls):
    _load_repair_standard_cache()
    if isinstance(urls, str):
        urls = [urls]
    if not isinstance(urls, list):
        return ""
    original_phrase = "本服务维修使用原厂配件按厂家标准进行维修不影响厂家标准保修"
    non_original_phrase = (
        "本服务使用非厂家部件进行维修后续可能会影响原商品厂家标准保修请您熟知非原厂"
    )

    normalized_urls = []
    seen_urls = set()
    for url in urls:
        url_key = str(url or "").strip()
        if url_key and url_key not in seen_urls:
            seen_urls.add(url_key)
            normalized_urls.append(url_key)
    if not normalized_urls:
        return ""

    with REPAIR_STANDARD_LOCK:
        for url_key in normalized_urls:
            cached = REPAIR_STANDARD_CACHE.get(url_key)
            if cached == "none":
                return ""
            if cached:
                return cached

    def detect_one(url_key, psm):
        normalized = _normalize_detail_text(_ocr_repair_detail(url_key, psm))
        if (
            original_phrase in normalized
            or (
                "原厂配件按厂家标准" in normalized
                and "不影响厂家标准保修" in normalized
            )
        ):
            return url_key, (
                "original_official"
                if "官方系统可查" in normalized or "官方可查" in normalized
                else "original"
            )
        if non_original_phrase in normalized or (
            "非厂家部件" in normalized
            and "影响原商品厂家标准保修" in normalized
        ):
            return url_key, "non_original"
        return url_key, ""

    executor = ThreadPoolExecutor(max_workers=REPAIR_OCR_WORKERS)
    futures = {}
    completed_count = 0
    try:
        futures = {
            executor.submit(detect_one, url_key, psm): (url_key, psm)
            for url_key in normalized_urls
            for psm in (6, 3, 11)
        }
        for future in as_completed(
            futures,
            timeout=REPAIR_OCR_TIMEOUT_SECONDS,
        ):
            try:
                url_key, detected = future.result()
            except Exception:
                continue
            completed_count += 1
            if not detected:
                continue
            with REPAIR_STANDARD_LOCK:
                REPAIR_STANDARD_CACHE[url_key] = detected
                _save_repair_standard_cache()
            return detected
    except FutureTimeoutError:
        pass
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False)
    if futures and completed_count == len(futures):
        with REPAIR_STANDARD_LOCK:
            for url_key in normalized_urls:
                REPAIR_STANDARD_CACHE[url_key] = "none"
            _save_repair_standard_cache()
    return ""


def _repair_requirement_remark(base):
    detected = _detect_repair_requirement_from_images(
        base.get("outerSkuDetailUrls") or []
    )
    if detected == "original":
        remark = "铂慧拆，率盛原厂配件，不影响厂保"
    elif detected == "original_official":
        remark = "铂慧拆，率盛原厂配件，不影响厂保，官方可查"
    elif detected == "non_original":
        remark = "铂慧拆，率盛非原厂配件，影响厂保"
    else:
        text = _clean_log_message(base.get("repairRequirement"))
        if "非原厂" in text or "非厂家部件" in text:
            remark = "铂慧拆，率盛非原厂配件，影响厂保"
        elif "原厂" in text or "厂家标准" in text:
            remark = "铂慧拆，率盛原厂配件，不影响厂保"
        else:
            return ""
    return remark


def build_service_bill_log_messages(base):
    messages = []
    customer_name = _clean_log_message(base.get("customerName"))
    customer_phone = _clean_log_message(base.get("customerPhone"))
    customer_parts = []
    if customer_name:
        customer_parts.append("客户姓名：" + customer_name)
    if customer_phone:
        customer_parts.append("客户电话：" + customer_phone)
    if customer_parts:
        messages.append("，".join(customer_parts))
    express_no = _clean_log_message(base.get("expressNo"))
    performing = _clean_log_message(base.get("performingOrderNo"))
    main_order_no = _clean_log_message(base.get("mainGoodsOrderNo"))
    order_parts = []
    if performing:
        order_parts.append("履约单号：" + performing)
    if express_no:
        order_parts.append("快递单号：" + express_no)
    if main_order_no:
        order_parts.append("主商品订单号：" + main_order_no)
    if order_parts:
        messages.append("，".join(order_parts))
    customer_address = _clean_log_message(base.get("customerReceiveAddress"))
    if customer_address:
        messages.append("客户收货地址：" + customer_address)
    service_fee_remark = _service_fee_remark(base)
    logistics_label = _logistics_free_label(base)
    if service_fee_remark:
        fee_part = service_fee_remark
        if logistics_label:
            fee_part += "，双向免物流：" + logistics_label
        messages.append(fee_part)
    elif logistics_label:
        messages.append("双向免物流：" + logistics_label)
    custom_remark = _clean_log_message(base.get("customRemark"))
    for custom_line in custom_remark.splitlines():
        line_text = _clean_log_message(custom_line)
        if line_text:
            messages.append(line_text)
    return messages


def _service_bill_log_lock(service_bill_no):
    with SERVICE_LOG_LOCKS_GUARD:
        lock = SERVICE_LOG_LOCKS.get(service_bill_no)
        if lock is None:
            lock = threading.Lock()
            SERVICE_LOG_LOCKS[service_bill_no] = lock
        return lock


def _resolve_digital_cookie(cookie, client_id=""):
    cookie_text = str(cookie or "").strip()
    if cookie_text:
        return cookie_text
    client_config = CLIENT_CONFIGS.get(str(client_id or "")) or {}
    return str(
        client_config.get("cookie")
        or DIGITAL_CONFIG.get("cookie")
        or ""
    ).strip()


def _baozang_order_no(base):
    row = base.get("row") or {}
    detail = base.get("detail") or {}
    commit = detail.get("repairCommitInfoDto") or {}
    return str(
        row.get("orderNo")
        or find_key(commit, "orderNo")
        or base.get("orderNo")
        or base.get("mainGoodsOrderNo")
        or ""
    ).strip()


def _baozang_service_order_no(base):
    detail = base.get("detail") or {}
    commit = detail.get("repairCommitInfoDto") or {}
    return str(
        base.get("serviceOrderNo")
        or commit.get("serviceOrderNo")
        or ""
    ).strip()


def _baozang_tag_error(response):
    if not isinstance(response, dict):
        return "宝藏备注接口返回格式异常"
    return str(
        response.get("showMsg")
        or response.get("message")
        or response.get("msg")
        or response.get("error")
        or "宝藏备注写入失败"
    )


def _baozang_existing_tags(order_no, cookie, user_id, app_code):
    response = call_jd(
        "/serviceOrder/queryOrderTag",
        {"orderNo": order_no},
        cookie,
        user_id,
        app_code,
    )
    if not isinstance(response, dict) or not response.get("success"):
        return set()
    values = response.get("values")
    if not isinstance(values, list):
        values = response.get("data") if isinstance(response.get("data"), list) else []
    result = set()
    for item in values:
        if not isinstance(item, dict):
            continue
        text = str(
            item.get("tagInfo")
            or item.get("tagMessage")
            or item.get("remark")
            or item.get("content")
            or ""
        ).strip()
        if text:
            result.add(text[:200])
    return result


def _add_baozang_tag(
    order_no,
    service_order_no,
    message,
    cookie,
    user_id,
    app_code,
):
    payload = {
        "orderNo": order_no,
        "serviceOrderNo": service_order_no,
        "tagType": "FACILITATOR_REPAIR_PROCESS",
        "tagInfo": str(message or "").strip()[:200],
        "whetherShow": "1",
        "tagPromiseDate": "",
        "tagContactCustomerState": "0",
        "tagImages": [],
        "tagImage": [],
    }
    response = call_jd(
        "/serviceOrder/serviceOrderTag",
        payload,
        cookie,
        user_id,
        app_code,
    )
    success = bool(response) and (
        response.get("success") is True
        or response.get("code") in (1, 200)
    )
    sys.stdout.write(
        "bridge: baozang tag add order=%r service=%r message=%r success=%s result=%s\n"
        % (
            order_no,
            service_order_no,
            str(message or "")[:80],
            success,
            json.dumps(response or {}, ensure_ascii=False)[:1000],
        )
    )
    sys.stdout.flush()
    return {
        "success": success,
        "error": None if success else _baozang_tag_error(response),
        "response": response,
    }


def _add_baozang_tag_with_retry(
    order_no,
    service_order_no,
    message,
    cookie,
    user_id,
    app_code,
    client_id="",
):
    fingerprint = hashlib.sha256(
        (
            str(client_id or "")
            + "\n"
            + str(cookie or "")
            + "\n"
            + str(order_no or "")
        ).encode("utf-8")
    ).hexdigest()[:12]
    with BAOZANG_REMARK_GUARD:
        lock = BAOZANG_REMARK_LOCKS.get(fingerprint)
        if lock is None:
            lock = threading.Lock()
            BAOZANG_REMARK_LOCKS[fingerprint] = lock
    last = None
    for attempt in range(1, SERVICE_LOG_MAX_ATTEMPTS + 1):
        with lock:
            with BAOZANG_REMARK_GUARD:
                last_write_at = BAOZANG_REMARK_LAST_WRITE.get(fingerprint, 0.0)
            wait_seconds = BAOZANG_REMARK_INTERVAL_SECONDS - (
                time.monotonic() - last_write_at
            )
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            last = _add_baozang_tag(
                order_no,
                service_order_no,
                message,
                cookie,
                user_id,
                app_code,
            )
            with BAOZANG_REMARK_GUARD:
                BAOZANG_REMARK_LAST_WRITE[fingerprint] = time.monotonic()
        if last["success"]:
            last["attempts"] = attempt
            return last
        error_text = str(last.get("error") or "")
        if "打标处理中" in error_text or "请勿重复请求" in error_text:
            time.sleep(3)
            existing = _baozang_existing_tags(
                order_no,
                cookie,
                user_id,
                app_code,
            )
            if str(message or "").strip()[:200] in existing:
                return {
                    "success": True,
                    "skipped": True,
                    "error": None,
                    "attempts": attempt,
                }
        if any(marker in error_text for marker in ("登录", "权限", "参数")):
            break
        if attempt < SERVICE_LOG_MAX_ATTEMPTS:
            time.sleep(SERVICE_LOG_RETRY_DELAYS[min(attempt - 1, len(SERVICE_LOG_RETRY_DELAYS) - 1)])
    last = last or {"success": False, "error": "宝藏备注写入失败"}
    last["attempts"] = min(SERVICE_LOG_MAX_ATTEMPTS, attempt)
    return last


def _baozang_order_lock(order_no):
    key = str(order_no or "").strip()
    with BAOZANG_REMARK_GUARD:
        lock = BAOZANG_ORDER_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            BAOZANG_ORDER_LOCKS[key] = lock
        return lock


def write_baozang_order_tags_for_base(
    base,
    cookie,
    user_id="",
    app_code="",
    client_id="",
):
    order_no = _baozang_order_no(base)
    lock = _baozang_order_lock(order_no)
    with lock:
        return _write_baozang_order_tags_for_base_unlocked(
            base,
            cookie,
            user_id,
            app_code,
            client_id,
        )


def _write_baozang_order_tags_for_base_unlocked(
    base,
    cookie,
    user_id="",
    app_code="",
    client_id="",
):
    order_no = _baozang_order_no(base)
    service_order_no = _baozang_service_order_no(base)
    if not order_no:
        return {"success": False, "error": "缺少宝藏订单号"}
    cookie = _resolve_digital_cookie(cookie, client_id)
    if not cookie:
        return {"success": False, "error": "未配置宝藏 Cookie"}
    user_id = str(user_id or "").strip() or extract_cookie_value(cookie, "pin")
    app_code = str(app_code or "").strip() or extract_cookie_value(cookie, "systemCode")
    messages = [
        str(message or "").strip()[:200]
        for message in build_service_bill_log_messages(base)
        if str(message or "").strip()
    ]
    if not messages:
        return {"success": False, "error": "没有可逐条写入的留言内容"}

    existing = _baozang_existing_tags(
        order_no,
        cookie,
        user_id,
        app_code,
    )
    results = []
    added = 0
    skipped = 0
    first_error = ""
    for message in messages:
        if message in existing:
            skipped += 1
            results.append(
                {"message": message, "success": True, "skipped": True}
            )
            continue
        response = _add_baozang_tag_with_retry(
            order_no,
            service_order_no,
            message,
            cookie,
            user_id,
            app_code,
            client_id,
        )
        if response.get("success"):
            if response.get("skipped"):
                skipped += 1
            else:
                added += 1
            existing.add(message)
        elif not first_error:
            first_error = str(response.get("error") or "宝藏备注写入失败")
        results.append(
            {
                "message": message,
                "success": bool(response.get("success")),
                "skipped": False,
                "error": response.get("error"),
                "attempts": response.get("attempts"),
            }
        )
    success = all(item.get("success") for item in results)
    summary = "已通过宝藏逐条添加备注 %d 条" % added
    if skipped:
        summary += "，跳过 %d 条重复内容" % skipped
    return {
        "success": success,
        "message": summary,
        "error": first_error or (None if success else "宝藏备注写入失败"),
        "added": added,
        "skipped": skipped,
        "results": results,
    }


def write_service_bill_logs_for_base(base, jdl_token, jdl_cookie="", client_id=""):
    service_bill_no = str(base.get("serviceBillNo") or "").strip()
    with _service_bill_log_lock(service_bill_no):
        return _write_service_bill_logs_for_base(
            base,
            jdl_token,
            jdl_cookie,
            client_id,
        )


def start_service_bill_log_writes_background(
    base,
    jdl_token,
    jdl_cookie="",
    client_id="",
    digital_cookie="",
    user_id="",
    app_code="",
):
    service_bill_no = str(base.get("serviceBillNo") or "").strip()
    normalized_client_id = str(client_id or "")
    now = time.time()
    with SERVICE_LOG_TASKS_GUARD:
        for existing in SERVICE_LOG_TASKS.values():
            if (
                existing.get("state") == "running"
                and str(existing.get("clientId") or "") == normalized_client_id
                and str(existing.get("serviceBillNo") or "") == service_bill_no
            ):
                return existing.get("taskId")

    task_id = "log-" + secrets.token_urlsafe(12)
    task_token, task_cookie = _resolve_service_credentials(
        jdl_token,
        jdl_cookie,
        client_id,
    )
    resolved_digital_cookie = _resolve_digital_cookie(digital_cookie, client_id)
    task_credential = resolved_digital_cookie or (
        str(task_token or "") + "\n" + str(task_cookie or "")
    )
    with SERVICE_LOG_TASKS_GUARD:
        expired = [
            key
            for key, task in SERVICE_LOG_TASKS.items()
            if now - float(task.get("createdAtEpoch") or now)
            > SERVICE_LOG_TASK_TTL_SECONDS
        ]
        for key in expired:
            SERVICE_LOG_TASKS.pop(key, None)
        SERVICE_LOG_TASKS[task_id] = {
            "taskId": task_id,
            "state": "running",
            "serviceBillNo": service_bill_no,
            "createdAt": datetime.datetime.now().isoformat(),
            "createdAtEpoch": now,
            "clientId": str(client_id or ""),
            "credentialFingerprint": hashlib.sha256(
                str(task_credential or "").encode("utf-8")
            ).hexdigest()[:12],
            "result": None,
        }

    def worker():
        try:
            if resolved_digital_cookie:
                result = write_baozang_order_tags_for_base(
                    base,
                    resolved_digital_cookie,
                    user_id,
                    app_code,
                    client_id,
                )
            else:
                result = write_service_bill_logs_for_base(
                    base,
                    jdl_token,
                    jdl_cookie,
                    client_id,
                )
            public_result = {
                "success": bool(result.get("success")),
                "message": result.get("message") or "",
                "error": result.get("error"),
                "added": int(result.get("added") or 0),
                "skipped": int(result.get("skipped") or 0),
            }
        except Exception as error:
            public_result = {
                "success": False,
                "message": "",
                "error": str(error) or "后台写入留言异常",
                "added": 0,
                "skipped": 0,
            }
            sys.stdout.write(
                "bridge: background service log write failed %r\n" % (error,)
            )
            sys.stdout.flush()
        with SERVICE_LOG_TASKS_GUARD:
            SERVICE_LOG_TASKS[task_id] = {
                "taskId": task_id,
                "state": "completed" if public_result["success"] else "failed",
                "serviceBillNo": service_bill_no,
                "createdAt": SERVICE_LOG_TASKS.get(task_id, {}).get("createdAt")
                or datetime.datetime.now().isoformat(),
                "createdAtEpoch": now,
                "clientId": SERVICE_LOG_TASKS.get(task_id, {}).get("clientId")
                or str(client_id or ""),
                "credentialFingerprint": SERVICE_LOG_TASKS.get(task_id, {}).get(
                    "credentialFingerprint", ""
                ),
                "finishedAt": datetime.datetime.now().isoformat(),
                "result": public_result,
            }

    threading.Thread(target=worker, daemon=True).start()
    return task_id


def get_service_log_task(task_id):
    task_id = str(task_id or "").strip()
    if not task_id:
        return None
    now = time.time()
    with SERVICE_LOG_TASKS_GUARD:
        task = SERVICE_LOG_TASKS.get(task_id)
        if not task:
            return None
        if now - float(task.get("createdAtEpoch") or now) > SERVICE_LOG_TASK_TTL_SECONDS:
            SERVICE_LOG_TASKS.pop(task_id, None)
            return None
        return dict(task)


def get_recent_service_log_tasks(limit=20):
    try:
        limit = max(1, min(int(limit), 100))
    except Exception:
        limit = 20
    with SERVICE_LOG_TASKS_GUARD:
        tasks = sorted(
            SERVICE_LOG_TASKS.values(),
            key=lambda item: float(item.get("createdAtEpoch") or 0),
            reverse=True,
        )
        return [dict(task) for task in tasks[:limit]]


def _write_service_bill_logs_for_base(base, jdl_token, jdl_cookie="", client_id=""):
    service_bill_no = str(base.get("serviceBillNo") or "").strip()
    messages = build_service_bill_log_messages(base)
    if not service_bill_no:
        return {"success": False, "error": "缺少展翅服务单号"}
    if not messages:
        return {"success": False, "error": "没有可逐条写入的留言内容"}

    token, cookie = _resolve_service_credentials(jdl_token, jdl_cookie, client_id)
    existing_messages = set()
    try:
        list_response = call_jd_service(
            "/mcs/log/list",
            {
                "serviceBillNo": service_bill_no,
                "logType": 2,
                "pageIndex": 1,
                "pageSize": 100,
            },
            token,
            cookie,
            8,
        )
        if list_response.get("success") and isinstance(list_response.get("data"), list):
            for item in list_response["data"]:
                if (
                    isinstance(item, dict)
                    and item.get("logType") == 2
                    and item.get("logMessage")
                ):
                    message_text = str(item["logMessage"]).strip()
                    existing_messages.add(message_text)
                    WRITTEN_SERVICE_LOG_MESSAGES.add(
                        service_bill_no + "|" + message_text
                    )
    except Exception:
        pass

    results = []
    added = 0
    skipped = 0
    first_error = ""
    for index, message in enumerate(messages):
        written_key = service_bill_no + "|" + message
        if message in existing_messages or written_key in WRITTEN_SERVICE_LOG_MESSAGES:
            skipped += 1
            results.append(
                {"message": message, "success": True, "skipped": True}
            )
            continue
        response = add_service_bill_log_with_retry(
            service_bill_no,
            message,
            jdl_token,
            jdl_cookie,
            client_id,
        )
        ok = bool(response) and response.get("success") is True
        error = (
            response.get("error")
            or response.get("msg")
            or response.get("message")
            or (None if ok else "添加留言失败")
        )
        if ok:
            added += 1
            WRITTEN_SERVICE_LOG_MESSAGES.add(written_key)
        elif not first_error:
            first_error = str(error or "添加留言失败")
        results.append(
            {
                "message": message,
                "success": ok,
                "skipped": False,
                "error": error,
            }
        )
        if not ok and _service_log_identity_error(response):
            for remaining_message in messages[index + 1 :]:
                results.append(
                    {
                        "message": remaining_message,
                        "success": False,
                        "skipped": False,
                        "error": str(error or "账号权限校验失败"),
                        "aborted": True,
                    }
                )
            break

    success = all(item.get("success") for item in results)
    summary = "已逐条写入 %d 条展翅服务单留言" % added
    if skipped:
        summary += "，跳过 %d 条重复内容" % skipped
    return {
        "success": success,
        "message": summary,
        "error": first_error or (None if success else "添加留言失败"),
        "added": added,
        "skipped": skipped,
        "results": results,
    }


def _serviceplus_error(response):
    if not isinstance(response, dict):
        return "展翅接口返回格式异常"
    for key in ("message", "msg", "showMsg", "error", "errMsg"):
        value = response.get(key)
        if value not in (None, "", "成功"):
            return str(value)
    code = response.get("code")
    if code not in (None, 0, 1, 200, "0", "1", "200", "SUCCESS"):
        return "展翅接口返回错误码 %s" % code
    return "展翅接口操作失败"


def _serviceplus_success(response):
    if not isinstance(response, dict):
        return False
    if response.get("success") is True:
        return True
    if response.get("success") is False:
        return False
    code = response.get("code")
    return code in (1, 200, "1", "200", "SUCCESS")


def _serviceplus_data(response):
    if not isinstance(response, dict):
        return {}
    for key in ("value", "data", "result"):
        value = response.get(key)
        if isinstance(value, dict):
            return value
    return {}


def call_serviceplus(cookie, path, payload=None, timeout=30):
    cookie = str(cookie or "").replace("\r", "").replace("\n", "").strip()
    if not cookie:
        return {"success": False, "error": "未配置展翅 Cookie"}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "identity",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": cookie,
        "login-type": "1",
        "Origin": SERVICEPLUS_BASE,
        "Referer": SERVICEPLUS_BASE + "/checkRepairBill/list",
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
    }
    request = urllib.request.Request(
        SERVICEPLUS_BASE + path,
        data=json.dumps(payload or {}, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = decode_body(response.read(), response.headers)
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {
                "success": False,
                "error": "展翅返回格式异常",
            }
    except urllib.error.HTTPError as error:
        body = decode_body(error.read(), error.headers)
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                parsed.setdefault("httpStatus", error.code)
                return parsed
        except Exception:
            pass
        return {"success": False, "error": "HTTP %s: %s" % (error.code, body[:300])}
    except Exception as error:
        return {"success": False, "error": str(error)}


def _decimal_value(value):
    if value is None or value == "":
        return Decimal("0")
    text = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return Decimal("0")
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return Decimal("0")


def _money(value):
    return str(_decimal_value(value).quantize(Decimal("0.01")))


def _normalize_wing_type(value):
    text = str(value or "").strip().upper()
    if "直赔" in text or "DIRECT" in text:
        return "direct"
    if "换新" in text or "RENEW" in text or "CHANGE_NEW" in text:
        return "replace"
    return ""


def _option_value(options, keywords):
    if not isinstance(options, list):
        return None
    lowered = [str(keyword).lower() for keyword in keywords]
    for option in options:
        if not isinstance(option, dict):
            continue
        text = " ".join(
            str(option.get(key) or "")
            for key in ("label", "name", "title", "text", "value", "code")
        ).lower()
        if any(keyword in text for keyword in lowered):
            return option.get("value", option.get("code", option.get("name")))
    return None


def _find_url(value):
    if isinstance(value, dict):
        for key in ("imageUrl", "picUrl", "fileUrl", "url", "path", "uploadUrl"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for nested in value.values():
            candidate = _find_url(nested)
            if candidate:
                return candidate
    elif isinstance(value, list):
        for nested in value:
            candidate = _find_url(nested)
            if candidate:
                return candidate
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith("http://") or text.startswith("https://") or text.startswith("/"):
            return text
    return ""


def _upload_serviceplus_image(cookie, filename, content):
    cookie = str(cookie or "").replace("\r", "").replace("\n", "").strip()
    if not cookie:
        return {"success": False, "error": "未配置展翅 Cookie"}
    boundary = "----SCRP" + uuid.uuid4().hex
    safe_name = os.path.basename(filename or "已完结.png").replace('"', "")
    content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    body = b"".join(
        [
            ("--%s\r\n" % boundary).encode("utf-8"),
            (
                'Content-Disposition: form-data; name="file"; filename="%s"\r\n'
                % safe_name
            ).encode("utf-8"),
            ("Content-Type: %s\r\n\r\n" % content_type).encode("utf-8"),
            content,
            ("\r\n--%s--\r\n" % boundary).encode("utf-8"),
        ]
    )
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "identity",
        "Content-Type": "multipart/form-data; boundary=" + boundary,
        "Cookie": cookie,
        "login-type": "1",
        "Origin": SERVICEPLUS_BASE,
        "Referer": SERVICEPLUS_BASE + "/checkRepairBill/list",
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
    }
    request = urllib.request.Request(
        SERVICEPLUS_BASE + "/mcs/image/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            text = decode_body(response.read(), response.headers)
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {
                "success": False,
                "error": "上传接口返回格式异常",
            }
    except urllib.error.HTTPError as error:
        text = decode_body(error.read(), error.headers)
        return {"success": False, "error": "HTTP %s: %s" % (error.code, text[:300])}
    except Exception as error:
        return {"success": False, "error": str(error)}


def _save_completion_image(
    cookie,
    service_bill_no,
    maintenance_no,
    image_type,
    filename,
    image_url,
):
    payload = {
        "businessNo": maintenance_no,
        "serviceBillNo": service_bill_no,
        "maintenanceNo": maintenance_no,
        "imageType": image_type,
        "uploadLink": image_type,
        "picType": image_type,
        "imageUrl": image_url,
        "picUrl": image_url,
        "fileUrl": image_url,
        "imageName": filename,
        "picName": filename,
    }
    return call_serviceplus(cookie, "/mcs/receive/saveImage", payload, timeout=30)


def _extract_no_old_part_reason(detail):
    commit = detail.get("repairCommitInfoDto") or {}
    receive = detail.get("receiveMaintainOrderInfoDto") or {}
    candidates = [
        find_key(commit, "noOldPartReason"),
        find_key(commit, "noOldPartReasonName"),
        find_key(receive, "noOldPartReason"),
        find_key(receive, "noOldPartReasonName"),
        find_key(detail, "noOldPartReason"),
        find_key(detail, "noOldPartReasonName"),
    ]
    for value in candidates:
        if value not in (None, ""):
            text = str(value).strip()
            return NO_OLD_PART_REASON_NAMES.get(text, text)
    return ""


def _is_no_return_reason(reason):
    text = str(reason or "").strip()
    return "无需返件" in text or "无需邮寄" in text


def _extract_logistics_fee(detail):
    value = find_key(detail, "expressPrice")
    if value not in (None, ""):
        return _decimal_value(value)
    express_list = find_key(detail, "expressInfoDtoList")
    if isinstance(express_list, list):
        total = Decimal("0")
        for item in express_list:
            if isinstance(item, dict):
                total += _decimal_value(item.get("expressPrice"))
        if total > 0:
            return total
    return Decimal("0")


def close_service_order(
    performing_order_no,
    wing_type,
    detection_fee,
    other_fee,
    direct_compensation,
    new_machine_price,
    logistics_fee,
    image_base64,
    image_name,
    cookie,
    cookie2,
    user_id,
    app_code,
    shop_code,
    jdl_token,
    jdl_cookie,
    client_id,
    service_bill_no_override="",
):
    performing_order_no = str(performing_order_no or "").strip()
    if not performing_order_no:
        return {"ok": False, "error": "履约单号不能为空"}
    mode = _normalize_wing_type(wing_type)
    if not mode:
        return {"ok": False, "error": "换新类型无法识别：%s" % wing_type}

    base = query_repair(
        performing_order_no,
        cookie,
        user_id,
        app_code,
        shop_code,
        jdl_token,
        jdl_cookie,
        client_id,
    )
    if not base.get("ok"):
        return {
            "ok": False,
            "error": base.get("error") or "宝藏查询失败",
            "performingOrderNo": performing_order_no,
        }
    if not base.get("found"):
        return {
            "ok": True,
            "skipped": True,
            "error": "宝藏未查询到履约单",
            "performingOrderNo": performing_order_no,
        }

    detail = base.get("detail") or {}
    commit = detail.get("repairCommitInfoDto") or {}
    service_state = str(
        find_key(commit, "serviceState")
        or find_key(detail, "serviceState")
        or base.get("serviceState")
        or ""
    ).strip()
    service_state_name = SERVICE_ORDER_STATE_NAMES.get(service_state, service_state)
    if service_state != "SERVICE_ORDER_END" and service_state_name != "服务单结单":
        return {
            "ok": True,
            "skipped": True,
            "error": "宝藏服务单状态为“%s”，不是“服务单结单”"
            % (service_state_name or "未知"),
            "performingOrderNo": performing_order_no,
            "serviceState": service_state,
            "serviceStateName": service_state_name,
        }

    no_old_part_reason = _extract_no_old_part_reason(detail)
    if _is_no_return_reason(no_old_part_reason):
        return {
            "ok": True,
            "skipped": True,
            "error": "无旧件原因为“%s”" % no_old_part_reason,
            "performingOrderNo": performing_order_no,
            "serviceState": service_state,
            "serviceStateName": service_state_name,
            "noOldPartReason": no_old_part_reason,
        }

    service_bill_no = str(
        service_bill_no_override
        or base.get("serviceBillNo")
        or find_key(commit, "serviceBillNo")
        or find_key(detail, "serviceBillNo")
        or ""
    ).strip()
    if not service_bill_no:
        return {
            "ok": False,
            "error": "未获取到展翅服务单号",
            "performingOrderNo": performing_order_no,
            "serviceState": service_state,
            "serviceStateName": service_state_name,
            "noOldPartReason": no_old_part_reason,
        }

    token, resolved_jdl_cookie = _resolve_service_credentials(
        jdl_token,
        jdl_cookie,
        client_id,
    )
    del token
    service_cookie = str(resolved_jdl_cookie or jdl_cookie or "").strip()
    if not service_cookie:
        return {
            "ok": False,
            "error": "未配置展翅 Cookie",
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
        }

    detail_response = call_serviceplus(
        service_cookie,
        "/mcs/maintenance/queryRepairInfo",
        {"serviceBillNo": service_bill_no, "needEdit": True},
        timeout=30,
    )
    repair = _serviceplus_data(detail_response)
    if not _serviceplus_success(detail_response) or not repair:
        return {
            "ok": False,
            "error": "展翅检修单查询失败：" + _serviceplus_error(detail_response),
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
            "serviceState": service_state,
            "serviceStateName": service_state_name,
            "noOldPartReason": no_old_part_reason,
        }

    maintenance_status = int(
        _decimal_value(
            repair.get("maintenanceStatus")
            or find_key(repair, "maintenanceStatus")
        )
    )
    if maintenance_status in (60, 61, 62, 63):
        return {
            "ok": True,
            "skipped": True,
            "error": "展翅检修单已处于完结状态",
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
            "serviceState": service_state,
            "serviceStateName": service_state_name,
            "noOldPartReason": no_old_part_reason,
        }

    maintenance_id = repair.get("id") or find_key(repair, "maintenanceId")
    maintenance_no = repair.get("maintenanceNo") or find_key(repair, "maintenanceNo")
    service_no = repair.get("serviceNo") or service_bill_no
    sys_version = repair.get("sysVersion") or repair.get("systemVersion")
    if maintenance_id in (None, "") or not maintenance_no or not sys_version:
        return {
            "ok": False,
            "error": "展翅检修单缺少 id、maintenanceNo 或 sysVersion",
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
        }

    if not str(logistics_fee or "").strip():
        logistics_fee = _extract_logistics_fee(detail)
    merchant_fee = _decimal_value(detection_fee) + _decimal_value(other_fee)
    refund_fee = (
        _decimal_value(direct_compensation)
        if mode == "direct"
        else Decimal("0")
    )
    renewal_fee = (
        _decimal_value(new_machine_price)
        if mode == "replace"
        else Decimal("0")
    )
    quote_bill = {
        "factoryServiceFeeCode": None,
        "factoryServiceFee": "0.00",
        "customerServiceFee": "0.00",
        "merchantServiceFee": _money(merchant_fee),
        "merchantServiceFeeCode": None,
        "logisticsFee": _money(logistics_fee),
        "refundFee": _money(refund_fee),
        "renewalFee": _money(renewal_fee),
    }
    quote_payload = {
        "maintenanceId": maintenance_id,
        "sysVersion": sys_version,
        "serviceBillNo": service_no,
        "materialAddRequests": [],
        "quoteBillAddRequest": quote_bill,
    }

    quote_success = maintenance_status in (23, 41, 42)
    if not quote_success:
        check_response = call_serviceplus(
            service_cookie,
            "/mcs/maintenanceQuotation/checkBeforeAdd",
            quote_payload,
            timeout=30,
        )
        if _serviceplus_success(check_response) and check_response.get("data") is False:
            return {
                "ok": False,
                "error": "展翅报价前校验未通过：" + _serviceplus_error(check_response),
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
            }
        quote_response = call_serviceplus(
            service_cookie,
            "/mcs/maintenanceQuotation/add",
            quote_payload,
            timeout=45,
        )
        if not _serviceplus_success(quote_response):
            return {
                "ok": False,
                "error": "展翅报价失败：" + _serviceplus_error(quote_response),
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
                "quoteSuccess": False,
            }
        quote_success = True

    refreshed_response = call_serviceplus(
        service_cookie,
        "/mcs/maintenance/queryRepairInfo",
        {"serviceBillNo": service_bill_no, "needEdit": True},
        timeout=30,
    )
    refreshed = _serviceplus_data(refreshed_response)
    if not _serviceplus_success(refreshed_response) or not refreshed:
        return {
            "ok": False,
            "error": "报价后刷新展翅检修单失败：" + _serviceplus_error(refreshed_response),
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
            "quoteSuccess": quote_success,
        }

    refreshed_status = int(
        _decimal_value(
            refreshed.get("maintenanceStatus")
            or find_key(refreshed, "maintenanceStatus")
        )
    )
    repair_success = refreshed_status in (41, 42)
    if not repair_success:
        repair_payload = dict(refreshed)
        repair_payload["id"] = refreshed.get("id") or maintenance_id
        repair_payload["sysVersion"] = (
            refreshed.get("sysVersion")
            or refreshed.get("systemVersion")
            or sys_version
        )
        repair_payload["serviceNo"] = refreshed.get("serviceNo") or service_no
        repair_payload["operateType"] = 2
        repair_payload["detectResult"] = 2 if mode == "direct" else 1
        detect_type = _option_value(
            refreshed.get("detectTypeOperation"),
            ("退货换新", "退换货", "退货", "换新"),
        )
        if detect_type not in (None, ""):
            repair_payload["detectType"] = detect_type

        merchant_params = []
        merchant_repairs = refreshed.get("merchantRepairInfos")
        if isinstance(merchant_repairs, list):
            for item in merchant_repairs:
                if not isinstance(item, dict):
                    continue
                current = dict(item)
                current["partsCount"] = 1
                merchant_params.append(current)
        if merchant_params:
            repair_payload["merchantRepairInfoParams"] = merchant_params

        repair_response = call_serviceplus(
            service_cookie,
            "/mcs/maintenance/updateRepairInfo",
            repair_payload,
            timeout=45,
        )
        if not _serviceplus_success(repair_response):
            return {
                "ok": False,
                "error": "展翅维修完成失败：" + _serviceplus_error(repair_response),
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
                "quoteSuccess": quote_success,
                "repairSuccess": False,
            }
        repair_success = True

    image_upload_success = False
    image_save_success = False
    if str(image_base64 or "").strip():
        try:
            encoded = str(image_base64).strip()
            if "," in encoded and encoded.lower().startswith("data:"):
                encoded = encoded.split(",", 1)[1]
            image_bytes = base64.b64decode(encoded, validate=True)
        except Exception as error:
            return {
                "ok": False,
                "error": "已完结图片解析失败：" + str(error),
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
                "quoteSuccess": quote_success,
                "repairSuccess": repair_success,
            }
        upload_response = _upload_serviceplus_image(
            service_cookie,
            image_name or "已完结.png",
            image_bytes,
        )
        if not _serviceplus_success(upload_response):
            return {
                "ok": False,
                "error": "展翅已完结图片上传失败：" + _serviceplus_error(upload_response),
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
                "quoteSuccess": quote_success,
                "repairSuccess": repair_success,
                "imageUploadSuccess": False,
            }
        image_upload_success = True
        image_url = _find_url(upload_response)
        if not image_url:
            return {
                "ok": False,
                "error": "展翅图片上传成功但未返回图片地址",
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
                "quoteSuccess": quote_success,
                "repairSuccess": repair_success,
                "imageUploadSuccess": True,
                "imageSaveSuccess": False,
            }
        save_response = _save_completion_image(
            service_cookie,
            service_bill_no,
            str(maintenance_no),
            "RECHECK",
            image_name or "已完结.png",
            image_url,
        )
        if not _serviceplus_success(save_response):
            return {
                "ok": False,
                "error": "展翅已完结图片保存失败：" + _serviceplus_error(save_response),
                "performingOrderNo": performing_order_no,
                "serviceBillNo": service_bill_no,
                "quoteSuccess": quote_success,
                "repairSuccess": repair_success,
                "imageUploadSuccess": True,
                "imageSaveSuccess": False,
            }
        image_save_success = True

    recheck_response = call_serviceplus(
        service_cookie,
        "/mcs/maintenance/queryReCheckInfo",
        {"serviceBillNo": service_bill_no},
        timeout=30,
    )
    recheck = _serviceplus_data(recheck_response)
    if not _serviceplus_success(recheck_response) or not recheck:
        return {
            "ok": False,
            "error": "展翅复检信息查询失败：" + _serviceplus_error(recheck_response),
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
            "quoteSuccess": quote_success,
            "repairSuccess": repair_success,
            "imageUploadSuccess": image_upload_success,
            "imageSaveSuccess": image_save_success,
        }
    recheck_payload = dict(recheck)
    recheck_payload["operateType"] = 5
    recheck_payload["sysVersion"] = (
        recheck.get("sysVersion")
        or recheck.get("systemVersion")
        or refreshed.get("sysVersion")
        or sys_version
    )
    if not str(recheck_payload.get("reCheckInfo") or "").strip():
        recheck_payload["reCheckInfo"] = "复检通过"
    recheck_result = call_serviceplus(
        service_cookie,
        "/mcs/maintenance/updateRepairInfo",
        recheck_payload,
        timeout=45,
    )
    if not _serviceplus_success(recheck_result):
        return {
            "ok": False,
            "error": "展翅复检通过失败：" + _serviceplus_error(recheck_result),
            "performingOrderNo": performing_order_no,
            "serviceBillNo": service_bill_no,
            "quoteSuccess": quote_success,
            "repairSuccess": repair_success,
            "imageUploadSuccess": image_upload_success,
            "imageSaveSuccess": image_save_success,
            "recheckSuccess": False,
        }

    return {
        "ok": True,
        "skipped": False,
        "message": "展翅关单完成",
        "performingOrderNo": performing_order_no,
        "serviceBillNo": service_bill_no,
        "serviceState": service_state,
        "serviceStateName": service_state_name,
        "noOldPartReason": no_old_part_reason,
        "mode": mode,
        "quoteSuccess": quote_success,
        "repairSuccess": repair_success,
        "imageUploadSuccess": image_upload_success,
        "imageSaveSuccess": image_save_success,
        "recheckSuccess": True,
    }


def query_repair(
    express_no,
    cookie,
    user_id,
    app_code,
    shop_code,
    jdl_token,
    jdl_cookie="",
    client_id="",
    force_cookie=False,
):
    if not express_no or not str(express_no).strip():
        return {"ok": False, "error": "快递单号不能为空"}

    client_config = CLIENT_CONFIGS.get(client_id) or {}
    if force_cookie:
        cookie = str(cookie or "").strip()
        user_id = str(user_id or "").strip()
        app_code = str(app_code or "").strip()
        shop_code = str(shop_code or "").strip()
    else:
        cookie = (
            str(cookie or "").strip()
            or client_config.get("cookie", "")
            or DIGITAL_CONFIG.get("cookie", "")
        )
        user_id = (
            str(user_id or "").strip()
            or client_config.get("userId", "")
            or DIGITAL_CONFIG.get("userId", "")
        )
        app_code = (
            str(app_code or "").strip()
            or client_config.get("appCode", "")
            or DIGITAL_CONFIG.get("appCode", "")
        )
        shop_code = (
            str(shop_code or "").strip()
            or client_config.get("shopCode", "")
            or DIGITAL_CONFIG.get("shopCode", "")
        )
    if not user_id:
        user_id = extract_cookie_value(cookie, "pin")
    if not app_code:
        app_code = extract_cookie_value(cookie, "systemCode")
    if not shop_code:
        shop_code = extract_cookie_value(cookie, "shopCode")
    facilitator_code = ""
    shop_name = ""
    shops = call_jd(
        "/serviceOrder/queryBindShopInfo",
        {},
        cookie,
        user_id,
        app_code,
    )
    if shops.get("success") and shops.get("values"):
        first_shop = shops["values"][0]
        shop_code = str(first_shop.get("code") or "").strip()
        facilitator_code = str(first_shop.get("facilitatorCode") or "").strip()
        shop_name = str(
            first_shop.get("shopName")
            or first_shop.get("name")
            or ""
        ).strip()

    code_value = str(express_no).strip().upper()
    performing_style = code_value.isdigit() or (
        code_value.startswith("JD") and code_value[2:].isdigit()
    )
    if code_value.startswith("JDX") or not performing_style:
        query_fields = [
            "expressNo",
            "performingId",
            "serviceOrderNo",
            "orderId",
        ]
    else:
        query_fields = [
            "performingId",
            "serviceOrderNo",
            "orderId",
        ]
    rows = []
    all_rows = []
    list_response = None
    for field in query_fields:
        query = {field: code_value}
        if shop_code:
            query["shopCode"] = shop_code.strip()
        list_response = call_jd(
            "/serviceOrder/queryFacilitatorOrderByStateAndCode",
            {
                "pageIndex": 1,
                "pageSize": 10,
                "query": query,
            },
            cookie,
            user_id,
            app_code,
        )
        if list_response.get("success"):
            rows = list_response.get("values") or list_response.get("value") or []
            if isinstance(rows, dict):
                rows = [rows]
            all_rows.extend(rows or [])
            if any(is_pending_start_row(row) for row in (rows or [])):
                break
    if not list_response:
        return {"ok": False, "error": "查询接口未返回结果"}
    if not all_rows:
        if not list_response.get("success"):
            message = (
                list_response.get("msg")
                or list_response.get("error")
                or list_response.get("showMsg")
                or "查询失败"
            )
            return {"ok": False, "error": str(message)}
        return {"ok": True, "found": False}

    row = next(
        (item for item in all_rows if is_pending_start_row(item)),
        all_rows[0],
    )
    row_info = normalize_row(row)
    detail_payload = {
        "serviceOrderNo": row_info["serviceOrderNo"],
        "facilitatorCode": row_info["facilitatorCode"] or facilitator_code,
        "shopCode": row_info["shopCode"] or shop_code,
        "performingOrderState": row_info["serviceState"] or find_key(row, "performingOrderState"),
    }
    detail_response = call_jd(
        "/serviceOrder/serviceOrderDetail",
        detail_payload,
        cookie,
        user_id,
        app_code,
    )
    if not detail_response.get("success"):
        message = (
            detail_response.get("msg")
            or detail_response.get("error")
            or detail_response.get("showMsg")
            or "详情查询失败"
        )
        return {"ok": False, "error": str(message), "row": row}

    detail = detail_response.get("value") or {}
    commit = detail.get("repairCommitInfoDto") or {}
    receive = detail.get("receiveMaintainOrderInfoDto") or {}
    customer_info = detail.get("customerInfoDto") or {}
    express_list = find_key(receive, "expressInfoDtoList")
    express_no = row_info["expressNo"] or find_key(receive, "expressNo")
    if not express_no and isinstance(express_list, list) and express_list:
        first = express_list[0]
        express_no = first.get("expressNo") if isinstance(first, dict) else first
    if not express_no:
        express_no = str(express_no).strip().upper()
    performing_order_no = (
        find_key(commit, "performingOrderNo")
        or find_key(commit, "performingNo")
        or find_key(receive, "performingOrderNo")
        or find_key(receive, "performingNo")
        or find_key(detail, "performingOrderNo")
        or find_key(detail, "performingNo")
        or row_info["performingOrderNo"]
        or row_info["serviceOrderNo"]
    )
    merchant_order_no = (
        find_key(commit, "merchantOrderNo")
        or find_key(receive, "merchantOrderNo")
        or find_key(detail, "merchantOrderNo")
    )
    service_bill_no = (
        find_key(commit, "serviceBillNo")
        or find_key(receive, "serviceBillNo")
        or find_key(detail, "serviceBillNo")
        or row_info["serviceBillNo"]
    )
    afs_service_bill_no = (
        find_key(commit, "afsServiceBillNo")
        or find_key(receive, "afsServiceBillNo")
        or find_key(detail, "afsServiceBillNo")
        or row_info["afsServiceBillNo"]
    )
    part_barcode = query_parts_barcode(
        merchant_order_no or performing_order_no,
        jdl_token,
        jdl_cookie,
        client_id,
        service_bill_no,
        afs_service_bill_no,
    )
    if not service_bill_no:
        service_bill_no = LAST_MCS_SERVICE_NO

    return {
        "ok": True,
        "found": True,
        "performingOrderNo": performing_order_no,
        "merchantOrderNo": merchant_order_no,
        "mainGoodsOrderNo": (
            find_key(commit, "outerMainOrderNo")
            or find_key(commit, "mainGoodsOrderNo")
            or find_key(receive, "outerMainOrderNo")
            or find_key(receive, "mainGoodsOrderNo")
            or find_key(detail, "outerMainOrderNo")
            or find_key(detail, "mainGoodsOrderNo")
            or find_key(row, "outerMainOrderNo")
            or find_key(row, "mainGoodsOrderNo")
            or ""
        ),
        "serviceBillNo": service_bill_no,
        "afsServiceBillNo": afs_service_bill_no,
        "serviceOrderNo": row_info["serviceOrderNo"] or find_key(commit, "serviceOrderNo"),
        "problemDesc": find_key(commit, "problemDesc") or find_key(commit, "faultDesc") or "",
        "repairRequirement": {
            "1": "原厂",
            "2": "非原厂",
        }.get(str(find_key(commit, "performFixedStandard") or "").strip(), ""),
        "whetherWarranty": (
            find_key(commit, "whetherWarranty")
            or find_key(receive, "whetherWarranty")
            or find_key(detail, "whetherWarranty")
            or find_key(row, "whetherWarranty")
            or ""
        ),
        "outerSkuDetailUrls": (
            find_key(commit, "outerSkuDetailUrls")
            or find_key(receive, "outerSkuDetailUrls")
            or find_key(detail, "outerSkuDetailUrls")
            or find_key(row, "outerSkuDetailUrls")
            or []
        ),
        "logisticsFree": find_key(commit, "logisticalMoneyType")
        or find_key(commit, "logisticsFreeType")
        or "",
        "customerName": str((customer_info.get("customerName") or "")).strip(),
        "customerPhone": str(
            customer_info.get("customerPhone")
            or find_key(customer_info, "customerPhone")
            or ""
        ).strip(),
        "customerReceiveAddress": str((customer_info.get("customerReceiveAddress") or "")).strip(),
        "category": (
            find_key(commit, "outerMainSkuThridCategory")
            or find_key(commit, "outerMainSkuThirdCategory")
            or row_info["outerMainSkuThridCategory"]
            or row_info["outerMainSkuThirdCategory"]
        ),
        "expressNo": express_no,
        "productName": (
            find_key(commit, "outerMainSkuName")
            or find_key(commit, "outerSkuName")
            or row_info["outerMainSkuName"]
            or row_info["outerSkuName"]
        ),
        "sku": find_key(commit, "outerSku") or row_info["outerSku"],
        "brand": find_key(commit, "outerMainSkuBrand"),
        "model": find_key(commit, "mainSkuModel"),
        "performingModel": format_performing_model(commit),
        "shopName": shop_name,
        "partBarcode": part_barcode,
        "row": row,
        "detail": detail,
    }


def auto_start_and_sync(
    express_no,
    cookie,
    user_id,
    app_code,
    shop_code,
    jdl_token,
    jdl_cookie="",
    client_id="",
    custom_remark="",
    force_cookie=False,
    write_remark=True,
):
    client_config = CLIENT_CONFIGS.get(client_id) or {}
    if force_cookie:
        cookie = str(cookie or "").strip()
        user_id = str(user_id or "").strip()
        app_code = str(app_code or "").strip()
        shop_code = str(shop_code or "").strip()
    else:
        cookie = (
            str(cookie or "").strip()
            or client_config.get("cookie", "")
            or DIGITAL_CONFIG.get("cookie", "")
        )
        user_id = (
            str(user_id or "").strip()
            or client_config.get("userId", "")
            or DIGITAL_CONFIG.get("userId", "")
        )
        app_code = (
            str(app_code or "").strip()
            or client_config.get("appCode", "")
            or DIGITAL_CONFIG.get("appCode", "")
        )
        shop_code = (
            str(shop_code or "").strip()
            or client_config.get("shopCode", "")
            or DIGITAL_CONFIG.get("shopCode", "")
        )
    if not user_id:
        user_id = extract_cookie_value(cookie, "pin")
    if not app_code:
        app_code = extract_cookie_value(cookie, "systemCode")
    if not shop_code:
        shop_code = extract_cookie_value(cookie, "shopCode")
    steps = []
    base = query_repair(
        express_no,
        cookie,
        user_id,
        app_code,
        shop_code,
        jdl_token,
        jdl_cookie,
        client_id,
        force_cookie,
    )
    steps.append(
        {
            "name": "query",
            "ok": bool(base.get("ok")),
            "found": bool(base.get("found")),
            "error": base.get("error"),
        }
    )
    if not base.get("ok") or not base.get("found"):
        return {**base, "steps": steps}
    if custom_remark:
        base["customRemark"] = custom_remark

    detail = base.get("detail") or {}
    commit = detail.get("repairCommitInfoDto") or {}
    service_id = str(
        find_key(commit, "facilitatorCode") or find_key(detail, "facilitatorCode") or ""
    ).strip()
    shop_id = str(
        find_key(commit, "shopCode") or find_key(detail, "shopCode") or ""
    ).strip()
    service_order_no = str(
        base.get("serviceOrderNo")
        or find_key(commit, "serviceOrderNo")
        or find_key(detail, "serviceOrderNo")
        or ""
    ).strip()
    service_type = str(
        find_key(commit, "serviceTypeEnum")
        or find_key(detail, "serviceTypeEnum")
        or ""
    ).strip()
    service_state = str(
        find_key(commit, "serviceState")
        or find_key(detail, "serviceState")
        or ""
    ).strip()
    wait_receive_states = {
        "ZERO",
        "ONE",
        "WAIT_REPORT_INFO",
        "EXPRESS_INFO_FINISH",
        "WAIT_VISIT",
        "WAIT_ARRIVE_STORE",
        "WAIT_RECEIVE",
        "WAIT_RECEIVED",
        "TO_BE_RECEIVED",
        "RECEIVE",
    }
    terminal_states = {
        "SERVICE_ORDER_END",
        "CANCEL",
        "CUSTOMER_RECEIVE",
        "RETURN_GOODS",
        "MAINTAIN_FINISH",
        "MAINTAIN_FINISH_WAIT_VISIT",
        "MAINTAIN_FINISH_WAIT_SHORE",
        "MAINTAIN_FINISH_WAIT_PAY",
        "FINISH_PAY",
        "FAIL_PAY",
    }
    terminal_blocked = service_state in terminal_states
    already_started = (
        bool(service_state)
        and service_state not in wait_receive_states
        and not terminal_blocked
    )

    order_info = {}
    for key in (
        "storePhone",
        "engineerIndex",
        "engineerJdPin",
        "engineerName",
        "engineerPhone",
        "maintainType",
        "modifyCallCause",
        "subscribeTime",
        "subscribeTimeType",
        "returnAddress",
        "warehouseCode",
        "needReturnGoods",
    ):
        value = find_key(commit, key) or find_key(detail, key)
        if value not in (None, ""):
            order_info[key] = str(value).strip() if not isinstance(value, bool) else value

    receive = detail.get("receiveMaintainOrderInfoDto") or {}
    if not order_info.get("storePhone"):
        shop_tel = find_key(receive, "shopTel") or find_key(detail, "shopTel")
        if shop_tel not in (None, ""):
            order_info["storePhone"] = str(shop_tel).strip()
    for key in (
        "engineerIndex",
        "engineerJdPin",
        "engineerName",
        "engineerPhone",
        "maintainType",
        "modifyCallCause",
        "subscribeTime",
        "subscribeTimeType",
    ):
        if not order_info.get(key):
            value = find_key(receive, key) or find_key(detail, key)
            if value not in (None, ""):
                order_info[key] = str(value).strip()

    if not order_info.get("warehouseCode"):
        warehouse_response = call_jd(
            "/warehouse/queryByFacilitatorAndShopCode",
            {"shopCode": shop_id, "busStatus": "1"},
            cookie,
            user_id,
            app_code,
        )
        sys.stdout.write(
            "bridge: warehouse query response=%s\n"
            % json.dumps(warehouse_response, ensure_ascii=False)[:1000]
        )
        sys.stdout.flush()
        warehouse_values = warehouse_response.get("values") or []
        if warehouse_values and isinstance(warehouse_values, list):
            first_warehouse = warehouse_values[0]
            if isinstance(first_warehouse, dict):
                order_info["warehouseCode"] = str(
                    first_warehouse.get("warehouseCode") or ""
                ).strip()

    if not order_info.get("returnAddress") and order_info.get("warehouseCode"):
        warehouse_detail_response = call_jd_get(
            "/warehouse/queryByWarehouseCode/" + order_info["warehouseCode"],
            cookie,
            user_id,
            app_code,
        )
        sys.stdout.write(
            "bridge: warehouse detail response=%s\n"
            % json.dumps(warehouse_detail_response, ensure_ascii=False)[:1000]
        )
        sys.stdout.flush()
        warehouse_detail = warehouse_detail_response.get("value") or {}
        if isinstance(warehouse_detail, dict):
            address_parts = [
                warehouse_detail.get("provinceName"),
                warehouse_detail.get("cityName"),
                warehouse_detail.get("countyName"),
                warehouse_detail.get("townName"),
                warehouse_detail.get("addressDetail"),
            ]
            address_parts = [str(part).strip() for part in address_parts if part]
            if address_parts:
                order_info["returnAddress"] = "/".join(address_parts)

    if not service_order_no:
        return {
            **base,
            "steps": steps,
            "startSuccess": False,
            "error": "未获取到服务单号，无法自动开始接机",
        }

    start_response = {}
    start_success = True
    if terminal_blocked:
        start_success = False
        start_response = {
            "success": False,
            "showMsg": "京东维修中该履约单已结单，未找到待确认接机的服务单",
        }
    elif already_started:
        start_response = {"success": True, "showMsg": "该单已接机，跳过开始接机"}
    else:
        start_payload = {
            "serviceId": service_id,
            "shopId": shop_id,
            "serviceOrderNo": service_order_no,
            "serviceType": service_type,
            **order_info,
        }
        start_response = call_jd_encrypted(
            "/serviceOrder/facilitatorAcceptExpress",
            start_payload,
            cookie,
            user_id,
            app_code,
        )
        sys.stdout.write(
            "bridge: auto-start payload=%s response=%s\n"
            % (
                json.dumps(start_payload, ensure_ascii=False),
                json.dumps(start_response, ensure_ascii=False)[:1200],
            )
        )
        sys.stdout.flush()
        start_success = bool(start_response.get("success"))
        start_error_text = str(
            start_response.get("showMsg")
            or start_response.get("msg")
            or start_response.get("error")
            or ""
        )
        if "HTTP 400" in start_error_text or "HTTP 4" in start_error_text:
            start_response["encryptionRequired"] = True
            start_response["showMsg"] = "需要在京东维修页面执行自动接机命令"
        if "NotLogin" in start_error_text or "未登录" in start_error_text:
            start_response["encryptionRequired"] = True
            start_response["showMsg"] = "需要在京东维修页面执行自动接机命令"
        if not start_success and any(
            keyword in start_error_text
            for keyword in ("已接机", "已收货", "已确认接机", "重复操作", "已开始")
        ):
            start_success = True
            start_response["showMsg"] = start_error_text
    steps.append(
        {
            "name": "start",
            "ok": start_success,
            "skipped": already_started,
            "error": start_response.get("showMsg")
            or start_response.get("msg")
            or start_response.get("error"),
            "response": start_response,
        }
    )

    part_barcode = ""
    performing_order_no = base.get("performingOrderNo") or ""
    merchant_order_no = base.get("merchantOrderNo") or ""
    service_bill_no = base.get("serviceBillNo") or ""
    afs_service_bill_no = base.get("afsServiceBillNo") or ""
    barcode_attempts = 0
    max_barcode_attempts = 1
    while not part_barcode and barcode_attempts < max_barcode_attempts:
        barcode_attempts += 1
        if performing_order_no or merchant_order_no:
            part_barcode = query_parts_barcode(
                merchant_order_no or performing_order_no,
                jdl_token,
                jdl_cookie,
                client_id,
                service_bill_no,
                afs_service_bill_no,
            )
        sys.stdout.write(
            "bridge: barcode retry %d/%d found=%s partCode=%r error=%r\n"
            % (
                barcode_attempts,
                max_barcode_attempts,
                bool(part_barcode),
                part_barcode,
                LAST_BARCODE_ERROR,
            )
        )
        sys.stdout.flush()
    steps.append(
        {
            "name": "barcode",
            "ok": bool(part_barcode),
            "partBarcode": part_barcode,
            "retries": barcode_attempts,
            "error": LAST_BARCODE_ERROR,
        }
    )

    result = {**base, "steps": steps, "startSuccess": start_success}

    if write_remark:
        service_log_task_id = start_service_bill_log_writes_background(
            base,
            jdl_token,
            jdl_cookie,
            client_id,
            cookie,
            user_id,
            app_code,
        )
        service_log_result = {
            "success": True,
            "message": "已开始后台逐条写入展翅服务单留言，页面将自动显示最终结果",
            "background": True,
            "taskId": service_log_task_id,
        }
    else:
        service_log_result = {
            "success": True,
            "message": "已跳过留言写入",
            "background": False,
            "taskId": None,
        }
    result["customerRemarkResult"] = service_log_result
    result["serviceLogResult"] = service_log_result

    if start_response.get("encryptionRequired"):
        result["encryptionRequired"] = True
    if part_barcode:
        result["partBarcode"] = part_barcode
    if not start_success:
        if start_response.get("encryptionRequired"):
            result["error"] = "请在京东维修页面执行自动接机命令，再回来查询"
        else:
            result["error"] = "自动开始接机失败：" + str(
                steps[-2].get("error") or "请到京东维修页面手动操作"
            )
    return result


def remark_info_and_sync(
    express_no,
    cookie,
    user_id,
    app_code,
    shop_code,
    jdl_token,
    jdl_cookie="",
    client_id="",
    custom_remark="",
    force_cookie=False,
    background=False,
):
    base = query_repair(
        express_no,
        cookie,
        user_id,
        app_code,
        shop_code,
        jdl_token,
        jdl_cookie,
        client_id,
        force_cookie,
    )
    if not base.get("ok") or not base.get("found"):
        return base
    if custom_remark:
        base["customRemark"] = custom_remark

    result = {**base}
    if background:
        task_id = start_service_bill_log_writes_background(
            base,
            jdl_token,
            jdl_cookie,
            client_id,
            cookie,
            user_id,
            app_code,
        )
        service_log_result = {
            "success": True,
            "message": "后台留言写入任务已创建",
            "background": True,
            "taskId": task_id,
        }
    else:
        service_log_result = write_service_bill_logs_for_base(
            base,
            jdl_token,
            jdl_cookie,
            client_id,
        )
    result["customerRemarkResult"] = service_log_result
    result["serviceLogResult"] = service_log_result
    return result


def desktop_dir():
    home = os.path.expanduser("~")
    for candidate in (
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive", "桌面"),
    ):
        if os.path.isdir(candidate):
            return candidate
    return home


def export_categories_xlsx(rows, account="admin"):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "品类看板"
    headers = ["品类", "今日数量", "累计数量", "今日占比"]
    ws.append(headers)
    head_fill = PatternFill("solid", fgColor="E1251B")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    normalized_rows = []
    for item in rows or []:
        category = str(item.get("category") or "未分类")
        today_count = int(item.get("todayCount") or 0)
        total_count = int(item.get("totalCount") or item.get("count") or 0)
        normalized_rows.append([category, today_count, total_count])
    total_all = sum(row[2] for row in normalized_rows) or 1
    for category, today_count, total_count in normalized_rows:
        percent = round((total_count / total_all) * 100, 1)
        ws.append([category, today_count, total_count, percent])

    for col, width in zip("ABCD", [28, 12, 12, 12]):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    filename = "品类看板_%s_%s.xlsx" % (
        account,
        time.strftime("%Y%m%d_%H%M%S"),
    )
    path = os.path.join(desktop_dir(), filename)
    wb.save(path)
    return path


def _cleanup_print_agents():
    cutoff = time.time() - 30
    for agent_id in list(PRINT_AGENTS.keys()):
        if PRINT_AGENTS[agent_id].get("updatedAt", 0) < cutoff:
            PRINT_AGENTS.pop(agent_id, None)


def _get_latest_print_agent():
    _cleanup_print_agents()
    best = None
    for agent in PRINT_AGENTS.values():
        if not agent.get("path"):
            continue
        if best is None or agent.get("updatedAt", 0) > best.get("updatedAt", 0):
            best = agent
    return best


class BridgeHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _is_authorized(self, parsed):
        provided = str(self.headers.get("X-Api-Key") or "").strip()
        if not provided:
            query = urllib.parse.parse_qs(parsed.query)
            provided = (query.get("apiKey") or [""])[0].strip()
        return provided in API_KEYS

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        global JDL_TOKEN, JDL_COOKIE
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(200, {"ok": True, "message": "JD repair bridge is running"})
            return
        if parsed.path.startswith("/api/") and not self._is_authorized(parsed):
            self._send_json(401, {"ok": False, "error": "Unauthorized"})
            return
        if parsed.path == "/api/agreements":
            query = urllib.parse.parse_qs(parsed.query)
            account = (query.get("account") or [""])[0].strip()
            client_id = (query.get("clientId") or [""])[0].strip()
            user_name = (query.get("userName") or [""])[0].strip()
            with AGREEMENT_LOCK:
                records = list(AGREEMENTS.values())
            if account:
                records = [
                    item for item in records
                    if str(item.get("account") or "") == account
                ]
            if client_id:
                records = [
                    item for item in records
                    if str(item.get("clientId") or "") == client_id
                ]
            if user_name:
                records = [
                    item for item in records
                    if str(item.get("userName") or "") == user_name
                ]
            records.sort(
                key=lambda item: str(item.get("acceptedAt") or ""),
                reverse=True,
            )
            self._send_json(
                200,
                {
                    "ok": True,
                    "count": len(records),
                    "agreements": records,
                },
            )
            return
        if parsed.path == "/api/agreements/pdf":
            query = urllib.parse.parse_qs(parsed.query)
            record_id = (query.get("recordId") or [""])[0].strip()
            client_id = (query.get("clientId") or [""])[0].strip()
            with AGREEMENT_LOCK:
                record = AGREEMENTS.get(record_id) if record_id else None
                if record is None and client_id:
                    candidates = [
                        item for item in AGREEMENTS.values()
                        if str(item.get("clientId") or "") == client_id
                    ]
                    candidates.sort(
                        key=lambda item: str(
                            item.get("acceptedAt") or ""
                        ),
                        reverse=True,
                    )
                    record = candidates[0] if candidates else None
            if record is None:
                self._send_json(404, {"ok": False, "error": "签署记录不存在"})
                return
            try:
                pdf_name = ensure_agreement_pdf(record)
                with AGREEMENT_LOCK:
                    save_agreements()
            except Exception as error:
                self._send_json(
                    500,
                    {"ok": False, "error": "PDF生成失败：" + str(error)},
                )
                return
            pdf_path = os.path.join(AGREEMENT_PDF_DIR, pdf_name)
            if not os.path.isfile(pdf_path):
                self._send_json(404, {"ok": False, "error": "PDF文件不存在"})
                return
            with open(pdf_path, "rb") as handle:
                body = handle.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header(
                "Content-Disposition",
                'inline; filename="' + pdf_name + '"',
            )
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/print-agent/find":
            with PRINT_LOCK:
                agent = _get_latest_print_agent()
            if agent:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "found": True,
                        "path": agent.get("path", ""),
                        "agentId": agent.get("agentId", ""),
                    },
                )
            else:
                self._send_json(200, {"ok": True, "found": False})
            return
        if parsed.path == "/api/print-agent/jobs":
            query = urllib.parse.parse_qs(parsed.query)
            agent_id = (query.get("agentId") or [""])[0].strip()
            job = None
            if agent_id:
                with PRINT_LOCK:
                    queue = PRINT_JOBS.get(agent_id) or []
                    if queue:
                        job = queue.pop(0)
            self._send_json(200, {"ok": True, "job": job})
            return
        if parsed.path == "/api/print-agent/result":
            query = urllib.parse.parse_qs(parsed.query)
            job_id = (query.get("jobId") or [""])[0].strip()
            result = None
            if job_id:
                with PRINT_LOCK:
                    result = PRINT_JOB_RESULTS.get(job_id)
            self._send_json(
                200,
                {
                    "ok": True,
                    "done": bool(result),
                    "result": result,
                },
            )
            return
        if parsed.path == "/api/repair/set-digital-cookie":
            query = urllib.parse.parse_qs(parsed.query)
            data_text = (query.get("data") or [""])[0]
            try:
                payload = json.loads(data_text)
            except Exception:
                self._send_json(400, {"ok": False, "error": "data 不是合法 JSON"})
                return
            client_id = str(payload.get("clientId", "") or "").strip()
            incoming_cookie = str(payload.get("cookie", "") or "").strip()
            incoming_cookie2 = str(payload.get("cookie2", "") or "").strip()
            cookie_text = incoming_cookie
            cookie2_text = incoming_cookie2
            if not cookie_text and DIGITAL_CONFIG.get("cookie"):
                cookie_text = str(DIGITAL_CONFIG.get("cookie") or "").strip()
            if not cookie2_text and DIGITAL_CONFIG.get("cookie2"):
                cookie2_text = str(DIGITAL_CONFIG.get("cookie2") or "").strip()
            if incoming_cookie and not validate_digital_cookie(incoming_cookie):
                self._send_json(400, {"ok": False, "error": "延保 Cookie 无效，未保存"})
                return
            cookie2_warning = ""
            if incoming_cookie2 and not validate_digital_cookie(incoming_cookie2):
                cookie2_warning = "商家险 Cookie 无效，已忽略，其余配置照常保存"
                incoming_cookie2 = ""
                cookie2_text = ""
            config_updates = {
                "cookie": cookie_text,
                "cookie2": cookie2_text,
                "userId": str(payload.get("userId", "") or extract_cookie_value(cookie_text, "pin") or "").strip(),
                "appCode": str(payload.get("appCode", "") or extract_cookie_value(cookie_text, "systemCode") or "").strip(),
                "shopCode": str(payload.get("shopCode", "") or extract_cookie_value(cookie_text, "shopCode") or "").strip(),
            }
            jdl_token = str(payload.get("jdlToken", "") or "").strip()
            jdl_cookie = str(payload.get("jdlCookie", "") or "").strip()
            if jdl_token or jdl_cookie:
                apply_settings_update(
                    client_id,
                    config_updates=config_updates,
                    jdl_token=jdl_token,
                    jdl_cookie=jdl_cookie,
                )
            else:
                apply_settings_update(client_id, config_updates=config_updates)
            self._send_json(
                200,
                {
                    "ok": True,
                    "message": "OK",
                    "warning": cookie2_warning,
                },
            )
            return
        if parsed.path == "/api/repair/set-jdl-token":
            query = urllib.parse.parse_qs(parsed.query)
            data_text = (query.get("data") or [""])[0]
            try:
                payload = json.loads(data_text)
            except Exception:
                self._send_json(400, {"ok": False, "error": "data 不是合法 JSON"})
                return
            client_id = str(payload.get("clientId", "") or "").strip()
            token = str(payload.get("jdlToken", "") or "").strip()
            cookie = str(payload.get("jdlCookie", "") or "").strip()
            if token or cookie:
                apply_settings_update(
                    client_id,
                    jdl_token=token,
                    jdl_cookie=cookie,
                )
            self._send_json(
                200,
                {
                    "ok": True,
                    "message": "OK",
                    "configured": bool(
                        (CLIENT_JDL_TOKENS.get(client_id) if client_id else JDL_TOKEN)
                        or (CLIENT_JDL_COOKIES.get(client_id) if client_id else JDL_COOKIE)
                    ),
                },
            )
            return
        if parsed.path == "/api/repair/config":
            token_configured = bool(
                JDL_TOKEN
                or any(CLIENT_JDL_TOKENS.values())
                or JDL_COOKIE
                or any(CLIENT_JDL_COOKIES.values())
            )
            self._send_json(
                200,
                {
                    "ok": True,
                    "digitalConfigured": bool(DIGITAL_CONFIG.get("cookie")),
                    "jdlConfigured": token_configured,
                    "message": "京东维修/展翅登录状态",
                },
            )
            return
        if parsed.path == "/api/repair/service-log-tasks":
            query = urllib.parse.parse_qs(parsed.query)
            limit = (query.get("limit") or ["20"])[0]
            self._send_json(
                200,
                {"ok": True, "tasks": get_recent_service_log_tasks(limit)},
            )
            return
        if parsed.path == "/api/repair/service-log-status":
            query = urllib.parse.parse_qs(parsed.query)
            task_id = (query.get("taskId") or [""])[0]
            task = get_service_log_task(task_id)
            if not task:
                self._send_json(
                    404,
                    {"ok": False, "error": "留言写入任务不存在或已过期"},
                )
            else:
                self._send_json(200, task)
            return
        if parsed.path == "/api/repair/latest":
            query = urllib.parse.parse_qs(parsed.query)
            tracking = (query.get("tracking") or [""])[0].strip().upper()
            result = LATEST_RESULTS.get(tracking)
            if result:
                self._send_json(200, result)
            else:
                self._send_json(200, {"ok": True, "found": False, "tracking": tracking})
            return

        if parsed.path == "/api/print/find":
            printer_path = find_barcode_printer()
            self._send_json(
                200,
                {
                    "ok": bool(printer_path),
                    "path": printer_path,
                    "error": None if printer_path else "未在本机找到 BarPrinter.exe",
                },
            )
            return

        if parsed.path == "/api/state":
            query = urllib.parse.parse_qs(parsed.query)
            account = (query.get("account") or ["admin"])[0]
            self._send_json(
                200,
                {
                    "ok": True,
                    "account": account,
                    "state": SHARED_STATES.get(account) or {
                        "schemaVersion": 2,
                        "parcels": [],
                        "anomalies": [],
                    },
                },
            )
            return

        relative = parsed.path.lstrip("/") or "index.html"
        file_path = os.path.realpath(os.path.join(ROOT_DIR, relative))
        if not file_path.startswith(ROOT_DIR) or not os.path.isfile(file_path):
            self._send_json(404, {"ok": False, "error": "Not found"})
            return
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        with open(file_path, "rb") as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global JDL_TOKEN, JDL_COOKIE, PRINT_JOB_SEQ
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/") and not self._is_authorized(parsed):
            self._send_json(401, {"ok": False, "error": "Unauthorized"})
            return
        if parsed.path == "/api/agreements":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            account = str(payload.get("account") or "admin").strip() or "admin"
            user_name = str(payload.get("userName") or "").strip()
            version = str(payload.get("version") or "").strip()
            accepted_at = str(payload.get("acceptedAt") or "").strip()
            client_id = str(payload.get("clientId") or "").strip()
            if not user_name or not version:
                self._send_json(400, {"ok": False, "error": "缺少姓名或协议版本"})
                return
            if not accepted_at:
                accepted_at = datetime.datetime.now().isoformat(timespec="seconds")
            record_id = account + ":" + (client_id or "unknown")
            now = datetime.datetime.now().isoformat(timespec="seconds")
            record = {
                "id": record_id,
                "account": account,
                "userName": user_name,
                "version": version,
                "acceptedAt": accepted_at,
                "serverReceivedAt": now,
                "clientId": client_id,
                "machineName": str(payload.get("machineName") or "").strip(),
                "windowsUser": str(payload.get("windowsUser") or "").strip(),
                "appVersion": str(payload.get("appVersion") or "").strip(),
                "ip": str(self.client_address[0] if self.client_address else ""),
                "userAgent": str(self.headers.get("User-Agent", "")),
            }
            with AGREEMENT_LOCK:
                AGREEMENTS[record_id] = record
                save_agreements()
            try:
                ensure_agreement_pdf(record)
            except Exception as error:
                record["pdfError"] = str(error)
            with AGREEMENT_LOCK:
                AGREEMENTS[record_id] = record
                save_agreements()
            self._send_json(200, {"ok": True, "agreement": record})
            return
        if parsed.path == "/api/debug/ingest":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8", "ignore")
            except Exception:
                raw = ""
            try:
                with open(
                    os.path.join(ROOT_DIR, "captured_requests.log"),
                    "a",
                    encoding="utf-8",
                ) as handle:
                    handle.write(datetime.datetime.now().isoformat() + " " + raw + "\n")
            except Exception:
                pass
            self._send_json(200, {"ok": True})
            return
        if parsed.path == "/api/print-agent/heartbeat":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            agent_id = str(payload.get("agentId", "") or "").strip()
            if not agent_id:
                self._send_json(400, {"ok": False, "error": "缺少 agentId"})
                return
            with PRINT_LOCK:
                PRINT_AGENTS[agent_id] = {
                    "agentId": agent_id,
                    "path": str(payload.get("path", "") or "").strip(),
                    "ok": bool(payload.get("ok", True)),
                    "updatedAt": time.time(),
                }
            self._send_json(200, {"ok": True})
            return
        if parsed.path == "/api/print-agent/print":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            order_no = str(payload.get("orderNo", "") or "").strip()
            if not order_no:
                self._send_json(400, {"ok": False, "error": "缺少履约单号"})
                return
            with PRINT_LOCK:
                agent = _get_latest_print_agent()
                if not agent:
                    self._send_json(
                        200,
                        {
                            "ok": False,
                            "error": "未检测到在线打印助手，请先运行 start_print_helper_all.bat",
                        },
                    )
                    return
                PRINT_JOB_SEQ += 1
                job_id = "PJ%d%05d" % (int(time.time()), PRINT_JOB_SEQ)
                job = {
                    "jobId": job_id,
                    "orderNo": order_no,
                    "partCode": str(payload.get("partCode", "") or "").strip(),
                    "manualOnly": bool(payload.get("manualOnly")),
                    "printerName": str(payload.get("printerName", "") or "").strip(),
                    "barPrinterPath": str(
                        payload.get("barPrinterPath", "") or ""
                    ).strip()
                    or agent.get("path", ""),
                }
                PRINT_JOBS.setdefault(agent["agentId"], []).append(job)
                PRINT_JOB_RESULTS[job_id] = None
                target_agent = agent["agentId"]
            self._send_json(
                200,
                {
                    "ok": True,
                    "jobId": job_id,
                    "agentId": target_agent,
                },
            )
            return
        if parsed.path == "/api/print-agent/result":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            job_id = str(payload.get("jobId", "") or "").strip()
            if not job_id:
                self._send_json(400, {"ok": False, "error": "缺少 jobId"})
                return
            with PRINT_LOCK:
                PRINT_JOB_RESULTS[job_id] = {
                    "ok": bool(payload.get("ok")),
                    "output": str(payload.get("output", "") or ""),
                }
            self._send_json(200, {"ok": True})
            return
        if parsed.path == "/api/print":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            order_no = str(payload.get("orderNo", "") or "").strip()
            part_code = str(payload.get("partCode", "") or "").strip()
            if not order_no:
                self._send_json(400, {"ok": False, "error": "缺少履约单号"})
                return
            if os.name != "nt":
                self._send_json(
                    500,
                    {
                        "ok": False,
                        "error": "打印需在安装 BarPrinter.exe 的 Windows 本机桥接服务中执行，当前云服务器无法直接打印",
                    },
                )
                return
            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                PRINT_SCRIPT,
                "-OrderNo",
                order_no,
            ]
            if part_code:
                command += ["-PartCode", part_code]
            if payload.get("manualOnly"):
                command += ["-ManualOnly"]
            bar_printer_path = str(payload.get("barPrinterPath", "") or "").strip()
            if bar_printer_path:
                command += ["-BarPrinterPath", bar_printer_path]
            if payload.get("dryRun"):
                command += ["-DryRun"]
            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                self._send_json(504, {"ok": False, "error": "条码打印超时"})
                return
            except Exception as error:
                self._send_json(500, {"ok": False, "error": str(error)})
                return
            output = (result.stdout or "") + (result.stderr or "")
            self._send_json(
                200,
                {
                    "ok": result.returncode == 0,
                    "output": output,
                    "error": None if result.returncode == 0 else output,
                },
            )
            return

        if parsed.path == "/api/state":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            account = str(payload.get("account") or "admin").strip()
            incoming = payload.get("state") or {}
            stored = SHARED_STATES.get(account) or {
                "parcels": [],
                "anomalies": [],
            }
            if payload.get("replace"):
                cleared_at = str(
                    payload.get("clearedAt")
                    or stored.get("clearedAt")
                    or ""
                )
                incoming_parcels = _merge_state_list(
                    [],
                    incoming.get("parcels"),
                    id_key="tracking",
                    cleared_at=cleared_at,
                )
                incoming_anomalies = _merge_state_list(
                    [],
                    incoming.get("anomalies"),
                    id_key="id",
                    cleared_at=cleared_at,
                )
                merged = {
                    "schemaVersion": int(
                        incoming.get("schemaVersion")
                        or stored.get("schemaVersion")
                        or 2
                    ),
                    "parcels": incoming_parcels,
                    "anomalies": incoming_anomalies,
                    "clearedAt": payload.get("clearedAt")
                    or stored.get("clearedAt")
                    or "",
                }
            else:
                merged = merge_shared_state(stored, incoming)
                if stored.get("clearedAt"):
                    merged["clearedAt"] = stored["clearedAt"]
            SHARED_STATES[account] = merged
            save_shared_states()
            self._send_json(
                200,
                {
                    "ok": True,
                    "account": account,
                    "state": merged,
                },
            )
            return

        if parsed.path == "/api/export-categories":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            account = str(payload.get("account") or "admin").strip()
            rows = payload.get("rows") or []
            try:
                path = export_categories_xlsx(rows, account)
                self._send_json(
                    200,
                    {"ok": True, "path": path, "message": "已导出到桌面"},
                )
            except Exception as error:
                self._send_json(500, {"ok": False, "error": str(error)})
            return

        if parsed.path == "/api/repair/set-digital-cookie":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            client_id = str(payload.get("clientId", "") or "").strip()
            incoming_cookie = str(payload.get("cookie", "") or "").strip()
            incoming_cookie2 = str(payload.get("cookie2", "") or "").strip()
            cookie_text = incoming_cookie
            cookie2_text = incoming_cookie2
            if not cookie_text and DIGITAL_CONFIG.get("cookie"):
                cookie_text = str(DIGITAL_CONFIG.get("cookie") or "").strip()
            if not cookie2_text and DIGITAL_CONFIG.get("cookie2"):
                cookie2_text = str(DIGITAL_CONFIG.get("cookie2") or "").strip()
            if incoming_cookie and not validate_digital_cookie(incoming_cookie):
                self._send_json(400, {"ok": False, "error": "延保 Cookie 无效，未保存"})
                return
            cookie2_warning = ""
            if incoming_cookie2 and not validate_digital_cookie(incoming_cookie2):
                cookie2_warning = "商家险 Cookie 无效，已忽略，其余配置照常保存"
                incoming_cookie2 = ""
                cookie2_text = ""
            config_updates = {
                "cookie": cookie_text,
                "cookie2": cookie2_text,
                "userId": str(payload.get("userId", "") or extract_cookie_value(cookie_text, "pin") or "").strip(),
                "appCode": str(payload.get("appCode", "") or extract_cookie_value(cookie_text, "systemCode") or "").strip(),
                "shopCode": str(payload.get("shopCode", "") or extract_cookie_value(cookie_text, "shopCode") or "").strip(),
            }
            jdl_token = str(payload.get("jdlToken", "") or "").strip()
            jdl_cookie = str(payload.get("jdlCookie", "") or "").strip()
            if jdl_token or jdl_cookie:
                apply_settings_update(
                    client_id,
                    config_updates=config_updates,
                    jdl_token=jdl_token,
                    jdl_cookie=jdl_cookie,
                )
            else:
                apply_settings_update(client_id, config_updates=config_updates)
            self._send_json(
                200,
                {
                    "ok": True,
                    "configured": bool(
                        (CLIENT_CONFIGS.get(client_id) or {}).get("cookie")
                        if client_id
                        else DIGITAL_CONFIG["cookie"]
                    ),
                    "message": "京东维修登录信息已保存到本地桥接服务",
                    "warning": cookie2_warning,
                },
            )
            return

        if parsed.path == "/api/repair/set-jdl-token":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            client_id = str(payload.get("clientId", "") or "").strip()
            token = str(payload.get("jdlToken", "") or "").strip()
            cookie = str(payload.get("jdlCookie", "") or "").strip()
            apply_settings_update(
                client_id,
                jdl_token=token,
                jdl_cookie=cookie,
            )
            self._send_json(
                200,
                {
                    "ok": True,
                    "configured": bool(
                        (CLIENT_JDL_TOKENS.get(client_id) if client_id else JDL_TOKEN)
                        or (CLIENT_JDL_COOKIES.get(client_id) if client_id else JDL_COOKIE)
                    ),
                    "message": "京东物流 Token 已保存到本地桥接服务",
                },
            )
            return

        if parsed.path == "/api/repair/import":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8")
                content_type = self.headers.get("Content-Type", "")
                if "application/x-www-form-urlencoded" in content_type:
                    form = urllib.parse.parse_qs(raw_body)
                    payload = json.loads((form.get("data") or [""])[0])
                else:
                    payload = json.loads(raw_body)
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            tracking = str(payload.get("tracking", "")).strip().upper()
            result = payload.get("result")
            if not tracking or not isinstance(result, dict):
                self._send_json(400, {"ok": False, "error": "缺少 tracking 或 result"})
                return
            jdl_token = str(payload.get("jdlToken", "") or "").strip()
            jdl_cookie = str(payload.get("jdlCookie", "") or "").strip()
            if jdl_token or jdl_cookie:
                JDL_TOKEN = jdl_token
                JDL_COOKIE = jdl_cookie
                client_id = str(payload.get("clientId", "") or "").strip()
                if client_id:
                    CLIENT_JDL_TOKENS[client_id] = jdl_token
                    CLIENT_JDL_COOKIES[client_id] = jdl_cookie
                save_jdl_token()
            LATEST_RESULTS[tracking] = result
            self._send_json(200, {"ok": True, "tracking": tracking})
            return

        if parsed.path == "/api/repair/service-close":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            result = close_service_order(
                payload.get("performingOrderNo", ""),
                payload.get("wingType", ""),
                payload.get("detectionFee", ""),
                payload.get("otherFee", ""),
                payload.get("directCompensation", ""),
                payload.get("newMachinePrice", ""),
                payload.get("logisticsFee", ""),
                payload.get("imageBase64", ""),
                payload.get("imageName", "已完结.png"),
                payload.get("cookie", ""),
                payload.get("cookie2", ""),
                payload.get("userId", ""),
                payload.get("appCode", ""),
                payload.get("shopCode", ""),
                payload.get("jdlToken", ""),
                payload.get("jdlCookie", ""),
                payload.get("clientId", ""),
                payload.get("serviceBillNo", ""),
            )
            sys.stdout.write(
                "bridge: service-close order=%r type=%r ok=%s skipped=%s error=%r\n"
                % (
                    payload.get("performingOrderNo", ""),
                    payload.get("wingType", ""),
                    result.get("ok"),
                    result.get("skipped"),
                    result.get("error"),
                )
            )
            sys.stdout.flush()
            self._send_json(200, result)
            return

        if parsed.path == "/api/repair/part-barcode":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            merchant_order_no = payload.get("merchantOrderNo", "")
            jdl_token = payload.get("jdlToken", "")
            jdl_cookie = payload.get("jdlCookie", "")
            client_id = payload.get("clientId", "")
            part_barcode = query_parts_barcode(
                merchant_order_no,
                jdl_token,
                jdl_cookie,
                client_id,
                payload.get("serviceBillNo", ""),
                payload.get("afsServiceBillNo", ""),
            )
            sys.stdout.write(
                "bridge: part-barcode order=%r found=%s partCode=%r error=%r\n"
                % (
                    merchant_order_no,
                    bool(part_barcode),
                    part_barcode,
                    LAST_BARCODE_ERROR,
                )
            )
            sys.stdout.flush()
            self._send_json(
                200,
                {
                    "ok": True,
                    "found": bool(part_barcode),
                    "partBarcode": part_barcode,
                    "merchantOrderNo": merchant_order_no,
                    "error": LAST_BARCODE_ERROR
                    or (None if part_barcode else "未查询到备件条码"),
                },
            )
            return

        if parsed.path == "/api/repair/auto-start":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            result = auto_start_and_sync(
                payload.get("expressNo", ""),
                payload.get("cookie", ""),
                payload.get("userId", ""),
                payload.get("appCode", ""),
                payload.get("shopCode", ""),
                payload.get("jdlToken", ""),
                payload.get("jdlCookie", ""),
                payload.get("clientId", ""),
                payload.get("customRemark", ""),
                write_remark=bool(payload.get("writeRemark", True)),
            )
            cookie2 = str(
                payload.get("cookie2", "") or ""
            ).strip() or DIGITAL_CONFIG.get("cookie2", "")
            if cookie2 and (
                not result.get("ok")
                or (result.get("ok") and not result.get("found"))
                or "NotLogin" in str(result.get("error") or "")
            ):
                result = auto_start_and_sync(
                    payload.get("expressNo", ""),
                    cookie2,
                    "",
                    "",
                    "",
                    payload.get("jdlToken", ""),
                    payload.get("jdlCookie", ""),
                    payload.get("clientId", ""),
                    payload.get("customRemark", ""),
                    force_cookie=True,
                    write_remark=bool(payload.get("writeRemark", True)),
                )
                sys.stdout.write(
                    "bridge: auto-start retry cookie2 %r ok=%s found=%s error=%r\n"
                    % (
                        payload.get("expressNo", ""),
                        result.get("ok"),
                        result.get("found"),
                        result.get("error"),
                    )
                )
                sys.stdout.flush()
            self._send_json(200, result)
            return

        if parsed.path in (
            "/api/repair/remark-info",
            "/api/repair/remark-info-async",
        ):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
                return
            result = remark_info_and_sync(
                payload.get("expressNo", ""),
                payload.get("cookie", ""),
                payload.get("userId", ""),
                payload.get("appCode", ""),
                payload.get("shopCode", ""),
                payload.get("jdlToken", ""),
                payload.get("jdlCookie", ""),
                payload.get("clientId", ""),
                payload.get("customRemark", ""),
                background=parsed.path.endswith("-async"),
            )
            cookie2 = str(
                payload.get("cookie2", "") or ""
            ).strip() or DIGITAL_CONFIG.get("cookie2", "")
            if cookie2 and (
                not result.get("ok")
                or (result.get("ok") and not result.get("found"))
                or "NotLogin" in str(result.get("error") or "")
            ):
                result = remark_info_and_sync(
                    payload.get("expressNo", ""),
                    cookie2,
                    "",
                    "",
                    "",
                    payload.get("jdlToken", ""),
                    payload.get("jdlCookie", ""),
                    payload.get("clientId", ""),
                    payload.get("customRemark", ""),
                    force_cookie=True,
                    background=parsed.path.endswith("-async"),
                )
                sys.stdout.write(
                    "bridge: remark-info retry cookie2 ok=%s found=%s error=%r\n"
                    % (
                        result.get("ok"),
                        result.get("found"),
                        result.get("error"),
                    )
                )
                sys.stdout.flush()
            self._send_json(200, result)
            return

        if parsed.path != "/api/repair/query":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
            return

        express_no = payload.get("expressNo", "")
        cookie = payload.get("cookie", "")
        user_id = payload.get("userId", "")
        app_code = payload.get("appCode", "")
        shop_code = payload.get("shopCode", "")
        jdl_token = payload.get("jdlToken", "")
        jdl_cookie = payload.get("jdlCookie", "")
        client_id = payload.get("clientId", "")
        result = query_repair(
            express_no,
            cookie,
            user_id,
            app_code,
            shop_code,
            jdl_token,
            jdl_cookie,
            client_id,
        )
        cookie2 = str(payload.get("cookie2", "") or "").strip() or DIGITAL_CONFIG.get("cookie2", "")
        if cookie2 and (
            not result.get("ok")
            or (result.get("ok") and not result.get("found"))
            or "NotLogin" in str(result.get("error") or "")
        ):
            result = query_repair(
                express_no,
                cookie2,
                "",
                "",
                "",
                jdl_token,
                jdl_cookie,
                client_id,
                force_cookie=True,
            )
            sys.stdout.write(
                "bridge: query retry cookie2 %r ok=%s found=%s error=%r\n"
                % (express_no, result.get("ok"), result.get("found"), result.get("error"))
            )
            sys.stdout.flush()
        sys.stdout.write(
            "bridge: query %r ok=%s found=%s performing=%r service=%r merchant=%r error=%r\n"
            % (
                express_no,
                result.get("ok"),
                result.get("found"),
                result.get("performingOrderNo"),
                result.get("serviceOrderNo"),
                result.get("merchantOrderNo"),
                result.get("error"),
            )
        )
        sys.stdout.flush()
        self._send_json(200, result)

    def log_message(self, format, *args):
        sys.stdout.write("bridge: " + format % args + "\n")
        sys.stdout.flush()


def main():
    start_port = int(sys.argv[1]) if len(sys.argv) > 1 else 9090
    server = None
    port = None
    for candidate in range(start_port, start_port + 20):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", candidate), BridgeHandler)
            port = candidate
            break
        except OSError:
            continue
    if server is None or port is None:
        print("JD repair bridge: no free port", flush=True)
        sys.exit(1)
    try:
        hostname = socket.gethostname()
        local_ips = list(dict.fromkeys(socket.gethostbyname_ex(hostname)[2]))
    except Exception:
        local_ips = ["127.0.0.1"]
    print(f"JD repair bridge ready at http://127.0.0.1:{port}", flush=True)
    for ip in local_ips:
        print(f"LAN: http://{ip}:{port}", flush=True)
    load_digital_config()
    load_jdl_token()
    load_client_configs()
    load_shared_states()
    load_agreements()
    ensure_all_agreement_pdfs()
    load_api_keys()
    save_shared_states()
    save_agreements()
    server.serve_forever()


if __name__ == "__main__":
    main()
