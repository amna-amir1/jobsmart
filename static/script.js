// script.js — JobSmart AI frontend logic

const cvFileInput = document.getElementById("cvFile");
const cvDropzone = document.getElementById("cvDropzone");
const cvFileName = document.getElementById("cvFileName");

const jdPdfFileInput = document.getElementById("jdPdfFile");
const jdPdfDropzone = document.getElementById("jdPdfDropzone");
const jdPdfFileName = document.getElementById("jdPdfFileName");

const jdImageFileInput = document.getElementById("jdImageFile");
const jdImageDropzone = document.getElementById("jdImageDropzone");
const jdImageFileName = document.getElementById("jdImageFileName");

const jdTextArea = document.getElementById("jdText");

const analyzeBtn = document.getElementById("analyzeBtn");
const errorBox = document.getElementById("errorBox");
const loadingBox = document.getElementById("loadingBox");
const loadingText = document.getElementById("loadingText");
const resultsSection = document.getElementById("resultsSection");

let activeJdTab = "paste";
let lastCoverLetter = "";
let lastTailoredCv = "";

// ---------- File picking (click-to-choose) ----------

function wireDropzone(dropzone, input, nameLabel, defaultText) {
  dropzone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    if (input.files && input.files.length > 0) {
      nameLabel.textContent = input.files[0].name;
      dropzone.classList.add("has-file");
    } else {
      nameLabel.textContent = defaultText;
      dropzone.classList.remove("has-file");
    }
  });
}

wireDropzone(cvDropzone, cvFileInput, cvFileName, "Choose your CV (PDF) here");
wireDropzone(jdPdfDropzone, jdPdfFileInput, jdPdfFileName, "Choose the JD PDF here");
wireDropzone(jdImageDropzone, jdImageFileInput, jdImageFileName, "Choose the JD screenshot/image here");

// ---------- JD tabs ----------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    activeJdTab = tab;

    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    document.querySelector(`.tab-content[data-tab-content="${tab}"]`).classList.add("active");
  });
});

// ---------- Simple markdown-ish -> HTML renderer for previews ----------
// Model # / ## / - / plain lines ko readable HTML mein badalta hai.

function renderPreviewHtml(text) {
  const lines = text.split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();

    if (!line) {
      closeList();
      html += "<br>";
      continue;
    }

    if (line.startsWith("# ")) {
      closeList();
      html += `<h3>${escapeHtml(line.slice(2))}</h3>`;
    } else if (line.startsWith("## ")) {
      closeList();
      html += `<h4>${escapeHtml(line.slice(3))}</h4>`;
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${escapeHtml(line.slice(2))}</li>`;
    } else {
      closeList();
      html += `<p>${escapeHtml(line)}</p>`;
    }
  }
  closeList();
  return html;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Score color helper ----------

function scoreColor(score) {
  if (score >= 75) return "#22c55e";
  if (score >= 50) return "#eab308";
  return "#ef4444";
}

// ---------- Error handling ----------

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

// ---------- Analyze ----------

analyzeBtn.addEventListener("click", async () => {
  clearError();
  resultsSection.hidden = true;

  if (!cvFileInput.files || cvFileInput.files.length === 0) {
    showError("Please upload your CV first.");
    return;
  }

  const formData = new FormData();
  formData.append("cv_file", cvFileInput.files[0]);

  if (activeJdTab === "paste") {
    const jdText = jdTextArea.value.trim();
    if (!jdText) {
      showError("Please paste the job description text.");
      return;
    }
    formData.append("jd_text", jdText);
  } else if (activeJdTab === "pdf") {
    if (!jdPdfFileInput.files || jdPdfFileInput.files.length === 0) {
      showError("Please upload the JD PDF.");
      return;
    }
    formData.append("jd_file", jdPdfFileInput.files[0]);
  } else if (activeJdTab === "image") {
    if (!jdImageFileInput.files || jdImageFileInput.files.length === 0) {
      showError("Please upload the JD image/screenshot.");
      return;
    }
    formData.append("jd_image", jdImageFileInput.files[0]);
  }

  analyzeBtn.disabled = true;
  loadingBox.hidden = false;
  loadingText.textContent = "Analyzing your CV and job description, please wait…";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      showError(data.error || data.detail || "Something went wrong. Please try again.");
      return;
    }

    renderResults(data);
  } catch (err) {
    showError("Could not connect to the server: " + err.message);
  } finally {
    analyzeBtn.disabled = false;
    loadingBox.hidden = true;
  }
});

// ---------- Render results ----------

function renderResults(data) {
  const { analysis, cover_letter, tailored_cv } = data;
  lastCoverLetter = cover_letter;
  lastTailoredCv = tailored_cv;

  const score = parseInt(analysis.overall_score, 10) || 0;
  const color = scoreColor(score);

  const scoreNumberEl = document.getElementById("scoreNumber");
  scoreNumberEl.innerHTML = `${score}<span class="score-out-of">/100</span>`;
  scoreNumberEl.style.color = color;

  const verdictEl = document.getElementById("verdictBadge");
  verdictEl.textContent = analysis.verdict || "";
  verdictEl.style.background = `${color}22`;
  verdictEl.style.color = color;

  document.getElementById("recommendationText").textContent = analysis.recommendation || "";

  const strengthsList = document.getElementById("strengthsList");
  strengthsList.innerHTML = "";
  (analysis.strengths || []).forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    strengthsList.appendChild(li);
  });

  const gapsList = document.getElementById("gapsList");
  gapsList.innerHTML = "";
  (analysis.gaps || []).forEach((g) => {
    const li = document.createElement("li");
    li.textContent = g;
    gapsList.appendChild(li);
  });

  document.getElementById("coverLetterPreview").innerHTML = renderPreviewHtml(cover_letter);
  document.getElementById("tailoredCvPreview").innerHTML = renderPreviewHtml(tailored_cv);

  resultsSection.hidden = false;
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

// ---------- Downloads ----------

async function downloadPdf(text, title, filename, button) {
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Downloading...";

  try {
    const formData = new FormData();
    formData.append("text", text);
    formData.append("title", title);
    formData.append("filename", filename);

    const response = await fetch("/api/download-pdf", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Could not download the PDF.");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    showError(err.message);
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

document.getElementById("downloadCoverLetter").addEventListener("click", (e) => {
  downloadPdf(lastCoverLetter, "Cover Letter", "cover_letter.pdf", e.target);
});

document.getElementById("downloadTailoredCv").addEventListener("click", (e) => {
  downloadPdf(lastTailoredCv, "", "tailored_cv.pdf", e.target);
});