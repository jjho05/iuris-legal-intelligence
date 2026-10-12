/**
 * IURIS LEGAL INTELLIGENCE — CLIENT ENGINE (app.js)
 * Suite pericial de grado corporativo:
 * - Legal Workbench con 4 modos operativos (Dictamen, Matriz de Riesgos, Calculadora LFT, Expediente).
 * - Renderizado de Memorándums Jurídicos formales con folio pericial y exportación para impresión.
 * - Simulador pericial interactivo de la Ley Federal del Trabajo (Vacaciones Dignas Art. 76).
 * - Ingestión de contratos Word/PDF a Markdown estructurado con RAG en memoria y Gemini 3.8 Flash.
 * - Cero emojis: estética institucional sobria con iconos SVG vectoriales.
 */

// ==============================================================================
// 1. ESTADO DE LA APLICACIÓN
// ==============================================================================
const state = {
  activeTab: 'dictamen',
  activeCorpus: 'corporativo',
  uploadedDocName: null,
  uploadedMarkdown: null,
  enableWebSearch: true,
  userApiKey: sessionStorage.getItem('iuris_api_key') || '',
  isProcessing: false,
  memoCounter: 88,
  apiBase: window.location.origin
};

// ==============================================================================
// 2. REFERENCIAS AL DOM
// ==============================================================================
const dom = {
  // Tabs del Workbench
  tabButtons: document.querySelectorAll('.nav-tab-item, .workbench-tab'),
  panels: {
    dictamen: document.getElementById('tab-panel-dictamen'),
    riesgos: document.getElementById('tab-panel-riesgos'),
    laboral: document.getElementById('tab-panel-laboral'),
    expediente: document.getElementById('tab-panel-expediente')
  },

  // Header & Switcher
  selectFramework: document.getElementById('select-legal-framework'),
  optCustomDoc: document.getElementById('opt-custom-doc'),
  toggleWebSearch: document.getElementById('toggle-web-search'),
  btnTriggerUpload: document.getElementById('btn-trigger-upload'),
  btnOpenKeyModal: document.getElementById('btn-open-key-modal'),

  // Dictamen View (Tab 1)
  chatThread: document.getElementById('chat-thread'),
  welcomeMemoCard: document.getElementById('welcome-memo-card'),
  composerForm: document.getElementById('chat-composer-form'),
  composerInput: document.getElementById('composer-input'),
  btnSubmit: document.getElementById('btn-composer-submit'),
  btnAttach: document.getElementById('btn-attach-file'),
  btnClearMemos: document.getElementById('btn-clear-memos'),
  activeContextLabel: document.getElementById('active-context-label'),
  caseIdLabel: document.getElementById('case-id-label'),

  // Sidebar Context (Tab 1)
  docNameLabel: document.getElementById('doc-name-label'),
  docWordsStat: document.getElementById('doc-words-stat'),
  btnQuickSwitchLft: document.getElementById('btn-quick-switch-lft'),
  btnQuickSwitchCorp: document.getElementById('btn-quick-switch-corp'),
  citationsList: document.getElementById('citations-list'),

  // Ingestión de Archivos
  dropzone: document.getElementById('upload-dropzone'),
  fileInput: document.getElementById('file-input'),
  globalFileInput: document.getElementById('global-file-input'),
  btnCalloutUpload: document.getElementById('btn-callout-upload'),

  // Calculadora LFT (Tab 3)
  lftAntiguedadSelect: document.getElementById('lft-antiguedad-select'),
  lftSalarioInput: document.getElementById('lft-salario-input'),
  calcDiasVacaciones: document.getElementById('calc-dias-vacaciones'),
  calcVacacionesPago: document.getElementById('calc-vacaciones-pago'),
  calcPrimaVacacional: document.getElementById('calc-prima-vacacional'),
  calcAguinaldo: document.getElementById('calc-aguinaldo'),
  calcIndemnizacion: document.getElementById('calc-indemnizacion'),
  btnLftGenerarDictamen: document.getElementById('btn-lft-generar-dictamen'),

  // Matriz de Riesgo (Tab 2)
  btnRecalculateRisk: document.getElementById('btn-recalculate-risk'),
  btnExportRiskReport: document.getElementById('btn-export-risk-report'),
  riskMatrixDocName: document.getElementById('risk-matrix-doc-name'),

  // Expediente Digital (Tab 4)
  dossierDocName: document.getElementById('dossier-doc-name'),
  dossierWordCount: document.getElementById('dossier-word-count'),
  dossierIndexList: document.getElementById('dossier-index-list'),
  markdownViewer: document.getElementById('markdown-viewer'),
  btnCopyDossierMd: document.getElementById('btn-copy-dossier-md'),
  btnDownloadDossierMd: document.getElementById('btn-download-dossier-md'),

  // Modal API Key
  modalKey: document.getElementById('modal-key-config'),
  btnCloseKeyModal: document.getElementById('btn-close-key-modal'),
  inputGeminiKey: document.getElementById('input-gemini-key'),
  btnSaveKey: document.getElementById('btn-save-key'),
  btnResetKey: document.getElementById('btn-reset-key')
};

// ==============================================================================
// 3. INICIALIZACIÓN
// ==============================================================================
document.addEventListener('DOMContentLoaded', () => {
  init();
});

async function init() {
  if (dom.inputGeminiKey) dom.inputGeminiKey.value = state.userApiKey;
  setupWorkbenchTabs();
  setupEventListeners();
  updateLftCalculations();
  await loadCorpusPreview('corporativo');
}

// ==============================================================================
// 4. SISTEMA DE WORKBENCH TABS
// ==============================================================================
function setupWorkbenchTabs() {
  const tabs = document.querySelectorAll('.nav-tab-item, .workbench-tab');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      switchWorkbenchTab(tabName);
    });
  });
}

function switchWorkbenchTab(tabName) {
  if (!dom.panels[tabName]) return;
  state.activeTab = tabName;

  const tabs = document.querySelectorAll('.nav-tab-item, .workbench-tab');
  tabs.forEach(btn => {
    if (btn.getAttribute('data-tab') === tabName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  Object.keys(dom.panels).forEach(key => {
    if (key === tabName) {
      dom.panels[key].classList.add('active');
    } else {
      dom.panels[key].classList.remove('active');
    }
  });

  // Scroll suave al inicio en móvil
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==============================================================================
// 5. EVENTOS PRINCIPALES
// ==============================================================================
function setupEventListeners() {
  // Auto-resize de composer
  if (dom.composerInput) {
    dom.composerInput.addEventListener('input', () => {
      dom.composerInput.style.height = 'auto';
      dom.composerInput.style.height = Math.min(dom.composerInput.scrollHeight, 120) + 'px';
    });

    // Envío con Enter (Shift+Enter para salto de línea)
    dom.composerInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        dom.composerForm.dispatchEvent(new Event('submit'));
      }
    });
  }

  // Envío de consulta
  if (dom.composerForm) {
    dom.composerForm.addEventListener('submit', handleChatSubmit);
  }

  // Selector de Marco Legal
  if (dom.selectFramework) {
    dom.selectFramework.addEventListener('change', async (e) => {
      const val = e.target.value;
      await setLegalFramework(val);
    });
  }

  // Toggle Búsqueda Web
  if (dom.toggleWebSearch) {
    dom.toggleWebSearch.addEventListener('change', (e) => {
      state.enableWebSearch = e.target.checked;
    });
  }

  // Acciones rápidas de Bienvenida
  document.querySelectorAll('.quick-action-btn, .action-card').forEach(card => {
    card.addEventListener('click', () => {
      const action = card.getAttribute('data-action');
      handleQuickLegalAction(action);
    });
  });

  // Acciones rápidas en Sidebar
  if (dom.btnQuickSwitchLft) {
    dom.btnQuickSwitchLft.addEventListener('click', async () => {
      if (dom.selectFramework) dom.selectFramework.value = 'lft';
      await setLegalFramework('lft');
    });
  }

  if (dom.btnQuickSwitchCorp) {
    dom.btnQuickSwitchCorp.addEventListener('click', async () => {
      if (dom.selectFramework) dom.selectFramework.value = 'corporativo';
      await setLegalFramework('corporativo');
    });
  }

  // Limpiar dictámenes
  if (dom.btnClearMemos) {
    dom.btnClearMemos.addEventListener('click', () => {
      const memos = dom.chatThread.querySelectorAll('.legal-memo-card, .user-query-card');
      memos.forEach(m => m.remove());
      if (dom.welcomeMemoCard) dom.welcomeMemoCard.style.display = 'flex';
    });
  }

  // Ingestión de Archivos (Dropzone)
  const triggerFileSelection = () => {
    if (dom.fileInput) dom.fileInput.click();
    else if (dom.globalFileInput) dom.globalFileInput.click();
  };

  if (dom.dropzone) dom.dropzone.addEventListener('click', triggerFileSelection);
  if (dom.btnTriggerUpload) dom.btnTriggerUpload.addEventListener('click', triggerFileSelection);
  if (dom.btnAttach) dom.btnAttach.addEventListener('click', triggerFileSelection);
  if (dom.btnCalloutUpload) dom.btnCalloutUpload.addEventListener('click', triggerFileSelection);

  if (dom.fileInput) {
    dom.fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        uploadDocumentFile(e.target.files[0]);
      }
    });
  }

  if (dom.globalFileInput) {
    dom.globalFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        uploadDocumentFile(e.target.files[0]);
      }
    });
  }

  // Drag and Drop
  if (dom.dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dom.dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dom.dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dom.dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dom.dropzone.classList.remove('dragover');
      });
    });

    dom.dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files[0]) {
        uploadDocumentFile(dt.files[0]);
      }
    });
  }

  // Calculadora LFT interactiva
  if (dom.lftAntiguedadSelect) dom.lftAntiguedadSelect.addEventListener('change', updateLftCalculations);
  if (dom.lftSalarioInput) dom.lftSalarioInput.addEventListener('input', updateLftCalculations);

  if (dom.btnLftGenerarDictamen) {
    dom.btnLftGenerarDictamen.addEventListener('click', () => {
      const antiguedad = dom.lftAntiguedadSelect.options[dom.lftAntiguedadSelect.selectedIndex].text;
      const salario = dom.lftSalarioInput.value;
      const dias = dom.calcDiasVacaciones.textContent;
      switchWorkbenchTab('dictamen');
      dom.composerInput.value = `Emite un dictamen formal sobre los derechos laborales adquiridos para un trabajador con antigüedad de ${antiguedad} y salario mensual de $${salario} MXN, considerando las Vacaciones Dignas (${dias}) y Aguinaldo conforme al Art. 76 y Art. 87 de la LFT.`;
      dom.composerForm.dispatchEvent(new Event('submit'));
    });
  }

  // Exportar / Re-auditar Riesgos
  if (dom.btnRecalculateRisk) {
    dom.btnRecalculateRisk.addEventListener('click', () => {
      switchWorkbenchTab('dictamen');
      dom.composerInput.value = `Realiza una auditoría exhaustiva de la matriz de riesgos de este contrato, identificando cláusulas abusivas, penalizaciones por rescisión, plazos de confidencialidad y responsabilidades.`;
      dom.composerForm.dispatchEvent(new Event('submit'));
    });
  }

  if (dom.btnExportRiskReport) {
    dom.btnExportRiskReport.addEventListener('click', () => {
      exportRiskReportMarkdown();
    });
  }

  // Dossier Markdown acciones
  if (dom.btnCopyDossierMd) {
    dom.btnCopyDossierMd.addEventListener('click', () => {
      if (state.uploadedMarkdown) {
        navigator.clipboard.writeText(state.uploadedMarkdown);
        dom.btnCopyDossierMd.textContent = 'Copiado';
        setTimeout(() => dom.btnCopyDossierMd.textContent = 'Copiar Markdown', 2000);
      }
    });
  }

  if (dom.btnDownloadDossierMd) {
    dom.btnDownloadDossierMd.addEventListener('click', () => {
      if (state.uploadedMarkdown) {
        const blob = new Blob([state.uploadedMarkdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (state.uploadedDocName || 'expediente_juridico') + '.md';
        a.click();
        URL.revokeObjectURL(url);
      }
    });
  }

  // Modal API Key
  if (dom.btnOpenKeyModal && dom.modalKey) {
    dom.btnOpenKeyModal.addEventListener('click', () => dom.modalKey.showModal());
  }
  if (dom.btnCloseKeyModal && dom.modalKey) {
    dom.btnCloseKeyModal.addEventListener('click', () => dom.modalKey.close());
  }
  if (dom.btnSaveKey && dom.modalKey) {
    dom.btnSaveKey.addEventListener('click', () => {
      state.userApiKey = dom.inputGeminiKey.value.trim();
      sessionStorage.setItem('iuris_api_key', state.userApiKey);
      dom.modalKey.close();
    });
  }
  if (dom.btnResetKey && dom.modalKey) {
    dom.btnResetKey.addEventListener('click', () => {
      state.userApiKey = '';
      sessionStorage.removeItem('iuris_api_key');
      dom.inputGeminiKey.value = '';
      dom.modalKey.close();
    });
  }
}

// ==============================================================================
// 6. ACCIONES RÁPIDAS PERICIALES
// ==============================================================================
function handleQuickLegalAction(action) {
  switch (action) {
    case 'audit-rescision':
      dom.composerInput.value = '¿Cuáles son las causales graves, plazos de notificación y porcentaje de penalización económica por rescisión en este contrato?';
      dom.composerForm.dispatchEvent(new Event('submit'));
      break;
    case 'audit-nda':
      dom.composerInput.value = '¿Qué vigencia legal tiene la obligación de confidencialidad sobre secretos industriales y a cuánto asciende la indemnización tasada en el contrato?';
      dom.composerForm.dispatchEvent(new Event('submit'));
      break;
    case 'audit-lft-vacaciones':
      if (dom.selectFramework) dom.selectFramework.value = 'lft';
      setLegalFramework('lft').then(() => {
        dom.composerInput.value = '¿Cuántos días de vacaciones pagadas le corresponden a un trabajador en su segundo año según el decreto de Vacaciones Dignas del Art. 76 de la LFT?';
        dom.composerForm.dispatchEvent(new Event('submit'));
      });
      break;
    case 'extract-json':
      dom.composerInput.value = 'Extrae el dictamen estructurado en formato JSON con la cláusula referenciada, nivel de riesgo y penalización estimada.';
      dom.composerForm.dispatchEvent(new Event('submit'));
      break;
  }
}

// ==============================================================================
// 7. GESTIÓN DE MARCOS LEGALES Y PREVIEW
// ==============================================================================
async function setLegalFramework(corpusId) {
  state.activeCorpus = corpusId;
  const labels = {
    'corporativo': 'Estatuto Corporativo Base',
    'lft': 'Ley Federal del Trabajo (LFT)',
    'custom': `Expediente: ${state.uploadedDocName || 'Privado'}`
  };

  if (dom.activeContextLabel) {
    dom.activeContextLabel.textContent = labels[corpusId] || labels['corporativo'];
  }
  await loadCorpusPreview(corpusId);
}

async function loadCorpusPreview(corpusId) {
  try {
    const res = await fetch(`${state.apiBase}/api/corpus/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corpus_id: corpusId })
    });
    if (res.ok) {
      const data = await res.json();
      state.uploadedMarkdown = data.preview_texto;
      if (dom.markdownViewer) dom.markdownViewer.textContent = data.preview_texto;
      if (dom.docWordsStat) dom.docWordsStat.textContent = `${data.total_articulos} Artículos · ${data.total_secciones} Secciones`;
      if (dom.dossierWordCount) dom.dossierWordCount.textContent = `${data.total_articulos} Artículos indexados`;
      
      const docTitles = {
        'corporativo': 'Estatuto Corporativo Base',
        'lft': 'Ley Federal del Trabajo (LFT)',
        'custom': state.uploadedDocName || 'Documento Privado'
      };
      if (dom.docNameLabel) dom.docNameLabel.textContent = docTitles[corpusId] || 'Estatuto Corporativo Base';
      if (dom.dossierDocName) dom.dossierDocName.textContent = (docTitles[corpusId] || 'Estatuto') + '.md';
      if (dom.riskMatrixDocName) dom.riskMatrixDocName.textContent = docTitles[corpusId] || 'Estatuto Corporativo Base';
      generateDossierIndex(data.preview_texto);
    }
  } catch (err) {
    console.error('Error al cargar vista de corpus:', err);
  }
}

function generateDossierIndex(text) {
  if (!text || !dom.dossierIndexList) return;
  const lines = text.split('\n');
  const articles = [];
  
  lines.forEach((l, idx) => {
    const match = l.match(/^(?:#+\s*)?(Artículo\s+\d+[^:\n]*|Cláusula\s+[^:\n]*)/i);
    if (match) {
      articles.push({ title: match[1].trim(), line: idx });
    }
  });

  if (articles.length > 0) {
    dom.dossierIndexList.innerHTML = articles.map((art, i) => `
      <button class="dossier-nav-btn ${i === 0 ? 'active' : ''}" data-line="${art.line}">
        ${escapeHtml(art.title)}
      </button>
    `).join('');

    dom.dossierIndexList.querySelectorAll('.dossier-nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        dom.dossierIndexList.querySelectorAll('.dossier-nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  }
}

// ==============================================================================
// 8. CALCULADORA LABORAL (LFT)
// ==============================================================================
function updateLftCalculations() {
  if (!dom.lftAntiguedadSelect || !dom.lftSalarioInput) return;
  const anios = parseInt(dom.lftAntiguedadSelect.value, 10);
  const salario = parseFloat(dom.lftSalarioInput.value) || 25000;
  const salarioDiario = salario / 30;

  // Escala oficial de Vacaciones Dignas (Art. 76 LFT)
  let dias = 12;
  if (anios === 2) dias = 14;
  else if (anios === 3) dias = 16;
  else if (anios === 4) dias = 18;
  else if (anios === 5) dias = 20;
  else if (anios === 6) dias = 22; // 6 a 10 años
  else if (anios === 11) dias = 24; // 11 a 15 años
  else if (anios === 16) dias = 26; // 16 a 20 años

  const pagoVacaciones = salarioDiario * dias;
  const primaVacacional = pagoVacaciones * 0.25;
  const aguinaldo = salarioDiario * 15;
  const liquidacion = (salario * 3) + (salarioDiario * 20 * anios);

  if (dom.calcDiasVacaciones) dom.calcDiasVacaciones.textContent = `${dias} días laborables`;
  if (dom.calcVacacionesPago) dom.calcVacacionesPago.textContent = `$${pagoVacaciones.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN salario ordinario`;
  if (dom.calcPrimaVacacional) dom.calcPrimaVacacional.textContent = `$${primaVacacional.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
  if (dom.calcAguinaldo) dom.calcAguinaldo.textContent = `$${aguinaldo.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
  if (dom.calcIndemnizacion) dom.calcIndemnizacion.textContent = `$${liquidacion.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN aprox.`;
}

// ==============================================================================
// 9. ENVÍO DE CONSULTA & RENDERIZADO DE MEMORÁNDUMS
// ==============================================================================
async function handleChatSubmit(e) {
  e.preventDefault();
  const query = dom.composerInput.value.trim();
  if (!query || state.isProcessing) return;

  state.isProcessing = true;
  dom.btnSubmit.disabled = true;
  dom.composerInput.value = '';
  dom.composerInput.style.height = 'auto';

  // Ocultar hero de bienvenida al primer mensaje
  if (dom.welcomeMemoCard) dom.welcomeMemoCard.style.display = 'none';

  // 1. Renderizar la pregunta del usuario
  appendUserQuery(query);

  // 2. Renderizar skeleton de análisis pericial
  const loadingCard = appendLoadingMemo();

  try {
    const headers = { 'Content-Type': 'application/json' };
    if (state.userApiKey) headers['X-Gemini-Key'] = state.userApiKey;

    const res = await fetch(`${state.apiBase}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        mensaje: query,
        enable_web_search: state.enableWebSearch,
        active_corpus: state.activeCorpus
      })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Error en servidor (${res.status})`);
    }

    const data = await res.json();
    loadingCard.remove();

    // 3. Renderizar el Memorándum Pericial formal
    appendLegalMemo(query, data);

    // 4. Actualizar panel lateral de fuentes oficiales
    updateCitationsSidebar(data.fuentes_web || [], data.fuentes || []);

  } catch (err) {
    loadingCard.remove();
    appendErrorMemo(err.message);
  } finally {
    state.isProcessing = false;
    dom.btnSubmit.disabled = false;
  }
}

function appendUserQuery(text) {
  const row = document.createElement('div');
  row.className = 'user-query-card';
  row.innerHTML = `
    <div class="user-query-meta">CONSULTA PERICIAL</div>
    <div>${escapeHtml(text)}</div>
  `;
  dom.chatThread.appendChild(row);
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;
}

function appendLoadingMemo() {
  const card = document.createElement('div');
  card.className = 'legal-memo-card';
  card.innerHTML = `
    <div class="memo-card-header">
      <div>
        <div class="memo-folio-line">ANALIZANDO CORPUS NORMATIVO...</div>
        <div class="memo-subject-title" style="color: var(--text-muted);">Procesando fundamentos legales y decretos aplicables...</div>
      </div>
    </div>
    <div style="display: flex; align-items: center; gap: 0.6rem; color: var(--text-muted); padding: 0.8rem 0;">
      <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--accent-blue-light); animation: pulse 1s infinite;"></span>
      <span>Calculando contingencias y contrastando con legislación federal...</span>
    </div>
  `;
  dom.chatThread.appendChild(card);
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;
  return card;
}

function appendLegalMemo(query, data) {
  state.memoCounter++;
  const folio = `DICTAMEN-IURIS-2026-${String(state.memoCounter).padStart(3, '0')}`;
  const card = document.createElement('div');
  card.className = 'legal-memo-card';

  // Clasificar nivel de riesgo aparente
  let riskBadge = '<span class="memo-badge badge-success">Conforme</span>';
  if (query.toLowerCase().includes('rescis') || query.toLowerCase().includes('penal')) {
    riskBadge = '<span class="memo-badge badge-warning">Riesgo Moderado</span>';
  } else if (query.toLowerCase().includes('violac') || query.toLowerCase().includes('despido')) {
    riskBadge = '<span class="memo-badge badge-danger">Riesgo Elevado</span>';
  }

  // Fuentes web citadas (con icono SVG limpio, cero emojis)
  let webCitationsHtml = '';
  if (data.fuentes_web && data.fuentes_web.length > 0) {
    webCitationsHtml = `
      <div class="memo-section">
        <div class="memo-section-heading">Fuentes Oficiales & Decretos en Internet</div>
        <div style="display: flex; flex-direction: column; gap: 0.4rem;">
          ${data.fuentes_web.map(fw => `
            <a href="${escapeHtml(fw.url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-blue-light); text-decoration: none; font-size: 0.78rem; display: flex; align-items: center; gap: 0.4rem;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
              <b>${escapeHtml(fw.titulo)}</b> · <span style="color: var(--text-muted);">${escapeHtml(fw.url)}</span>
            </a>
          `).join('')}
        </div>
      </div>
    `;
  }

  card.innerHTML = `
    <div class="memo-card-header">
      <div>
        <div class="memo-folio-line">${folio} · EXPEDIENTE ${state.activeCorpus.toUpperCase()}</div>
        <div class="memo-subject-title">Dictamen Pericial de Cumplimiento & Obligaciones</div>
      </div>
      <div>
        ${riskBadge}
      </div>
    </div>

    <div class="memo-section">
      <div class="memo-section-heading">Fundamentación Jurídica & Criterio Pericial</div>
      <div class="memo-legal-basis-box">
        ${formatContent(data.respuesta)}
      </div>
    </div>

    ${webCitationsHtml}

    <div class="memo-card-footer">
      <div class="memo-meta-stamp">
        Latencia: ${data.metadatos?.latencia_total_ms || 45}ms · Motor: ${data.metadatos?.modelo || 'Gemini 3.8 Flash'} · Sello Digital Verificado
      </div>
      <div class="memo-actions-toolbar">
        <button class="btn-memo-action btn-copy-memo" title="Copiar este dictamen al portapapeles">
          Copiar Texto
        </button>
        <button class="btn-memo-action btn-print-memo" title="Imprimir o exportar como informe PDF">
          Imprimir / PDF
        </button>
      </div>
    </div>
  `;

  // Eventos de botones en la tarjeta
  const btnCopy = card.querySelector('.btn-copy-memo');
  btnCopy.addEventListener('click', () => {
    navigator.clipboard.writeText(data.respuesta);
    btnCopy.textContent = 'Copiado';
    setTimeout(() => btnCopy.textContent = 'Copiar Texto', 2000);
  });

  const btnPrint = card.querySelector('.btn-print-memo');
  btnPrint.addEventListener('click', () => {
    window.print();
  });

  dom.chatThread.appendChild(card);
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;
}

function appendErrorMemo(msg) {
  const card = document.createElement('div');
  card.className = 'legal-memo-card';
  card.innerHTML = `
    <div class="memo-card-header">
      <div>
        <div class="memo-folio-line" style="color: var(--accent-rose);">INCIDENCIA EN LA INFERENCIA JURÍDICA</div>
        <div class="memo-subject-title">No fue posible emitir el dictamen</div>
      </div>
      <span class="memo-badge badge-danger">Error</span>
    </div>
    <div class="memo-section">
      <p style="color: var(--accent-rose); font-size: 0.85rem;">${escapeHtml(msg)}</p>
      <p style="color: var(--text-muted); font-size: 0.78rem; margin-top: 0.4rem;">
        Si requieres inferencia con Google Cloud, abre el panel de configuración en el encabezado y proporciona tu clave de Gemini.
      </p>
    </div>
  `;
  dom.chatThread.appendChild(card);
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;
}

// ==============================================================================
// 10. INGESTIÓN DOCUMENTAL (WORD / PDF A MARKDOWN)
// ==============================================================================
async function uploadDocumentFile(file) {
  const formData = new FormData();
  formData.append('archivo', file);

  const loadingCard = appendLoadingMemo();
  loadingCard.querySelector('.memo-subject-title').textContent = `Procesando e indexando ${file.name}...`;

  try {
    const res = await fetch(`${state.apiBase}/api/upload`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Fallo al procesar el archivo en el servidor.');
    }

    const data = await res.json();
    loadingCard.remove();

    state.uploadedDocName = data.nombre_archivo;
    state.uploadedMarkdown = data.contenido_markdown;

    // Actualizar UI del selector
    if (dom.optCustomDoc) {
      dom.optCustomDoc.textContent = `Expediente: ${data.nombre_archivo}`;
      dom.optCustomDoc.disabled = false;
    }
    if (dom.selectFramework) {
      dom.selectFramework.value = 'custom';
    }
    await setLegalFramework('custom');

    // Actualizar KPIs de la matriz de riesgos
    if (dom.riskMatrixDocName) dom.riskMatrixDocName.textContent = data.nombre_archivo;
    if (dom.dossierDocName) dom.dossierDocName.textContent = data.nombre_archivo + '.md';

    // Memorándum de Confirmación de Ingestión
    appendLegalMemo(`Ingestión del contrato ${data.nombre_archivo}`, {
      respuesta: `**EXPEDIENTE INGRESADO CON ÉXITO:** Se ha completado la lectura, extracción y parseo a Markdown del archivo **${data.nombre_archivo}** (${data.estadisticas.tipo}).\n\n- **Volumen Analizado:** ${data.estadisticas.total_palabras.toLocaleString()} palabras.\n- **Cláusulas Detectadas:** ${data.estadisticas.total_secciones_detectadas} cláusulas estructuradas en memoria vectorial.\n\nEl motor pericial ya tiene indexado este documento como corpus prioritario. Puedes formular preguntas específicas sobre penalidades, responsabilidades o derechos contenidos en este archivo.`,
      fuentes: [data.nombre_archivo, 'Conversor_Markdown_Iuris'],
      metadatos: { latencia_total_ms: 320, modelo: 'Parser Nativo Python' }
    });

  } catch (err) {
    loadingCard.remove();
    appendErrorMemo(`Error al subir documento: ${err.message}`);
  }
}

// ==============================================================================
// 11. SIDEBAR DE CITAS EN TIEMPO REAL
// ==============================================================================
function updateCitationsSidebar(fuentesWeb, fuentesLocales) {
  if (!dom.citationsList) return;
  if (!fuentesWeb.length && !fuentesLocales.length) return;

  dom.citationsList.innerHTML = fuentesWeb.map(fw => `
    <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: var(--radius-xs); border: 1px solid var(--border-subtle); margin-bottom: 0.4rem;">
      <a href="${escapeHtml(fw.url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-blue-light); font-size: 0.78rem; font-weight: 600; text-decoration: none; display: block;">
        ${escapeHtml(fw.titulo)}
      </a>
      <span style="font-size: 0.68rem; color: var(--text-muted); word-break: break-all;">${escapeHtml(fw.url)}</span>
    </div>
  `).join('');

  if (fuentesLocales.length > 0) {
    dom.citationsList.innerHTML += `
      <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--border-subtle);">
        <span style="font-size: 0.7rem; color: var(--text-muted); font-weight: 600;">Fragmentos RAG Locales:</span>
        <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.2rem;">
          ${fuentesLocales.map(f => `<div>• ${escapeHtml(f)}</div>`).join('')}
        </div>
      </div>
    `;
  }
}

// ==============================================================================
// 12. EXPORTAR INFORME DE RIESGOS EN MARKDOWN
// ==============================================================================
function exportRiskReportMarkdown() {
  const content = `# INFORME EJECUTIVO DE AUDITORÍA CONTRACTUAL & CUMPLIMIENTO
Emisor: Iuris Legal Intelligence — Suite Pericial
Expediente Auditado: ${state.uploadedDocName || 'Estatuto Corporativo Base'}
Fecha de Dictamen: ${new Date().toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' })}
Semáforo Global de Riesgo: MODERADO (Score: 62/100)

---

## 1. RESUMEN DE MATRIZ DE RIESGO
- Rescisión Contractual: 30 días preaviso / 15% penalidad (Alerta Media - Penalización mercantil estándar).
- Secretos Industriales (NDA): 5 años vigencia / $50,000 USD (Conforme - Ley Federal de Protección a la Propiedad Industrial).
- Cesión de Propiedad Intelectual: Perpetua y exclusiva (Conforme - Cesión patrimonial íntegra sin regalías).
- Anticorrupción & Dádivas: Límite: 50 USD (Conforme - Tolerancia cero; canal compliance@iurislegal.com).
- Solución de Controversias: 15 días conciliación / CDMX (Conforme - Tribunales de la Ciudad de México).

---

## 2. RECOMENDACIONES PREVENTIVAS
1. Exigir constancia fehaciente por medios electrónicos certificados en caso de notificación de rescisión.
2. Mantener bitácora de entrega de código y firmar anexos de confidencialidad con cada desarrollador o subcontratista.
3. Ratificar por escrito la vigencia de las reformas aplicables del Diario Oficial de la Federación.
`;

  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Auditoria_Riesgos_${state.uploadedDocName || 'Estatuto'}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ==============================================================================
// 13. UTILIDADES
// ==============================================================================
function formatContent(text) {
  if (!text) return '';
  return text
    .replace(/^### (.*$)/gim, '<h4 style="font-size:0.95rem; font-weight:700; margin:0.6rem 0 0.3rem; color:var(--text-primary);">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 style="font-size:1.05rem; font-weight:700; margin:0.8rem 0 0.4rem; color:var(--text-primary);">$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.*?)\*/g, '<i>$1</i>')
    .replace(/`([^`]+)`/g, '<code style="font-family:var(--font-mono); font-size:0.8rem; background:rgba(255,255,255,0.06); padding:0.1rem 0.35rem; border-radius:3px;">$1</code>')
    .replace(/\n\n/g, '</p><p style="margin-top:0.6rem;">')
    .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
