const numberFormatter = new Intl.NumberFormat("ko-KR");

const state = {
  authMode: "login",
  user: null,
  dashboard: null,
  includeCurrentMonth: true,
  monthly: [],
  santechMonth: null,
  santech: null,
  santechEditingId: null,
  santechCards: [],
  santechRefundFilter: "all",
  santechProductFilters: new Set(),
  refundSimulation: {
    enabled: false,
    shinsegaeUnit: 0,
    otherUnit: 0,
    excludedIds: new Set(),
  },
  emailSettings: null,
  cream: null,
  mileage: null,
  loaded: {
    dashboard: false,
    monthly: false,
    cream: false,
    mileage: false,
  },
};

async function apiGet(url) {
  return apiRequest(url, { method: "GET" });
}

async function apiPost(url, data) {
  return apiRequest(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

async function apiPatch(url, data) {
  return apiRequest(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

async function apiDelete(url) {
  return apiRequest(url, { method: "DELETE" });
}

async function apiRequest(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = normalizeApiError(data.detail || data.message || message);
    } catch (error) {
      message = `${response.status} ${response.statusText}`;
    }
    if (response.status === 401 && state.user) {
      showAuthView();
    }
    throw new Error(message);
  }
  return response.json();
}

async function loadCurrentUser() {
  const response = await fetch("/api/auth/me");
  if (!response.ok) {
    return null;
  }
  return response.json();
}

async function submitAuth(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form, []);
  try {
    clearAuthError();
    const user = await apiPost(`/api/auth/${state.authMode}`, payload);
    state.user = user;
    form.reset();
    showAppView();
    await loadInitialApp();
  } catch (error) {
    showAuthError(error.message);
  }
}

async function logout() {
  try {
    await apiPost("/api/auth/logout", {});
  } catch (error) {
    // Local UI still returns to the login screen if the session was already gone.
  }
  resetAppState();
  showAuthView();
}

function setAuthMode(mode) {
  state.authMode = mode;
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.authMode === mode);
  });
  document.getElementById("auth-submit").textContent = mode === "register" ? "회원가입" : "로그인";
  clearAuthError();
}

function showAuthView() {
  state.user = null;
  document.getElementById("auth-view").hidden = false;
  document.getElementById("app-header").hidden = true;
  document.getElementById("app-shell").hidden = true;
  document.getElementById("bottom-nav").hidden = true;
}

function showAppView() {
  document.getElementById("auth-view").hidden = true;
  document.getElementById("app-header").hidden = false;
  document.getElementById("app-shell").hidden = false;
  document.getElementById("bottom-nav").hidden = false;
  document.getElementById("current-user-label").textContent = state.user?.username || "";
}

function showAuthError(message) {
  const box = document.getElementById("auth-error");
  box.textContent = message;
  box.hidden = false;
}

function clearAuthError() {
  const box = document.getElementById("auth-error");
  box.textContent = "";
  box.hidden = true;
}

function resetAppState() {
  state.dashboard = null;
  state.monthly = [];
  state.santechMonth = null;
  state.santech = null;
  state.santechEditingId = null;
  state.santechCards = [];
  state.santechRefundFilter = "all";
  state.santechProductFilters = new Set();
  state.refundSimulation = {
    enabled: false,
    shinsegaeUnit: 0,
    otherUnit: 0,
    excludedIds: new Set(),
  };
  state.emailSettings = null;
  state.cream = null;
  state.mileage = null;
  state.loaded = {
    dashboard: false,
    monthly: false,
    cream: false,
    mileage: false,
  };
}

function normalizeApiError(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("\n");
  }
  if (typeof detail === "object" && detail !== null) {
    return JSON.stringify(detail);
  }
  return String(detail);
}

function formatNumber(value) {
  return numberFormatter.format(Number(value) || 0);
}

function formatWon(value) {
  return `${formatNumber(Math.round(Number(value) || 0))}원`;
}

function formatMile(value) {
  return `${formatNumber(Math.round(Number(value) || 0))} mi`;
}

function formatProfit(value) {
  const number = Number(value) || 0;
  if (number > 0) {
    return `+${formatWon(number)}`;
  }
  if (number < 0) {
    return `-${formatWon(Math.abs(number))}`;
  }
  return "0원";
}

function profitClass(value) {
  const number = Number(value) || 0;
  if (number > 0) {
    return "positive";
  }
  if (number < 0) {
    return "negative";
  }
  return "neutral";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    toast.classList.remove("show");
  }, 2200);
}

function showError(message) {
  const box = document.getElementById("global-error");
  box.textContent = message;
  box.hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function clearError() {
  const box = document.getElementById("global-error");
  box.textContent = "";
  box.hidden = true;
}

function switchTab(tabName) {
  clearError();
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${tabName}-view`);
  });
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });

  if (tabName === "dashboard") {
    loadDashboard();
  }
  if ((tabName === "santech" || tabName === "refund") && state.santechMonth) {
    loadSantech(state.santechMonth);
  }
  if (tabName === "cream") {
    loadCream();
  }
}

async function loadDashboard() {
  try {
    clearError();
    state.dashboard = await apiGet(`/api/dashboard?include_current_month=${state.includeCurrentMonth}`);
    state.loaded.dashboard = true;
    renderDashboard();
    await loadMonthly();
    await loadMileage();
  } catch (error) {
    showError(error.message);
  }
}

async function loadMonthly() {
  try {
    state.monthly = await apiGet("/api/monthly");
    state.loaded.monthly = true;
    renderMonthlyTable();
  } catch (error) {
    showError(error.message);
  }
}

async function loadSantech(month) {
  try {
    clearError();
    state.santechMonth = month;
    state.santechEditingId = null;
    state.santech = await apiGet(`/api/santech?month=${encodeURIComponent(month)}`);
    renderSantech();
  } catch (error) {
    showError(error.message);
  }
}

async function loadSantechCards() {
  try {
    clearError();
    state.santechCards = await apiGet("/api/santech/cards");
    renderSantechCards();
    updateSantechPreview();
  } catch (error) {
    showError(error.message);
  }
}

async function loadEmailSettings() {
  try {
    state.emailSettings = await apiGet("/api/email-settings");
    renderEmailSettings();
  } catch (error) {
    showError(error.message);
  }
}

async function submitSantech(event) {
  event.preventDefault();
  if (state.santech?.read_only) {
    showError("읽기 전용 월에는 저장할 수 없습니다.");
    return;
  }

  const form = event.currentTarget;
  const payload = formPayload(form, [
    "purchase_amount",
    "quantity",
    "point_amount",
    "cashback_amount",
    "korean_air",
    "asiana",
    "hana_mile",
  ]);
  const preservedProduct = form.product.value;
  const preservedCard = form.card.value;

  try {
    clearError();
    const created = await apiPost("/api/santech", payload);
    const count = Array.isArray(created) ? created.length : 1;
    showToast(`${count}건의 상테크 거래가 저장되었습니다.`);
    form.reset();
    setSantechDateBounds(state.santechMonth);
    if (santechProductOptions().includes(preservedProduct)) {
      form.product.value = preservedProduct;
    }
    if (santechCardOptions().includes(preservedCard)) {
      form.card.value = preservedCard;
    }
    if (form.product.value !== "신세계상품권") {
      form.purchase_amount.value = 465000;
    }
    updateSantechPreview();
    await refreshAfterMutation("santech");
  } catch (error) {
    showError(error.message);
  }
}

async function submitEmailSettings(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    email: form.elements.email.value.trim(),
    enabled: form.elements.enabled.checked,
  };
  const submitButton = form.querySelector("button[type='submit']");
  try {
    clearError();
    setEmailStatus("저장 중...");
    submitButton.disabled = true;
    state.emailSettings = await apiPatch("/api/email-settings", payload);
    renderEmailSettings("저장되었습니다.");
    showToast("메일 설정이 저장되었습니다.");
  } catch (error) {
    setEmailStatus(error.message);
    showError(error.message);
  } finally {
    submitButton.disabled = false;
  }
}

async function sendTestEmail() {
  const form = document.getElementById("email-settings-form");
  const button = document.getElementById("daily-email-test");
  const payload = {
    email: form.elements.email.value.trim(),
    enabled: form.elements.enabled.checked,
  };
  try {
    clearError();
    setEmailStatus("테스트 메일 발송 중...");
    button.disabled = true;
    state.emailSettings = await apiPatch("/api/email-settings", payload);
    await apiPost("/api/email-settings/test", {});
    renderEmailSettings("테스트 메일을 보냈습니다.");
    showToast("테스트 메일을 보냈습니다.");
  } catch (error) {
    setEmailStatus(error.message);
    showError(error.message);
  } finally {
    button.disabled = false;
  }
}

async function submitSantechCard(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const unlimited = form.is_unlimited.checked;
  const payload = formPayload(form, ["mileage_spend_amount", "mileage_earn_amount", "reward_rate", "monthly_cap"]);
  payload.is_unlimited = unlimited;
  if (payload.benefit_type === "mileage") {
    payload.reward_rate = 0;
    payload.monthly_cap = null;
    payload.is_unlimited = true;
  } else if (unlimited) {
    payload.monthly_cap = null;
  }

  try {
    clearError();
    await apiPost("/api/santech/cards", payload);
    showToast("카드가 추가되었습니다.");
    form.reset();
    updateCardBenefitFields();
    await loadSantechCards();
    if (state.santechMonth) {
      await loadSantech(state.santechMonth);
    }
  } catch (error) {
    showError(error.message);
  }
}

async function deleteSantechCard(id) {
  if (!confirm("이 카드를 삭제할까요? 이미 거래에 사용된 카드는 삭제할 수 없습니다.")) {
    return;
  }
  try {
    clearError();
    await apiDelete(`/api/santech/cards/${id}`);
    showToast("카드가 삭제되었습니다.");
    await loadSantechCards();
    if (state.santechMonth) {
      await loadSantech(state.santechMonth);
    }
  } catch (error) {
    showError(error.message);
  }
}

async function deleteSantech(id) {
  if (!confirm("이 상테크 거래를 삭제할까요?")) {
    return;
  }
  try {
    clearError();
    await apiDelete(`/api/santech/${id}`);
    showToast("삭제되었습니다.");
    await refreshAfterMutation("santech");
  } catch (error) {
    showError(error.message);
  }
}

async function bulkUpdateSantechRefund() {
  const ids = Array.from(document.querySelectorAll("[data-santech-select]:checked")).map((input) => input.dataset.santechSelect);
  if (!ids.length) {
    showError("환급 정보를 입력할 거래를 먼저 선택해주세요.");
    return;
  }

  const vendorSelect = document.getElementById("bulk-refund-vendor");
  const amountInput = document.getElementById("bulk-refund-amount");
  const refundAmount = Number(amountInput.value || 0);

  try {
    clearError();
    for (const id of ids) {
      await apiPatch(`/api/santech/${id}/refund`, {
        refund_amount: refundAmount,
        refund_vendor: vendorSelect.value,
      });
    }
    showToast(`${ids.length}건의 환급 정보가 반영되었습니다.`);
    await refreshAfterMutation("santech");
  } catch (error) {
    showError(error.message);
  }
}

async function bulkDeleteSantech() {
  const ids = Array.from(document.querySelectorAll("[data-santech-select]:checked")).map((input) => input.dataset.santechSelect);
  if (!ids.length) {
    showError("삭제할 거래를 먼저 선택해주세요.");
    return;
  }
  if (!confirm(`선택한 ${ids.length}건을 삭제할까요?`)) {
    return;
  }

  try {
    clearError();
    for (const id of ids) {
      await apiDelete(`/api/santech/${id}`);
    }
    showToast(`${ids.length}건이 삭제되었습니다.`);
    await refreshAfterMutation("santech");
  } catch (error) {
    showError(error.message);
  }
}

async function updateSantechTransaction(id) {
  const form = document.querySelector(`[data-santech-edit-form="${id}"]`);
  if (!form) {
    return;
  }
  const payload = formPayload(form, ["purchase_amount", "refund_amount", "korean_air", "asiana"]);
  if (!payload.refund_vendor) {
    payload.refund_vendor = null;
  }

  try {
    clearError();
    await apiPatch(`/api/santech/${id}`, payload);
    state.santechEditingId = null;
    showToast("거래가 수정되었습니다.");
    await refreshAfterMutation("santech");
  } catch (error) {
    showError(error.message);
  }
}

async function loadCream() {
  try {
    clearError();
    state.cream = await apiGet("/api/cream");
    state.loaded.cream = true;
    renderCream();
  } catch (error) {
    showError(error.message);
  }
}

async function submitCream(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form, [
    "buy_amount",
    "sell_amount",
    "payback_amount",
    "korean_air",
    "asiana",
  ]);

  try {
    clearError();
    await apiPost("/api/cream", payload);
    showToast("크림 거래가 저장되었습니다.");
    form.reset();
    setCreamDateDefault();
    updateCreamPreview();
    await refreshAfterMutation("cream");
  } catch (error) {
    showError(error.message);
  }
}

async function deleteCream(id) {
  if (!confirm("이 크림 거래를 삭제할까요?")) {
    return;
  }
  try {
    clearError();
    await apiDelete(`/api/cream/${id}`);
    showToast("삭제되었습니다.");
    await refreshAfterMutation("cream");
  } catch (error) {
    showError(error.message);
  }
}

async function loadMileage() {
  try {
    clearError();
    state.mileage = await apiGet(`/api/mileage?include_current_month=${state.includeCurrentMonth}`);
    state.loaded.mileage = true;
    renderMileage();
  } catch (error) {
    showError(error.message);
  }
}

function renderDashboard() {
  if (!state.dashboard) {
    return;
  }
  const data = state.dashboard;
  document.getElementById("dashboard-cards").innerHTML = [
    metricCard("누적 총 수익", formatProfit(data.total_profit), profitClass(data.total_profit), `상테크 ${formatProfit(data.total_st_profit)} · 리셀 ${formatProfit(data.total_cr_profit)}`),
    metricCard(`${data.current_month} 수익`, formatProfit(data.current_month_profit), profitClass(data.current_month_profit), "이번 달 합산"),
    metricCard("누적 마일리지", formatMile(data.miles.total), "neutral", `대한항공 ${formatNumber(data.miles.korean_air)} · 아시아나 ${formatNumber(data.miles.asiana)} · 하나마일 ${formatNumber(data.miles.hana_mile)}`),
    metricCard("마일 평균 단가", `${formatNumber(data.avg_mile_price.toFixed(2))}원`, "neutral", "상테크 손익 기준"),
  ].join("");
  renderRefundSimulationControls();
}

function renderRefundSimulationControls() {
  const enabledInput = document.getElementById("refund-simulation-enabled");
  const panel = document.getElementById("refund-simulation-panel");
  const shinsegaeInput = document.getElementById("refund-sim-shinsegae");
  const otherInput = document.getElementById("refund-sim-other");
  const summaryBox = document.getElementById("refund-simulation-summary");
  if (!enabledInput || !panel || !shinsegaeInput || !otherInput || !summaryBox) {
    return;
  }
  enabledInput.checked = state.refundSimulation.enabled;
  panel.hidden = !state.refundSimulation.enabled;
  shinsegaeInput.value = state.refundSimulation.shinsegaeUnit;
  otherInput.value = state.refundSimulation.otherUnit;

  const rows = state.santech?.transactions || [];
  const summary = summarizeSantechRefundStatus(rows);
  summaryBox.innerHTML = [
    miniMetric("미환급 구매", formatWon(summary.pendingPurchase)),
    miniMetric("예상 환급", formatWon(summary.simulatedRefund)),
    miniMetric("예상 손익", formatProfit(summary.simulatedProfit), profitClass(summary.simulatedProfit)),
  ].join("");
}

function updateRefundSimulationFromControls() {
  const enabledInput = document.getElementById("refund-simulation-enabled");
  const shinsegaeInput = document.getElementById("refund-sim-shinsegae");
  const otherInput = document.getElementById("refund-sim-other");
  state.refundSimulation.enabled = Boolean(enabledInput?.checked);
  state.refundSimulation.shinsegaeUnit = Number(shinsegaeInput?.value || 0);
  state.refundSimulation.otherUnit = Number(otherInput?.value || 0);
  renderRefundSimulationControls();
  if (state.santech) {
    renderSantechTransactions(state.santech);
  }
}

function renderEmailSettings(message = "") {
  const form = document.getElementById("email-settings-form");
  if (!form || !state.emailSettings) {
    return;
  }
  form.elements.email.value = state.emailSettings.email || "";
  form.elements.enabled.checked = Boolean(state.emailSettings.enabled);
  const lastSent = state.emailSettings.last_sent_on ? `마지막 발송 ${state.emailSettings.last_sent_on}` : "아직 발송 전";
  setEmailStatus(message || lastSent);
}

function setEmailStatus(message) {
  const status = document.getElementById("daily-email-status");
  if (status) {
    status.textContent = message;
  }
}

function renderMonthlyTable() {
  const tbody = document.getElementById("monthly-tbody");
  if (!state.monthly.length) {
    tbody.innerHTML = emptyRow(13, "월별 데이터가 없습니다.");
    return;
  }

  tbody.innerHTML = state.monthly
    .map(
      (row) => `
        <tr>
          <td class="text-left">${escapeHtml(row.year_month)}${row.is_seed ? " · 시드" : ""}</td>
          <td>${formatNumber(row.mile_unit_price.toFixed(2))}</td>
          <td>${formatNumber(row.total_miles)}</td>
          <td>${formatNumber(row.korean_air)}</td>
          <td>${formatNumber(row.asiana)}</td>
          <td>${formatNumber(row.hana_mile)}</td>
          <td>${formatWon(row.st_purchase)}</td>
          <td>${formatWon(row.st_refund)}</td>
          <td class="${profitClass(row.st_profit)}">${formatProfit(row.st_profit)}</td>
          <td>${formatWon(row.st_point)}</td>
          <td>${formatWon(row.st_cashback)}</td>
          <td class="${profitClass(row.cr_profit)}">${formatProfit(row.cr_profit)}</td>
          <td class="${profitClass(row.total_profit)}">${formatProfit(row.total_profit)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderSantech() {
  const data = state.santech;
  if (!data) {
    return;
  }

  const readonlyBadge = document.getElementById("santech-readonly");
  readonlyBadge.hidden = !data.read_only;
  document.getElementById("santech-fieldset").disabled = data.read_only;
  syncSantechMonthControls(data.month);

  renderSantechSummary(data.summary);
  renderSantechCardUsage(data.card_usage || []);
  syncSantechProductFilterControls();
  renderSantechTransactions(data);
  renderSantechRecent(data.recent_templates || []);
  renderRefundSimulationControls();
}

function renderSantechSummary(summary) {
  const totalMiles = summary.korean_air + summary.asiana + summary.hana_mile;
  document.getElementById("santech-summary").innerHTML = [
    miniMetric("매매", formatWon(summary.purchase)),
    miniMetric("환급", formatWon(summary.refund)),
    miniMetric("수익", formatProfit(summary.profit), profitClass(summary.profit)),
    miniMetric("마일", formatMile(totalMiles)),
  ].join("");
}

function renderSantechCards() {
  renderSantechCardOptions();
  renderSantechCardRules();
}

function renderSantechCardOptions() {
  const options = santechCardOptions();
  const optionHtml = options.map((card) => `<option value="${escapeHtml(card)}">${escapeHtml(card)}</option>`).join("");
  document.querySelectorAll('select[name="card"]').forEach((select) => {
    const current = select.value;
    select.innerHTML = optionHtml;
    if (options.includes(current)) {
      select.value = current;
    }
  });
}

function renderSantechCardRules() {
  const tbody = document.getElementById("santech-card-rules-tbody");
  if (!tbody) {
    return;
  }
  if (!state.santechCards.length) {
    tbody.innerHTML = emptyRow(4, "등록된 카드가 없습니다.");
    return;
  }
  tbody.innerHTML = state.santechCards
    .map(
      (card) => `
        <tr>
          <td class="text-left">${escapeHtml(card.name)}</td>
          <td class="text-left">${escapeHtml(cardBenefitTypeLabel(card.benefit_type))}</td>
          <td class="text-left">${escapeHtml(cardBenefitDescription(card))}</td>
          <td><button class="danger-button" type="button" data-delete-santech-card="${card.id}" aria-label="카드 삭제" title="카드 삭제">×</button></td>
        </tr>
      `,
    )
    .join("");
}

function renderSantechTransactions(data) {
  const tbody = document.getElementById("santech-tbody");
  const tfoot = document.getElementById("santech-tfoot");
  const productRows = productFilteredSantechTransactions(data.transactions || []);
  const rows = filteredSantechTransactions(data.transactions || []);
  syncSantechSelectAll(false);
  renderSantechRefundStatus(productRows);

  if (!rows.length) {
    tbody.innerHTML = emptyRow(15, data.read_only ? "과거 시드 월은 상세 거래가 없습니다." : "조건에 맞는 거래가 없습니다.");
  } else {
    tbody.innerHTML = rows.map((row) => renderSantechTransactionRow(row, data.read_only)).join("");
  }

  const summary = summarizeSantechRows(rows);
  tfoot.innerHTML = `
    <tr>
      <td class="text-left" colspan="4">합계</td>
      <td>${formatWon(summary.purchase)}</td>
      <td></td>
      <td>${formatWon(summary.refund)}</td>
      <td></td>
      <td>${formatWon(summary.cashback)}</td>
      <td class="${profitClass(summary.profit)}">${formatProfit(summary.profit)}</td>
      <td>${formatNumber(summary.korean_air)}</td>
      <td>${formatNumber(summary.asiana)}</td>
      <td>${formatNumber(summary.hana_mile)}</td>
      <td colspan="2"></td>
    </tr>
  `;
}

function renderSantechRefundStatus(rows) {
  const box = document.getElementById("santech-refund-status");
  if (!box) {
    return;
  }
  const summary = summarizeSantechRefundStatus(rows);
  const metrics = [
    miniMetric("현재 환급금", formatWon(summary.refund)),
    miniMetric("환급 필요 구매금액", formatWon(summary.pendingPurchase)),
  ];
  if (state.refundSimulation.enabled) {
    metrics.push(
      miniMetric("모의 예상 환급", formatWon(summary.simulatedRefund)),
      miniMetric("모의 예상 수익", formatProfit(summary.simulatedProfit), profitClass(summary.simulatedProfit)),
    );
  }
  box.innerHTML = metrics.join("");
}

function renderSantechTransactionRow(row, readOnly) {
  const editing = Number(state.santechEditingId) === Number(row.id);
  const editableClass = readOnly ? "text-left" : "text-left editable-cell";
  const editAttr = readOnly ? "" : ` data-edit-santech="${row.id}" title="수정"`;
  const numberEditAttr = readOnly ? "" : ` class="editable-cell" data-edit-santech="${row.id}" title="수정"`;
  const actionButtons = readOnly
    ? ""
    : `
      <div class="row-actions">
        <button class="secondary-button compact-button" type="button" data-edit-santech="${row.id}">수정</button>
        <button class="danger-button" type="button" data-delete-santech="${row.id}" aria-label="삭제" title="삭제">×</button>
      </div>
    `;

  return `
    <tr class="${editing ? "is-editing" : ""}">
      <td><input type="checkbox" data-santech-select="${row.id}" aria-label="거래 선택" /></td>
      <td class="${editableClass}"${editAttr}>${escapeHtml(row.date)}</td>
      <td class="${editableClass}"${editAttr}>${escapeHtml(row.product)}</td>
      <td class="${editableClass}"${editAttr}>${escapeHtml(row.card)}</td>
      <td${numberEditAttr}>${formatWon(row.purchase_amount)}</td>
      <td>${renderRefundSimulationToggle(row)}</td>
      <td${numberEditAttr}>${renderRefundAmount(row)}</td>
      <td class="${editableClass}"${editAttr}>${escapeHtml(row.refund_vendor || "미입력")}</td>
      <td>${formatWon(row.cashback_amount)}</td>
      <td class="${profitClass(effectiveSantechProfit(row))}">${formatProfit(effectiveSantechProfit(row))}</td>
      <td${numberEditAttr}>${formatNumber(row.korean_air)}</td>
      <td${numberEditAttr}>${formatNumber(row.asiana)}</td>
      <td>${formatNumber(row.hana_mile)}</td>
      <td class="${editableClass}"${editAttr}>${escapeHtml(row.memo)}</td>
      <td>${actionButtons}</td>
    </tr>
    ${editing ? renderSantechEditRow(row) : ""}
  `;
}

function renderSantechEditRow(row) {
  const productOptions = santechProductOptions()
    .map((option) => `<option value="${escapeHtml(option)}"${option === row.product ? " selected" : ""}>${escapeHtml(option)}</option>`)
    .join("");
  const cardOptions = santechCardOptions()
    .map((option) => `<option value="${escapeHtml(option)}"${option === row.card ? " selected" : ""}>${escapeHtml(option)}</option>`)
    .join("");
  const refundVendorOptions = [
    `<option value=""${row.refund_vendor ? "" : " selected"}>미입력</option>`,
    ...santechRefundVendorOptions().map(
      (option) => `<option value="${escapeHtml(option)}"${option === row.refund_vendor ? " selected" : ""}>${escapeHtml(option)}</option>`,
    ),
  ].join("");
  const minDate = `${row.year_month}-01`;
  const maxDate = lastDateOfMonth(row.year_month);

  return `
    <tr class="santech-edit-row">
      <td colspan="15">
        <form class="santech-edit-form" data-santech-edit-form="${row.id}">
          <label>
            <span>날짜</span>
            <input type="date" name="date" value="${escapeHtml(row.date)}" min="${minDate}" max="${maxDate}" required />
          </label>
          <label>
            <span>구매상품</span>
            <select name="product">${productOptions}</select>
          </label>
          <label>
            <span>카드</span>
            <select name="card">${cardOptions}</select>
          </label>
          <label>
            <span>매매</span>
            <input type="number" name="purchase_amount" min="0" step="1" inputmode="numeric" value="${row.purchase_amount}" required />
          </label>
          <label>
            <span>환급</span>
            <input type="number" name="refund_amount" min="0" step="1" inputmode="numeric" value="${row.refund_amount}" />
          </label>
          <label>
            <span>환급처</span>
            <select name="refund_vendor">${refundVendorOptions}</select>
          </label>
          <label>
            <span>대한항공</span>
            <input type="number" name="korean_air" min="0" step="1" inputmode="numeric" value="${row.korean_air}" />
          </label>
          <label>
            <span>아시아나</span>
            <input type="number" name="asiana" min="0" step="1" inputmode="numeric" value="${row.asiana}" />
          </label>
          <label class="wide-field">
            <span>메모</span>
            <input type="text" name="memo" value="${escapeHtml(row.memo)}" />
          </label>
          <div class="santech-edit-actions">
            <button class="secondary-button" type="submit">저장</button>
            <button class="icon-button" type="button" data-cancel-santech-edit="${row.id}" aria-label="취소" title="취소">×</button>
          </div>
        </form>
      </td>
    </tr>
  `;
}

function filteredSantechTransactions(rows) {
  const productRows = productFilteredSantechTransactions(rows);
  if (state.santechRefundFilter === "refunded") {
    return productRows.filter(isSantechRefunded);
  }
  if (state.santechRefundFilter === "pending") {
    return productRows.filter((row) => !isSantechRefunded(row));
  }
  return productRows;
}

function productFilteredSantechTransactions(rows) {
  if (!state.santechProductFilters.size) {
    return rows;
  }
  return rows.filter((row) => state.santechProductFilters.has(row.product));
}

function syncSantechProductFilterControls() {
  document.querySelectorAll("[data-santech-product-filter]").forEach((input) => {
    input.checked = state.santechProductFilters.has(input.value);
  });
}

function isSantechRefunded(row) {
  return Number(row.refund_amount || 0) > 0 && Boolean(row.refund_vendor);
}

function isRefundSimulationApplicable(row) {
  return state.refundSimulation.enabled && !isSantechRefunded(row);
}

function isRefundSimulationApplied(row) {
  return isRefundSimulationApplicable(row) && !state.refundSimulation.excludedIds.has(String(row.id));
}

function simulatedRefundAmount(row) {
  if (!isRefundSimulationApplied(row)) {
    return 0;
  }
  const baseAmount = row.product === "신세계상품권" ? 100000 : 500000;
  const unitAmount = row.product === "신세계상품권" ? state.refundSimulation.shinsegaeUnit : state.refundSimulation.otherUnit;
  return Math.floor((Number(row.purchase_amount || 0) / baseAmount) * Number(unitAmount || 0));
}

function effectiveSantechRefund(row) {
  return isRefundSimulationApplied(row) ? simulatedRefundAmount(row) : Number(row.refund_amount || 0);
}

function effectiveSantechProfit(row) {
  if (!isRefundSimulationApplied(row)) {
    return Number(row.profit || 0);
  }
  return Number(row.profit || 0) + simulatedRefundAmount(row);
}

function renderRefundSimulationToggle(row) {
  if (!isRefundSimulationApplicable(row)) {
    return '<span class="muted-cell">-</span>';
  }
  const checked = isRefundSimulationApplied(row) ? " checked" : "";
  return `<input type="checkbox" data-refund-sim-toggle="${row.id}" aria-label="모의 계산 적용"${checked} />`;
}

function renderRefundAmount(row) {
  if (!isRefundSimulationApplied(row)) {
    return formatWon(row.refund_amount);
  }
  return `${formatWon(simulatedRefundAmount(row))}<small class="sim-note">모의</small>`;
}

function summarizeSantechRows(rows) {
  return rows.reduce(
    (sum, row) => {
      sum.purchase += Number(row.purchase_amount || 0);
      sum.refund += effectiveSantechRefund(row);
      sum.cashback += Number(row.cashback_amount || 0);
      sum.profit += effectiveSantechProfit(row);
      sum.korean_air += Number(row.korean_air || 0);
      sum.asiana += Number(row.asiana || 0);
      sum.hana_mile += Number(row.hana_mile || 0);
      return sum;
    },
    { purchase: 0, refund: 0, cashback: 0, profit: 0, korean_air: 0, asiana: 0, hana_mile: 0 },
  );
}

function summarizeSantechRefundStatus(rows) {
  return rows.reduce(
    (sum, row) => {
      sum.refund += Number(row.refund_amount || 0);
      if (!isSantechRefunded(row)) {
        sum.pendingPurchase += Number(row.purchase_amount || 0);
        if (isRefundSimulationApplied(row)) {
          const simulatedRefund = simulatedRefundAmount(row);
          sum.simulatedRefund += simulatedRefund;
          sum.simulatedProfit += Number(row.profit || 0) + simulatedRefund;
        }
      }
      return sum;
    },
    { refund: 0, pendingPurchase: 0, simulatedRefund: 0, simulatedProfit: 0 },
  );
}

function renderSantechCardUsage(rows) {
  const tbody = document.getElementById("santech-card-usage-tbody");
  if (!rows.length) {
    tbody.innerHTML = emptyRow(8, "카드별 사용량이 없습니다.");
    return;
  }

  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td class="text-left">${escapeHtml(row.card)}</td>
          <td>${formatNumber(row.count)}</td>
          <td>${formatWon(row.purchase_amount)}</td>
          <td>${formatWon(row.refund_amount)}</td>
          <td>${formatWon(row.cashback_amount)}</td>
          <td>${formatWon(row.point_amount)}</td>
          <td>${formatNumber(row.hana_mile)}</td>
          <td class="${profitClass(row.profit)}">${formatProfit(row.profit)}</td>
        </tr>
      `,
    )
    .join("");
}

function syncSantechSelectAll(checked = false) {
  const master = document.getElementById("santech-select-all");
  if (!master) {
    return;
  }
  master.checked = checked;
  master.indeterminate = false;
}

function updateSantechSelectAllState() {
  const master = document.getElementById("santech-select-all");
  const checkboxes = Array.from(document.querySelectorAll("[data-santech-select]"));
  if (!master || !checkboxes.length) {
    syncSantechSelectAll(false);
    return;
  }
  const checkedCount = checkboxes.filter((input) => input.checked).length;
  master.checked = checkedCount === checkboxes.length;
  master.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

function renderSantechRecent(rows) {
  const select = document.getElementById("santech-recent-select");
  if (!rows.length) {
    select.innerHTML = '<option value="">최근 입력 없음</option>';
    select.disabled = true;
    document.getElementById("santech-load-recent").disabled = true;
    return;
  }

  select.disabled = false;
  document.getElementById("santech-load-recent").disabled = false;
  select.innerHTML = rows
    .map((row) => {
      const label = `${row.date} · ${row.card} · ${row.product} · ${formatWon(row.purchase_amount)}`;
      return `<option value="${row.id}">${escapeHtml(label)}</option>`;
    })
    .join("");
}

function loadRecentSantech() {
  const select = document.getElementById("santech-recent-select");
  const id = Number(select.value);
  const row = (state.santech?.recent_templates || []).find((item) => item.id === id);
  if (!row) {
    return;
  }

  const form = document.getElementById("santech-form");
  form.product.value = normalizeSantechProduct(row.product);
  form.card.value = normalizeSantechCard(row.card);
  form.purchase_amount.value = row.purchase_amount || 0;
  form.quantity.value = 1;
  form.korean_air.value = row.korean_air || 0;
  form.asiana.value = row.asiana || 0;
  form.memo.value = row.memo || "";
  updateSantechPreview();
  showToast("최근 입력을 불러왔습니다.");
}

function normalizeSantechCard(card) {
  if (santechCardOptions().includes(card)) {
    return card;
  }
  if (card === "유니" && santechCardOptions().includes("any")) {
    return "any";
  }
  return santechCardOptions()[0] || "";
}

function normalizeSantechProduct(product) {
  if (santechProductOptions().includes(product)) {
    return product;
  }
  if (product === "신세계" || product === "이마트") {
    return "신세계상품권";
  }
  if (product === "컬쳐") {
    return "컬쳐랜드";
  }
  if (product === "게임권") {
    return "게임온패스";
  }
  return product || "신세계상품권";
}

function santechProductOptions() {
  return ["신세계상품권", "북앤라이프", "컬쳐랜드", "틴캐시", "게임온패스"];
}

function santechCardOptions() {
  return state.santechCards.map((card) => card.name);
}

function santechRefundVendorOptions() {
  return ["포인트로페이", "페이즈", "마일캐시", "원천", "골드", "팔라고", "GLN"];
}

function cardBenefitTypeLabel(type) {
  const labels = {
    mileage: "마일리지",
    cashback: "캐시백",
    discount: "청구할인",
  };
  return labels[type] || type || "";
}

function cardBenefitDescription(card) {
  if (!card) {
    return "";
  }
  if (card.benefit_type === "mileage") {
    return `${mileageTargetLabel(card.mileage_target)} · ${formatWon(card.mileage_spend_amount)}당 ${formatNumber(card.mileage_earn_amount)}마일`;
  }
  const cap = card.is_unlimited ? "무제한" : `월 ${formatWon(card.monthly_cap)}`;
  return `${formatNumber(card.reward_rate)}% · ${cap}`;
}

function mileageTargetLabel(target) {
  const labels = {
    korean_air: "대한항공",
    asiana: "아시아나",
    hana_mile: "하나마일",
  };
  return labels[target] || "하나마일";
}

function renderCream() {
  if (!state.cream) {
    return;
  }

  const tbody = document.getElementById("cream-tbody");
  const seedTbody = document.getElementById("cream-seed-tbody");

  if (!state.cream.transactions.length) {
    tbody.innerHTML = emptyRow(10, "라이브 거래가 없습니다.");
  } else {
    tbody.innerHTML = state.cream.transactions
      .map(
        (row) => `
          <tr>
            <td class="text-left">${escapeHtml(row.date)}</td>
            <td class="text-left">${escapeHtml(row.year_month)}</td>
            <td class="text-left">${escapeHtml(row.platform)}</td>
            <td class="text-left">${escapeHtml(row.card_company)}</td>
            <td>${formatWon(row.buy_amount)}</td>
            <td>${formatWon(row.sell_amount)}</td>
            <td>${formatWon(row.payback_amount)}</td>
            <td class="${profitClass(row.profit)}">${formatProfit(row.profit)}</td>
            <td class="text-left">${escapeHtml(row.condition)}</td>
            <td><button class="danger-button" type="button" data-delete-cream="${row.id}" aria-label="삭제" title="삭제">×</button></td>
          </tr>
        `,
      )
      .join("");
  }

  if (!state.cream.seed_summaries.length) {
    seedTbody.innerHTML = emptyRow(5, "시드 요약이 없습니다.");
  } else {
    seedTbody.innerHTML = state.cream.seed_summaries
      .map(
        (row) => `
          <tr>
            <td class="text-left">${escapeHtml(row.year_month)}</td>
            <td>${formatNumber(row.cr_korean_air)}</td>
            <td>${formatNumber(row.cr_asiana)}</td>
            <td>${formatWon(row.cr_buy_total)}</td>
            <td class="${profitClass(row.cr_profit)}">${formatProfit(row.cr_profit)}</td>
          </tr>
        `,
      )
      .join("");
  }
}

function renderMileage() {
  if (!state.mileage) {
    return;
  }
  const totals = state.mileage.totals;
  document.getElementById("mileage-cards").innerHTML = [
    metricCard("대한항공", formatMile(totals.korean_air), "neutral", ""),
    metricCard("아시아나", formatMile(totals.asiana), "neutral", ""),
    metricCard("하나마일", formatMile(totals.hana_mile), "neutral", ""),
  ].join("");

  const input = document.getElementById("mile-unit-price");
  if (!input.value) {
    input.value = state.mileage.default_unit_price;
  }
  renderMileageValue();

  const tbody = document.getElementById("mileage-year-tbody");
  if (!state.mileage.by_year.length) {
    tbody.innerHTML = emptyRow(5, "적립 데이터가 없습니다.");
    return;
  }
  tbody.innerHTML = state.mileage.by_year
    .map(
      (row) => `
        <tr>
          <td class="text-left">${row.year}</td>
          <td>${formatNumber(row.korean_air)}</td>
          <td>${formatNumber(row.asiana)}</td>
          <td>${formatNumber(row.hana_mile)}</td>
          <td>${formatNumber(row.total)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderMileageValue() {
  if (!state.mileage) {
    return;
  }
  const unit = Number(document.getElementById("mile-unit-price").value) || 0;
  const totals = state.mileage.totals;
  document.getElementById("mileage-value").innerHTML = [
    valueCard("대한항공", formatWon(totals.korean_air * unit)),
    valueCard("아시아나", formatWon(totals.asiana * unit)),
    valueCard("하나마일", formatWon(totals.hana_mile * unit)),
    valueCard("총 예상 가치", formatWon(totals.total * unit), "full"),
  ].join("");
}

function metricCard(label, value, className, note) {
  return `
    <article class="metric-card">
      <span>${escapeHtml(label)}</span>
      <strong class="${className}">${escapeHtml(value)}</strong>
      ${note ? `<small>${escapeHtml(note)}</small>` : ""}
    </article>
  `;
}

function miniMetric(label, value, className = "neutral") {
  return `
    <article class="mini-metric">
      <span>${escapeHtml(label)}</span>
      <strong class="${className}">${escapeHtml(value)}</strong>
    </article>
  `;
}

function valueCard(label, value, extraClass = "") {
  return `
    <article class="value-card ${extraClass}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function emptyRow(colspan, text) {
  return `<tr><td class="empty-row" colspan="${colspan}">${escapeHtml(text)}</td></tr>`;
}

function formPayload(form, numberFields) {
  const data = Object.fromEntries(new FormData(form).entries());
  numberFields.forEach((field) => {
    data[field] = Number(data[field] || 0);
  });
  return data;
}

function updateSantechPreview() {
  const form = document.getElementById("santech-form");
  const card = form.card.value;
  const purchase = Number(form.purchase_amount.value || 0);
  const quantity = Math.max(1, Number(form.quantity.value || 1));
  const refund = 0;
  const benefits = calculateSantechBenefits(card, purchase);
  form.point_amount.value = benefits.point_amount;
  form.cashback_amount.value = benefits.cashback_amount;
  form.hana_mile.value = benefits.hana_mile;
  const profile = state.santechCards.find((item) => item.name === card);
  if (profile?.benefit_type === "mileage" && profile.mileage_target === "korean_air") {
    form.korean_air.value = benefits.korean_air;
  }
  if (profile?.benefit_type === "mileage" && profile.mileage_target === "asiana") {
    form.asiana.value = benefits.asiana;
  }
  const point = benefits.point_amount;
  const cashback = benefits.cashback_amount;
  const profit = (refund + point + cashback - purchase) * quantity;
  const preview = document.getElementById("santech-preview");
  preview.textContent = `예상 수익: ${formatProfit(profit)}${quantity > 1 ? ` (${quantity}건)` : ""}`;
  preview.className = `profit-preview ${profitClass(profit)}`;
}

function applySantechProductDefault() {
  const form = document.getElementById("santech-form");
  if (form.product.value !== "신세계상품권") {
    form.purchase_amount.value = 465000;
  }
  updateSantechPreview();
}

function calculateSantechBenefits(card, purchase) {
  const amount = Number(purchase) || 0;
  const benefits = { point_amount: 0, cashback_amount: 0, korean_air: 0, asiana: 0, hana_mile: 0 };
  const profile = state.santechCards.find((item) => item.name === card);

  if (!profile) {
    return benefits;
  }
  if (profile.benefit_type === "mileage") {
    const target = profile.mileage_target || "hana_mile";
    benefits[target] = Math.floor((amount / Number(profile.mileage_spend_amount || 1)) * Number(profile.mileage_earn_amount || 0));
  } else if (profile.benefit_type === "cashback" || profile.benefit_type === "discount") {
    const benefit = Math.floor(amount * (Number(profile.reward_rate || 0) / 100));
    if (profile.is_unlimited) {
      benefits.cashback_amount = benefit;
    } else {
      const remaining = Math.max(0, Number(profile.monthly_cap || 0) - santechUsedCardDiscount(card));
      benefits.cashback_amount = Math.min(benefit, remaining);
    }
  }

  return benefits;
}

function santechUsedCardDiscount(card) {
  const rows = state.santech?.transactions || [];
  return rows
    .filter((row) => row.card === card)
    .reduce((total, row) => total + Number(row.cashback_amount || 0), 0);
}

function updateCreamPreview() {
  const form = document.getElementById("cream-form");
  const buy = Number(form.buy_amount.value || 0);
  const sell = Number(form.sell_amount.value || 0);
  const payback = Number(form.payback_amount.value || 0);
  const profit = sell - buy + payback;
  const preview = document.getElementById("cream-preview");
  preview.textContent = `예상 수익: ${formatProfit(profit)}`;
  preview.className = `profit-preview ${profitClass(profit)}`;
}

async function refreshAfterMutation(area) {
  const shouldReloadMileage = state.loaded.mileage;
  state.loaded.dashboard = false;
  state.loaded.monthly = false;
  state.loaded.mileage = false;
  if (area === "santech") {
    await loadSantech(state.santechMonth);
  }
  if (area === "cream") {
    await loadCream();
  }
  await loadDashboard();
  if (shouldReloadMileage) {
    await loadMileage();
  }
}

function setupSantechMonths(currentMonth) {
  const selects = [document.getElementById("santech-month"), document.getElementById("refund-month")].filter(Boolean);
  const endMonth = maxMonth(currentMonth, "2026-07");
  const months = monthRange("2026-01", endMonth);
  selects.forEach((select) => {
    select.innerHTML = months.map((month) => `<option value="${month}">${month}</option>`).join("");
    select.value = endMonth;
  });
  state.santechMonth = endMonth;
  setSantechDateBounds(endMonth);
}

function syncSantechMonthControls(month) {
  document.querySelectorAll("#santech-month, #refund-month").forEach((select) => {
    select.value = month;
  });
}

function setSantechDateBounds(month) {
  const input = document.getElementById("santech-date");
  const min = `${month}-01`;
  const max = lastDateOfMonth(month);
  input.min = min;
  input.max = max;
  input.value = clampDate(todayText(), min, max);
}

function setCreamDateDefault() {
  const input = document.getElementById("cream-date");
  input.value = maxDate(todayText(), "2026-07-01");
}

function monthRange(start, end) {
  const months = [];
  let cursor = start;
  while (cursor <= end) {
    months.push(cursor);
    cursor = nextMonth(cursor);
  }
  return months;
}

function nextMonth(month) {
  const [yearText, monthText] = month.split("-");
  let year = Number(yearText);
  let next = Number(monthText) + 1;
  if (next === 13) {
    year += 1;
    next = 1;
  }
  return `${year}-${String(next).padStart(2, "0")}`;
}

function lastDateOfMonth(month) {
  const [yearText, monthText] = month.split("-");
  const lastDay = new Date(Number(yearText), Number(monthText), 0).getDate();
  return `${month}-${String(lastDay).padStart(2, "0")}`;
}

function todayText() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function maxMonth(a, b) {
  return a >= b ? a : b;
}

function maxDate(a, b) {
  return a >= b ? a : b;
}

function clampDate(value, min, max) {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

function openSantechEdit(id) {
  if (!state.santech || state.santech.read_only) {
    return;
  }
  state.santechEditingId = Number(id);
  renderSantechTransactions(state.santech);
  requestAnimationFrame(() => {
    document.querySelector(`[data-santech-edit-form="${id}"] input, [data-santech-edit-form="${id}"] select`)?.focus();
  });
}

function cancelSantechEdit() {
  state.santechEditingId = null;
  if (state.santech) {
    renderSantechTransactions(state.santech);
  }
}

function updateCardBenefitFields() {
  const form = document.getElementById("santech-card-form");
  if (!form) {
    return;
  }
  const isMileage = form.benefit_type.value === "mileage";
  const isUnlimited = form.is_unlimited.checked;

  form.querySelectorAll(".card-mileage-field").forEach((field) => {
    field.hidden = !isMileage;
    field.querySelectorAll("input").forEach((input) => {
      input.required = isMileage;
    });
  });
  form.querySelectorAll(".card-rate-field").forEach((field) => {
    field.hidden = isMileage;
  });
  form.reward_rate.required = !isMileage;
  form.monthly_cap.required = !isMileage && !isUnlimited;
  form.querySelectorAll(".card-cap-field").forEach((field) => {
    field.hidden = isMileage || isUnlimited;
  });
}

function bindEvents() {
  document.getElementById("auth-form").addEventListener("submit", submitAuth);
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
  });
  document.getElementById("logout-button").addEventListener("click", logout);

  document.querySelectorAll(".nav-button").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  document.getElementById("refresh-all").addEventListener("click", async () => {
    await loadDashboard();
    if (state.santechMonth) {
      await loadSantech(state.santechMonth);
    }
    if (state.cream) {
      await loadCream();
    }
    showToast("새로고침되었습니다.");
  });

  document.getElementById("santech-month").addEventListener("change", (event) => {
    const month = event.target.value;
    setSantechDateBounds(month);
    loadSantech(month);
  });
  document.getElementById("refund-month").addEventListener("change", (event) => {
    const month = event.target.value;
    setSantechDateBounds(month);
    loadSantech(month);
  });

  document.getElementById("santech-form").addEventListener("submit", submitSantech);
  document.getElementById("email-settings-form").addEventListener("submit", submitEmailSettings);
  document.getElementById("daily-email-test").addEventListener("click", sendTestEmail);
  document.getElementById("santech-card-form").addEventListener("submit", submitSantechCard);
  document.getElementById("card-benefit-type").addEventListener("change", updateCardBenefitFields);
  document.getElementById("card-unlimited").addEventListener("change", updateCardBenefitFields);
  document.getElementById("cream-form").addEventListener("submit", submitCream);
  document.getElementById("mile-unit-price").addEventListener("input", renderMileageValue);
  document.getElementById("santech-load-recent").addEventListener("click", loadRecentSantech);
  document.getElementById("dashboard-include-current").addEventListener("change", async (event) => {
    state.includeCurrentMonth = event.target.checked;
    await loadDashboard();
  });
  document.getElementById("refund-simulation-enabled").addEventListener("change", updateRefundSimulationFromControls);
  document.getElementById("refund-sim-shinsegae").addEventListener("input", updateRefundSimulationFromControls);
  document.getElementById("refund-sim-other").addEventListener("input", updateRefundSimulationFromControls);
  document.getElementById("bulk-refund-apply").addEventListener("click", bulkUpdateSantechRefund);
  document.getElementById("bulk-delete-apply").addEventListener("click", bulkDeleteSantech);
  document.getElementById("santech-refund-filter").addEventListener("change", (event) => {
    state.santechRefundFilter = event.target.value;
    renderSantechTransactions(state.santech || { transactions: [], read_only: false });
  });
  document.getElementById("santech-product-filter").addEventListener("change", (event) => {
    const input = event.target.closest("[data-santech-product-filter]");
    if (!input) {
      return;
    }
    if (input.checked) {
      state.santechProductFilters.add(input.value);
    } else {
      state.santechProductFilters.delete(input.value);
    }
    state.santechEditingId = null;
    renderSantechTransactions(state.santech || { transactions: [], read_only: false });
  });
  document.getElementById("santech-select-all").addEventListener("change", (event) => {
    document.querySelectorAll("[data-santech-select]").forEach((input) => {
      input.checked = event.target.checked;
    });
    updateSantechSelectAllState();
  });

  document.querySelectorAll("#santech-form input").forEach((input) => {
    input.addEventListener("input", updateSantechPreview);
  });
  document.querySelector('#santech-form select[name="product"]').addEventListener("change", applySantechProductDefault);
  document.querySelectorAll("#santech-form select").forEach((select) => {
    select.addEventListener("change", updateSantechPreview);
  });
  document.querySelectorAll("#cream-form input").forEach((input) => {
    input.addEventListener("input", updateCreamPreview);
  });

  document.addEventListener("click", (event) => {
    const santechButton = event.target.closest("[data-delete-santech]");
    if (santechButton) {
      deleteSantech(santechButton.dataset.deleteSantech);
      return;
    }
    const santechCardButton = event.target.closest("[data-delete-santech-card]");
    if (santechCardButton) {
      deleteSantechCard(santechCardButton.dataset.deleteSantechCard);
      return;
    }
    const cancelSantechButton = event.target.closest("[data-cancel-santech-edit]");
    if (cancelSantechButton) {
      cancelSantechEdit();
      return;
    }
    const editSantechTarget = event.target.closest("[data-edit-santech]");
    if (editSantechTarget) {
      openSantechEdit(editSantechTarget.dataset.editSantech);
      return;
    }
    const creamButton = event.target.closest("[data-delete-cream]");
    if (creamButton) {
      deleteCream(creamButton.dataset.deleteCream);
    }
  });

  document.addEventListener("change", (event) => {
    const transactionCheckbox = event.target.closest("[data-santech-select]");
    if (transactionCheckbox) {
      updateSantechSelectAllState();
    }
    const refundSimulationCheckbox = event.target.closest("[data-refund-sim-toggle]");
    if (refundSimulationCheckbox) {
      if (refundSimulationCheckbox.checked) {
        state.refundSimulation.excludedIds.delete(refundSimulationCheckbox.dataset.refundSimToggle);
      } else {
        state.refundSimulation.excludedIds.add(refundSimulationCheckbox.dataset.refundSimToggle);
      }
      renderRefundSimulationControls();
      renderSantechTransactions(state.santech || { transactions: [], read_only: false });
    }
  });

  document.addEventListener("submit", (event) => {
    const editForm = event.target.closest("[data-santech-edit-form]");
    if (editForm) {
      event.preventDefault();
      updateSantechTransaction(editForm.dataset.santechEditForm);
    }
  });
}

async function loadInitialApp() {
  setCreamDateDefault();
  updateCardBenefitFields();
  await loadSantechCards();
  updateSantechPreview();
  updateCreamPreview();
  await loadDashboard();
  await loadEmailSettings();
  setupSantechMonths(state.dashboard?.current_month || "2026-07");
  await loadSantech(state.santechMonth);
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  setAuthMode("login");
  state.user = await loadCurrentUser();
  if (!state.user) {
    showAuthView();
    return;
  }
  showAppView();
  await loadInitialApp();
});
