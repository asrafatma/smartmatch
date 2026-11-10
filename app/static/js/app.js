/**
 * SmartMatch Client Application
 * Modular Vanilla JavaScript Architecture
 */

// Application State
const state = {
  token: localStorage.getItem("smartmatch_token") || null,
  user: JSON.parse(localStorage.getItem("smartmatch_user") || "null"),
  currentView: "landing",
  selectedReportId: null,
  reports: [],
  matches: [],
  searchDebounceTimer: null
};

// ==========================================
// INITIALIZATION & ROUTING
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
  handleHashChange();
  window.addEventListener("hashchange", handleHashChange);
  loadMetrics();
});

function handleHashChange() {
  const hash = window.location.hash.replace("#", "") || "landing";
  const [view, queryStr] = hash.split("?");
  
  if (queryStr) {
    const params = new URLSearchParams(queryStr);
    if (params.get("id")) {
      state.selectedReportId = params.get("id");
    }
  }

  if (view === "submit-lost") {
    setFormReportType("lost");
    navigate("submit");
  } else if (view === "submit-found") {
    setFormReportType("found");
    navigate("submit");
  } else if (view === "report-detail") {
    navigate("report-detail");
  } else {
    navigate(view);
  }
}

function navigate(viewName) {
  state.currentView = viewName;
  
  // Hide all views
  document.querySelectorAll(".app-view").forEach(el => el.classList.add("hidden"));
  
  // Update nav links
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.remove("active");
    if (link.dataset.view === viewName || 
       (viewName === "submit" && (link.dataset.view === "submit-lost" || link.dataset.view === "submit-found"))) {
      link.classList.add("active");
    }
  });

  // Show target view
  const target = document.getElementById(`view-${viewName}`);
  if (target) {
    target.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // View specific loaders
  if (viewName === "landing") {
    loadMetrics();
  } else if (viewName === "reports") {
    loadReports();
  } else if (viewName === "report-detail" && state.selectedReportId) {
    loadReportDetail(state.selectedReportId);
  } else if (viewName === "claims") {
    loadClaimsReview();
  } else if (viewName === "my-reports") {
    loadMyReports();
  } else if (viewName === "admin") {
    loadAdminDashboard();
  }
}

// ==========================================
// AUTHENTICATION & JUDGE QUICK-LOGIN
// ==========================================
function updateAuthUI() {
  const loggedOutGroup = document.getElementById("auth-logged-out");
  const loggedInGroup = document.getElementById("auth-logged-in");
  const navAvatar = document.getElementById("nav-avatar");
  const navUserName = document.getElementById("nav-user-name");
  const navRoleTag = document.getElementById("nav-role-tag");
  const dropdownUserName = document.getElementById("dropdown-user-name");
  const dropdownUserEmail = document.getElementById("dropdown-user-email");
  const adminLinks = document.querySelectorAll(".admin-only");
  const authLinks = document.querySelectorAll(".auth-required");

  if (state.token && state.user) {
    loggedOutGroup.classList.add("hidden");
    loggedInGroup.classList.remove("hidden");

    const initial = (state.user.name || "U").charAt(0).toUpperCase();
    navAvatar.textContent = initial;
    navUserName.textContent = state.user.name || "User";
    navRoleTag.textContent = state.user.role || "student";
    dropdownUserName.textContent = state.user.name || "User";
    dropdownUserEmail.textContent = state.user.email || "";

    authLinks.forEach(el => el.classList.remove("hidden"));
    if (state.user.role === "admin") {
      adminLinks.forEach(el => el.classList.remove("hidden"));
    } else {
      adminLinks.forEach(el => el.classList.add("hidden"));
    }
  } else {
    loggedOutGroup.classList.remove("hidden");
    loggedInGroup.classList.add("hidden");
    authLinks.forEach(el => el.classList.add("hidden"));
    adminLinks.forEach(el => el.classList.add("hidden"));
  }
}

function toggleUserDropdown() {
  const menu = document.getElementById("user-dropdown");
  menu.classList.toggle("hidden");
}

document.addEventListener("click", (e) => {
  const pill = document.querySelector(".user-pill");
  const menu = document.getElementById("user-dropdown");
  if (menu && pill && !pill.contains(e.target) && !menu.contains(e.target)) {
    menu.classList.add("hidden");
  }
});

function openAuthModal(mode = "login") {
  switchAuthTab(mode);
  document.getElementById("auth-modal").classList.remove("hidden");
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById("tab-auth-login");
  const regTab = document.getElementById("tab-auth-register");
  const loginForm = document.getElementById("login-form");
  const regForm = document.getElementById("register-form");
  const title = document.getElementById("auth-modal-title");

  if (tab === "login") {
    loginTab.classList.add("active");
    regTab.classList.remove("active");
    loginForm.classList.remove("hidden");
    regForm.classList.add("hidden");
    title.textContent = "Sign In to SmartMatch";
  } else {
    regTab.classList.add("active");
    loginTab.classList.remove("active");
    regForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
    title.textContent = "Create Student Account";
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  await performLogin(email, password);
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const role = document.getElementById("reg-role").value;

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, role })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Registration failed", "error");
      return;
    }
    saveAuth(data.data.token, data.data.user);
    closeModal("auth-modal");
    showToast(`Welcome to SmartMatch, ${data.data.user.name}!`, "success");
  } catch (err) {
    showToast("Network error during registration", "error");
  }
}

async function quickLogin(email, password) {
  await performLogin(email, password);
}

async function performLogin(email, password) {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Authentication failed", "error");
      return;
    }
    saveAuth(data.data.token, data.data.user);
    closeModal("auth-modal");
    showToast(`Logged in as ${data.data.user.name} (${data.data.user.role})`, "success");
    // Reload active view
    navigate(state.currentView);
  } catch (err) {
    showToast("Server connection error during login", "error");
  }
}

function saveAuth(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("smartmatch_token", token);
  localStorage.setItem("smartmatch_user", JSON.stringify(user));
  updateAuthUI();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("smartmatch_token");
  localStorage.removeItem("smartmatch_user");
  updateAuthUI();
  showToast("Logged out successfully", "info");
  navigate("landing");
}

function authHeaders(isJson = true) {
  const h = {};
  if (state.token) {
    h["Authorization"] = `Bearer ${state.token}`;
  }
  if (isJson) {
    h["Content-Type"] = "application/json";
  }
  return h;
}

// ==========================================
// METRICS (HERO SECTION)
// ==========================================
async function loadMetrics() {
  try {
    const res = await fetch("/api/reports?limit=100");
    const data = await res.json();
    if (res.ok && data.data) {
      const items = data.data.items || [];
      const lost = items.filter(i => i.report_type === "lost").length;
      const found = items.filter(i => i.report_type === "found").length;
      const resolved = items.filter(i => i.status === "resolved").length;
      const claims = items.filter(i => i.status === "claim_pending").length;

      document.getElementById("metric-lost").textContent = lost;
      document.getElementById("metric-found").textContent = found;
      document.getElementById("metric-resolved").textContent = resolved;
      document.getElementById("metric-claims").textContent = claims;
    }
  } catch (err) {
    console.warn("Metrics load notice:", err);
  }
}

// ==========================================
// REPORT SUBMISSION & IMAGE PREVIEW
// ==========================================
function setFormReportType(type) {
  document.getElementById("form-report-type").value = type;
  const btnLost = document.getElementById("btn-toggle-lost");
  const btnFound = document.getElementById("btn-toggle-found");
  const title = document.getElementById("submit-form-title");

  if (type === "lost") {
    btnLost.classList.add("active");
    btnFound.classList.remove("active");
    title.textContent = "Submit Lost Item Report";
  } else {
    btnFound.classList.add("active");
    btnLost.classList.remove("active");
    title.textContent = "Submit Found Item Report";
  }
}

function previewUploadImage(input) {
  if (input.files && input.files[0]) {
    const file = input.files[0];
    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById("preview-img").src = e.target.result;
      document.getElementById("dropzone-placeholder").classList.add("hidden");
      document.getElementById("dropzone-preview").classList.remove("hidden");
    };
    reader.readAsDataURL(file);
  }
}

function removeUploadImage(e) {
  e.stopPropagation();
  const input = document.getElementById("form-image-input");
  input.value = "";
  document.getElementById("preview-img").src = "";
  document.getElementById("dropzone-preview").classList.add("hidden");
  document.getElementById("dropzone-placeholder").classList.remove("hidden");
}

async function handleReportSubmit(e) {
  e.preventDefault();

  if (!state.token) {
    showToast("Please sign in to submit a report", "info");
    openAuthModal("login");
    return;
  }

  const imageInput = document.getElementById("form-image-input");
  if (!imageInput.files || !imageInput.files[0]) {
    showToast("A valid photograph is mandatory for report submission.", "error");
    return;
  }

  const submitBtn = document.getElementById("btn-submit-report");
  const spinner = document.getElementById("submit-btn-spinner");
  const btnText = document.getElementById("submit-btn-text");

  submitBtn.disabled = true;
  spinner.classList.remove("hidden");
  btnText.textContent = "Analyzing Image & Processing AI...";

  const formData = new FormData();
  formData.append("report_type", document.getElementById("form-report-type").value);
  formData.append("title", document.getElementById("form-title").value.trim());
  formData.append("category", document.getElementById("form-category").value);
  formData.append("incident_date", document.getElementById("form-date").value);
  formData.append("location", document.getElementById("form-location").value.trim());
  formData.append("description", document.getElementById("form-description").value.trim());
  formData.append("image", imageInput.files[0]);

  // Optional custom attributes overrides
  const customAttrs = {
    color: document.getElementById("attr-color").value.split(",").map(s => s.trim()).filter(Boolean),
    material: document.getElementById("attr-material").value.split(",").map(s => s.trim()).filter(Boolean),
    brand_or_logo: document.getElementById("attr-brand").value.split(",").map(s => s.trim()).filter(Boolean),
    distinctive_features: document.getElementById("attr-features").value.split(",").map(s => s.trim()).filter(Boolean)
  };
  if (Object.values(customAttrs).some(arr => arr.length > 0)) {
    formData.append("attributes", JSON.stringify(customAttrs));
  }

  try {
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${state.token}`
      },
      body: formData
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to submit report", "error");
      return;
    }

    showToast("Report submitted & AI attributes extracted successfully!", "success");
    document.getElementById("report-form").reset();
    removeUploadImage(new Event("reset"));

    // Navigate to the newly created report detail & matches
    const newId = data.data.id;
    state.selectedReportId = newId;
    window.location.hash = `#report-detail?id=${newId}`;
  } catch (err) {
    showToast("Server communication error while saving report", "error");
  } finally {
    submitBtn.disabled = false;
    spinner.classList.add("hidden");
    btnText.textContent = "Submit Report & Run AI Extraction";
  }
}

// ==========================================
// REPORTS CATALOG & FILTERING
// ==========================================
function debounceSearch() {
  clearTimeout(state.searchDebounceTimer);
  state.searchDebounceTimer = setTimeout(() => {
    loadReports();
  }, 350);
}

async function loadReports() {
  const search = document.getElementById("report-search-input").value.trim();
  const reportType = document.getElementById("filter-type").value;
  const category = document.getElementById("filter-category").value;
  const status = document.getElementById("filter-status").value;

  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (reportType) params.append("report_type", reportType);
  if (category) params.append("category", category);
  if (status) params.append("status", status);

  try {
    const res = await fetch(`/api/reports?${params.toString()}`);
    const data = await res.json();
    const grid = document.getElementById("reports-grid");
    const emptyState = document.getElementById("reports-empty");

    if (!res.ok || !data.data || data.data.items.length === 0) {
      grid.innerHTML = "";
      emptyState.classList.remove("hidden");
      return;
    }

    emptyState.classList.add("hidden");
    state.reports = data.data.items;
    grid.innerHTML = data.data.items.map(r => renderReportCard(r)).join("");
  } catch (err) {
    showToast("Unable to fetch campus reports", "error");
  }
}

function renderReportCard(report) {
  const isLost = report.report_type === "lost";
  const badgeClass = isLost ? "badge-lost" : "badge-found";
  const typeText = isLost ? "LOST" : "FOUND";
  
  // Format color & brand tags
  const colors = report.attributes?.color || [];
  const brands = report.attributes?.brand_or_logo || [];
  const tags = [...colors, ...brands].slice(0, 3);

  return `
    <div class="report-card" onclick="viewReportDetail('${report.id}')">
      <div class="report-img-wrap">
        <img src="${report.image_path}" alt="${escapeHtml(report.title)}" onerror="this.src='/static/images/placeholder.png'">
        <span class="report-badge-type ${badgeClass}">${typeText}</span>
      </div>
      <div class="report-content">
        <h4 class="report-title">${escapeHtml(report.title)}</h4>
        <div class="report-meta">
          <span>📍 ${escapeHtml(report.location || "Campus")}</span>
          <span>📅 ${escapeHtml(report.incident_date || "Recent")}</span>
        </div>
        <p class="report-desc-preview">${escapeHtml(report.description || "")}</p>
        <div class="report-tags">
          <span class="tag-pill">📁 ${escapeHtml(report.category || "other")}</span>
          ${tags.map(t => `<span class="tag-pill">${escapeHtml(t)}</span>`).join("")}
        </div>
        <button class="btn btn-outline btn-xs w-100" style="margin-top:auto">View Details & Matches &rarr;</button>
      </div>
    </div>
  `;
}

function viewReportDetail(reportId) {
  state.selectedReportId = reportId;
  window.location.hash = `#report-detail?id=${reportId}`;
}

// ==========================================
// REPORT DETAIL & DETERMINISTIC MATCHES
// ==========================================
async function loadReportDetail(reportId) {
  try {
    const res = await fetch(`/api/reports/${reportId}`, {
      headers: authHeaders(false)
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Report not found", "error");
      navigate("reports");
      return;
    }

    const report = data.data;
    renderReportDetailCard(report);
    loadMatchesForReport(reportId);
  } catch (err) {
    showToast("Error loading report details", "error");
  }
}

function renderReportDetailCard(r) {
  const detailContainer = document.getElementById("detail-card");
  const actionsContainer = document.getElementById("detail-actions");
  const isLost = r.report_type === "lost";
  const badgeClass = isLost ? "badge-lost" : "badge-found";
  const typeText = isLost ? "LOST ITEM" : "FOUND ITEM";

  // Actions
  let actionButtons = "";
  if (!isLost && state.user && state.user.id !== r.user_id && r.status === "active") {
    actionButtons += `
      <button class="btn btn-primary btn-sm" onclick="openClaimModal('${r.id}')">
        🛡️ Submit Ownership Claim
      </button>
    `;
  }
  actionsContainer.innerHTML = actionButtons;

  const colors = (r.attributes?.color || []).join(", ") || "Unknown";
  const materials = (r.attributes?.material || []).join(", ") || "Not specified";
  const brands = (r.attributes?.brand_or_logo || []).join(", ") || "None / Unbranded";
  const features = (r.attributes?.distinctive_features || []).join(", ") || "None noted";
  const unknowns = (r.unknowns || []).join("; ") || "None";

  detailContainer.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span class="report-badge-type ${badgeClass}">${typeText}</span>
      <span class="badge badge-info">Status: ${escapeHtml(r.status)}</span>
    </div>

    <img src="${r.image_path}" class="detail-img" alt="${escapeHtml(r.title)}">

    <div>
      <h2>${escapeHtml(r.title)}</h2>
      <div class="report-meta" style="margin-top:0.5rem">
        <span>📍 <strong>Location:</strong> ${escapeHtml(r.location)}</span>
        <span>📅 <strong>Incident Date:</strong> ${escapeHtml(r.incident_date)}</span>
        <span>👤 <strong>Reported By:</strong> ${escapeHtml(r.submitter_name || "Campus Member")}</span>
        <span>🔒 <strong>Contact:</strong> ${escapeHtml(r.submitter_email)}</span>
      </div>
    </div>

    <div class="detail-section">
      <h4>Item Description</h4>
      <p class="text-sm">${escapeHtml(r.description)}</p>
    </div>

    <div class="detail-section">
      <h4>AI Extracted & Confirmed Attributes</h4>
      <div class="breakdown-grid">
        <div class="breakdown-item"><span>Category:</span> <strong>${escapeHtml(r.category)}</strong></div>
        <div class="breakdown-item"><span>Color(s):</span> <strong>${escapeHtml(colors)}</strong></div>
        <div class="breakdown-item"><span>Material:</span> <strong>${escapeHtml(materials)}</strong></div>
        <div class="breakdown-item"><span>Brand/Logo:</span> <strong>${escapeHtml(brands)}</strong></div>
        <div class="breakdown-item"><span>Features:</span> <strong>${escapeHtml(features)}</strong></div>
        <div class="breakdown-item"><span>AI Extraction:</span> <strong>${escapeHtml(r.ai_status || "manual")}</strong></div>
      </div>
    </div>

    <div class="detail-section">
      <h4>Observed Unknowns & Ambiguities</h4>
      <p class="text-muted text-xs">${escapeHtml(unknowns)}</p>
    </div>
  `;
}

async function loadMatchesForReport(reportId) {
  const matchesList = document.getElementById("matches-list");
  const emptyState = document.getElementById("matches-empty");
  matchesList.innerHTML = `<p class="text-muted text-sm">Evaluating deterministic match scores...</p>`;

  try {
    const res = await fetch(`/api/matches/${reportId}`);
    const data = await res.json();
    if (!res.ok || !data.data || data.data.length === 0) {
      matchesList.innerHTML = "";
      emptyState.classList.remove("hidden");
      return;
    }

    emptyState.classList.add("hidden");
    state.matches = data.data;
    matchesList.innerHTML = data.data.map(m => renderMatchCard(m)).join("");
  } catch (err) {
    matchesList.innerHTML = `<p class="text-danger text-sm">Error calculating matches.</p>`;
  }
}

function refreshMatches() {
  if (state.selectedReportId) {
    loadMatchesForReport(state.selectedReportId);
  }
}

function renderMatchCard(m) {
  const cand = m.candidate_report;
  const score = m.score;
  let scoreClass = "low";
  let cardBorderClass = "low-match";
  let labelBadgeClass = "badge-low";

  if (score >= 70) {
    scoreClass = "strong";
    cardBorderClass = "strong-match";
    labelBadgeClass = "badge-strong";
  } else if (score >= 40) {
    scoreClass = "possible";
    cardBorderClass = "possible-match";
    labelBadgeClass = "badge-possible";
  }

  // Claim button if candidate is a found item and viewer is not the submitter
  let claimBtn = "";
  if (cand.report_type === "found" && state.user && state.user.id !== cand.user_id) {
    claimBtn = `
      <button class="btn btn-primary btn-xs" onclick="openClaimModal('${cand.id}')">
        Claim Item
      </button>
    `;
  }

  return `
    <div class="match-card ${cardBorderClass}">
      <div class="match-header">
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <img src="${cand.image_path}" style="width:52px; height:52px; object-fit:cover; border-radius:6px;">
          <div>
            <h4 style="font-size:0.95rem; margin-bottom:0.15rem;">${escapeHtml(cand.title)}</h4>
            <span class="text-xs text-muted">📍 ${escapeHtml(cand.location)} &bull; 📅 ${escapeHtml(cand.incident_date)}</span>
          </div>
        </div>
        <div style="text-align:right;">
          <div class="score-badge ${scoreClass}">${score}<span style="font-size:0.8rem; font-weight:500;">/100</span></div>
          <span class="score-label ${labelBadgeClass}">${escapeHtml(m.label)}</span>
        </div>
      </div>

      <!-- Score Breakdown -->
      <div class="breakdown-grid">
        <div class="breakdown-item"><span>Category:</span> <strong>${m.score_breakdown.category || 0}/20</strong></div>
        <div class="breakdown-item"><span>Object:</span> <strong>${m.score_breakdown.object_type || 0}/15</strong></div>
        <div class="breakdown-item"><span>Brand:</span> <strong>${m.score_breakdown.brand_or_logo || 0}/15</strong></div>
        <div class="breakdown-item"><span>Color:</span> <strong>${m.score_breakdown.color || 0}/15</strong></div>
        <div class="breakdown-item"><span>Material:</span> <strong>${m.score_breakdown.material_and_shape || 0}/10</strong></div>
        <div class="breakdown-item"><span>Features:</span> <strong>${m.score_breakdown.distinctive_features || 0}/15</strong></div>
        <div class="breakdown-item"><span>Location:</span> <strong>${m.score_breakdown.location || 0}/5</strong></div>
        <div class="breakdown-item"><span>Date:</span> <strong>${m.score_breakdown.date || 0}/5</strong></div>
      </div>

      <!-- Explanations -->
      <div class="match-explanations">
        <div>
          ${m.matched_attributes.map(a => `<span class="pill-match overlap">✓ ${escapeHtml(a)}</span>`).join("")}
        </div>
        <div>
          ${m.conflicts.map(c => `<span class="pill-match conflict">✗ ${escapeHtml(c)}</span>`).join("")}
        </div>
        <div>
          ${m.unknowns.map(u => `<span class="pill-match unknown">? ${escapeHtml(u)}</span>`).join("")}
        </div>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.25rem;">
        <button class="btn btn-outline btn-xs" onclick="viewReportDetail('${cand.id}')">View Full Report</button>
        ${claimBtn}
      </div>
    </div>
  `;
}

// ==========================================
// CLAIMS SUBMISSION & REVIEW
// ==========================================
function openClaimModal(reportId) {
  if (!state.token) {
    showToast("Please sign in to submit an ownership claim", "info");
    openAuthModal("login");
    return;
  }
  document.getElementById("claim-report-id").value = reportId;
  document.getElementById("claim-answers").value = "";
  document.getElementById("claim-modal").classList.remove("hidden");
}

async function handleClaimSubmit(e) {
  e.preventDefault();
  const reportId = document.getElementById("claim-report-id").value;
  const answers = document.getElementById("claim-answers").value.trim();

  try {
    const res = await fetch("/api/claims", {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({
        report_id: reportId,
        verification_answers: answers
      })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Claim submission failed", "error");
      return;
    }

    closeModal("claim-modal");
    showToast("Ownership claim submitted! The finder will review your verification details.", "success");
    navigate("my-reports");
  } catch (err) {
    showToast("Network error submitting claim", "error");
  }
}

async function loadClaimsReview() {
  const list = document.getElementById("claims-review-list");
  const empty = document.getElementById("claims-review-empty");
  const countBadge = document.getElementById("pending-claims-count");

  try {
    const res = await fetch("/api/claims?scope=review", {
      headers: authHeaders(false)
    });
    const data = await res.json();
    if (!res.ok || !data.data || data.data.length === 0) {
      list.innerHTML = "";
      empty.classList.remove("hidden");
      countBadge.textContent = "0 Pending";
      return;
    }

    empty.classList.add("hidden");
    countBadge.textContent = `${data.data.length} Pending`;
    list.innerHTML = data.data.map(c => renderClaimReviewCard(c)).join("");
  } catch (err) {
    showToast("Failed to load claims for review", "error");
  }
}

function renderClaimReviewCard(c) {
  return `
    <div class="card mb-4" style="border-left: 4px solid var(--warning)">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
        <div>
          <h4 style="font-size:1.05rem;">Claim on: ${escapeHtml(c.report_title || "Found Item")}</h4>
          <span class="text-xs text-muted">Claim ID: ${c.id} &bull; Submitted: ${new Date(c.created_at).toLocaleString()}</span>
        </div>
        <span class="badge badge-warning">Attempts: ${c.attempt_count}/3</span>
      </div>

      <div style="background:var(--bg); padding:0.85rem; border-radius:6px; margin-bottom:1rem;">
        <strong class="text-xs" style="display:block; margin-bottom:0.35rem; color:var(--navy);">
          🔒 Private Verification Evidence:
        </strong>
        <p class="text-sm" style="white-space:pre-wrap;">${escapeHtml(c.verification_answers)}</p>
      </div>

      <div style="display:flex; gap:0.5rem; justify-content:flex-end;">
        <button class="btn btn-danger btn-sm" onclick="reviewClaimAction('${c.id}', 'rejected')">
          Reject Claim
        </button>
        <button class="btn btn-primary btn-sm" onclick="reviewClaimAction('${c.id}', 'approved')">
          ✓ Approve Ownership
        </button>
      </div>
    </div>
  `;
}

async function reviewClaimAction(claimId, action) {
  const notes = prompt(`Optional internal note for ${action} claim:`, "");
  try {
    const res = await fetch(`/api/claims/${claimId}`, {
      method: "PATCH",
      headers: authHeaders(true),
      body: JSON.stringify({ action, notes })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Review action failed", "error");
      return;
    }

    showToast(`Claim has been ${action} successfully.`, "success");
    loadClaimsReview();
  } catch (err) {
    showToast("Error processing claim review", "error");
  }
}

// ==========================================
// MY REPORTS & CLAIMS
// ==========================================
function switchMyTab(tab) {
  const tabs = document.querySelectorAll(".tabs-container .tab-btn");
  tabs.forEach(t => t.classList.remove("active"));
  
  const repTab = document.getElementById("my-items-tab");
  const claimTab = document.getElementById("my-claims-tab");

  if (tab === "reports") {
    tabs[0].classList.add("active");
    repTab.classList.remove("hidden");
    claimTab.classList.add("hidden");
    loadMyReports();
  } else {
    tabs[1].classList.add("active");
    claimTab.classList.remove("hidden");
    repTab.classList.add("hidden");
    loadMyClaims();
  }
}

async function loadMyReports() {
  if (!state.user) return;
  const grid = document.getElementById("my-reports-grid");
  const empty = document.getElementById("my-reports-empty");

  try {
    const res = await fetch(`/api/reports?user_id=${state.user.id}&limit=50`, {
      headers: authHeaders(false)
    });
    const data = await res.json();
    if (!res.ok || !data.data || data.data.items.length === 0) {
      grid.innerHTML = "";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    grid.innerHTML = data.data.items.map(r => renderReportCard(r)).join("");
  } catch (err) {
    showToast("Error loading your reports", "error");
  }
}

async function loadMyClaims() {
  const list = document.getElementById("my-claims-list");
  const empty = document.getElementById("my-claims-empty");

  try {
    const res = await fetch("/api/claims?scope=mine", {
      headers: authHeaders(false)
    });
    const data = await res.json();
    if (!res.ok || !data.data || data.data.length === 0) {
      list.innerHTML = "";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    list.innerHTML = data.data.map(c => `
      <div class="card mb-2">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong>Claim on Report ID: ${c.report_id}</strong>
            <div class="text-xs text-muted">Submitted: ${new Date(c.created_at).toLocaleDateString()}</div>
          </div>
          <span class="badge ${c.status === 'approved' ? 'badge-strong' : (c.status === 'rejected' ? 'badge-danger' : 'badge-possible')}">
            ${c.status.toUpperCase()}
          </span>
        </div>
        ${c.status === 'approved' ? `
          <div class="alert alert-success text-xs" style="margin-top:0.75rem;">
            🎉 Ownership Approved! View the report or contact desk for item collection.
          </div>
        ` : ''}
      </div>
    `).join("");
  } catch (err) {
    showToast("Error loading your submitted claims", "error");
  }
}

// ==========================================
// ADMIN DASHBOARD
// ==========================================
async function loadAdminDashboard() {
  if (!state.user || state.user.role !== "admin") {
    showToast("Administrator privileges required", "error");
    navigate("landing");
    return;
  }

  try {
    const res = await fetch("/api/admin/dashboard", {
      headers: authHeaders(false)
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Failed to load admin stats", "error");
      return;
    }

    const stats = data.data.stats;
    document.getElementById("admin-stat-users").textContent = stats.total_users;
    document.getElementById("admin-stat-lost").textContent = stats.total_lost;
    document.getElementById("admin-stat-found").textContent = stats.total_found;
    document.getElementById("admin-stat-claims").textContent = stats.pending_claims;

    // AI Logs Table
    const tbody = document.getElementById("admin-ai-logs-tbody");
    const logs = data.data.recent_ai_logs || [];
    tbody.innerHTML = logs.map(l => `
      <tr>
        <td>${new Date(l.created_at).toLocaleTimeString()}</td>
        <td><code>${escapeHtml(l.model_name)}</code></td>
        <td><span class="badge ${l.status === 'completed' ? 'badge-strong' : 'badge-possible'}">${escapeHtml(l.status)}</span></td>
        <td><small>${escapeHtml(l.report_id || 'N/A')}</small></td>
        <td>${escapeHtml(l.error_type || 'None')}</td>
      </tr>
    `).join("");
  } catch (err) {
    showToast("Error retrieving administration metrics", "error");
  }
}

// ==========================================
// UTILITY FUNCTIONS & TOASTS
// ==========================================
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

function handleModalOverlayClick(e, modalId) {
  if (e.target.id === modalId) {
    closeModal(modalId);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
